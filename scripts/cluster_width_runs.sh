#!/usr/bin/env bash
# Width sweeps for Qwen2.5 sizes on a hive cluster GPU (secondary 7B analysis + hardware check;
# rules: reports/agent1_width/README.md, "Amendment 24 November 2026").
#
#   bash cluster_width_runs.sh <sizes, e.g. 1.5b,3b> [limit]
#   job command: /bin/bash -c "curl -sSL <raw url of this file> -o run.sh && exec bash run.sh 1.5b,3b"
#   (exec: HTCondor signals only the job's main process, so this script must be it)
#
# Clones this repo's branch (public), builds a venv with the laptop's library versions (uv; its cache, the Python,
# the models and the Spider zip are kept on the shared scratch drive so a restart is quick), downloads the data and
# checks it against the laptop copies (sha256 + unchanged eval files), then for each size runs the dev and train
# sweeps: one after the other, or both at once with J26_PARALLEL=1 (needs GPU memory for two copies of the model).
# Results: /cluster/scratch/<user>/j26-width/<host>/{dev,train}_qwen<size>_fp16.jsonl + .log + env.txt (written
# per question, so a stopped job resumes where it was), copied into the job folder at the end.
# On SIGTERM (the desktop owner needs the PC) the job exits 85 = requeue (submit with checkpointing on).
# With a limit: dev only, first <limit> questions (a smoke test).
set -euo pipefail
SIZES=$1; LIMIT=${2:-}
BRANCH=${J26_BRANCH:-janiru/finish-agent1-unblocked}
JOB=$PWD
U=$(id -un); S=/cluster/scratch/$U; OUT=$S/j26-width/$(hostname)
# Job users have HOME=/nonexistent and the system Python cannot make a venv: uv brings its own Python.
# HF's xet downloader failed on the Spark's Wi-Fi (deleted its partial files); plain HTTP resumes them.
export HOME="$JOB" HF_HOME=$S/hf XDG_CACHE_HOME="$JOB/j26/.cache" UV_CACHE_DIR=$S/uv-cache \
  UV_PYTHON_INSTALL_DIR=$S/uv-python UV_LINK_MODE=copy TOKENIZERS_PARALLELISM=false \
  HF_HUB_DISABLE_XET=${HF_HUB_DISABLE_XET:-1} HF_HUB_DOWNLOAD_TIMEOUT=60
mkdir -p "$HF_HOME" "$OUT"
trap 'cd "$JOB"; rm -rf j26' EXIT
trap 'echo "SIGTERM: stopping, exit 85 = requeue"; kill $(jobs -p) 2>/dev/null; wait; exit 85' TERM

git clone -q --depth 1 -b "$BRANCH" https://github.com/JaniruEk/J26-DS-336-Reserch-Project.git j26
cd j26
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$PWD/.uv" UV_NO_MODIFY_PATH=1 sh -s -- -q
export PATH="$PWD/.uv:$PATH"
uv venv -q --python 3.12 .venv
. .venv/bin/activate
if [ "$(uname -m)" = aarch64 ]; then
  # ponytail: the laptop's torch 2.6.0+cu124 has no ARM/GB10 build; the newest CUDA build is used and recorded in env.txt
  uv pip install -q torch --index-url https://download.pytorch.org/whl/cu130
else
  uv pip install -q torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
fi
uv pip install -q transformers==5.20.2 accelerate==1.15.0 tokenizers==0.23.3 scikit-learn==1.9.1 joblib==1.5.2 \
  numpy==2.2.6 spacy==3.8.14 tiktoken==0.12.0 chromadb==1.5.9 onnxruntime==1.29.0 SQLAlchemy==2.0.44 fastapi httpx \
  https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.8.0/en_core_web_md-3.8.0-py3-none-any.whl
{ date; git log -1 --format='code %h %s'; hostname; uname -m; uv --version; python --version
  nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used --format=csv,noheader
  python -c "import torch, transformers; print('torch', torch.__version__, 'cuda', torch.version.cuda, '| transformers', transformers.__version__)"
} | tee -a "$OUT/env.txt"

mkdir -p data
python scripts/get_chinook.py
curl -sSL -o data/northwind.db https://github.com/jpwhite3/northwind-SQLite3/raw/main/dist/northwind.db
[ -f "$S/spider.zip" ] && cp "$S/spider.zip" data/spider.zip
python -m scripts.get_spider --width
[ -f "$S/spider.zip" ] || cp data/spider.zip "$S/spider.zip"
sha256sum -c - <<'EOF'
7651ba378ac2fcd0dfc3c66fb101f7a7eed3ba39a612ec642b96e20702061f15  data/chinook.db
2f4f5c68dfcd33ba27373eae48c7a4869800c68095ee0f9f0da494f83382a877  data/northwind.db
EOF
git diff --quiet eval || { echo "the downloaded Spider data gives different question files"; git diff --stat eval; exit 1; }

run() {  # size, set name, question files
  local f="$OUT/$2_qwen$1_fp16.jsonl"
  # a kill can leave a half-written last line: drop it so the resume (one JSON row per line) reads the file
  [ -f "$f" ] && python -c "import sys; p=sys.argv[1]; b=open(p,'rb').read(); open(p,'wb').write(b[:b.rfind(b'\n')+1])" "$f"
  echo "$(date) start $2 $1" >> "$OUT/$2_qwen$1.log"
  exec python -m scripts.width_sweep --pairs $3 --local fp16 --hf-model "Qwen/Qwen2.5-${1^^}-Instruct" --elbow \
    ${LIMIT:+--limit $LIMIT} --out "$f" >> "$OUT/$2_qwen$1.log" 2>&1
}
DEV="eval/spider_dev_full.json eval/chinook_pairs.json eval/northwind_pairs.json"
TRAIN=eval/spider_train_width.json
for SIZE in ${SIZES//,/ }; do
  python -c "from huggingface_hub import snapshot_download as s; s('Qwen/Qwen2.5-${SIZE^^}-Instruct')" &  # one download
  wait $!                                                     # (in the background so SIGTERM is handled at once)
  if [ -n "$LIMIT" ]; then run "$SIZE" dev "$DEV" & wait $!
  elif [ -n "${J26_PARALLEL:-}" ]; then run "$SIZE" dev "$DEV" & run "$SIZE" train "$TRAIN" & wait
  else run "$SIZE" dev "$DEV" & wait $!; run "$SIZE" train "$TRAIN" & wait $!; fi
  tail -n 9 "$OUT"/*_qwen"$SIZE".log
done
cp "$OUT"/*.jsonl "$OUT"/*.log "$OUT/env.txt" "$JOB/"
