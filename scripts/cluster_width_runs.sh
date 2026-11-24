#!/usr/bin/env bash
# Width sweeps for one Qwen2.5 size on a hive cluster GPU (secondary 7B analysis + hardware check;
# rules: reports/agent1_width/README.md, "Amendment 24 November 2026").
#
#   bash cluster_width_runs.sh <0.5b|1.5b|3b|7b> [limit]
#
# In the job folder: clones this repo's branch (public), builds a venv with the laptop's library versions,
# downloads the data and checks it against the laptop copies (sha256 + unchanged eval files), then runs the
# dev and train sweeps in parallel on the same GPU. Result files land in the job folder (copied back to hive):
# dev_qwen<size>_fp16.jsonl, train_qwen<size>_fp16.jsonl, plus env.txt (versions and GPU).
# With a limit: dev only, first <limit> questions (a smoke test).
set -euo pipefail
SIZE=$1; LIMIT=${2:-}
BRANCH=${J26_BRANCH:-janiru/finish-agent1-unblocked}
JOB=$PWD
# The job folder is copied back to hive at the end: keep the model (15 GB for 7B) on the shared scratch drive
# (cleaned after 7 days) and delete the clone, venv and caches when the job ends.
export HF_HOME=/cluster/scratch/$(id -un)/hf XDG_CACHE_HOME="$JOB/j26/.cache" PIP_NO_CACHE_DIR=1 \
  TOKENIZERS_PARALLELISM=false PIP_DISABLE_PIP_VERSION_CHECK=1
mkdir -p "$HF_HOME"
trap 'cd "$JOB"; rm -rf j26' EXIT

git clone -q --depth 1 -b "$BRANCH" https://github.com/JaniruEk/J26-DS-336-Reserch-Project.git j26
cd j26
python3 -m venv .venv && . .venv/bin/activate
if [ "$(uname -m)" = aarch64 ]; then
  # ponytail: the laptop's torch 2.6.0+cu124 has no ARM/GB10 build; the newest CUDA build is used and recorded in env.txt
  pip install -q torch --index-url https://download.pytorch.org/whl/cu130
else
  pip install -q torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
fi
pip install -q transformers==5.20.2 accelerate==1.15.0 tokenizers==0.23.3 scikit-learn==1.9.1 joblib==1.5.2 \
  numpy==2.2.6 spacy==3.8.14 tiktoken==0.12.0 chromadb==1.5.9 onnxruntime==1.29.0 SQLAlchemy==2.0.44 fastapi httpx \
  https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.8.0/en_core_web_md-3.8.0-py3-none-any.whl
{ git log -1 --format='code %h %s'; uname -m; nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
  python -c "import torch, transformers; print('torch', torch.__version__, 'cuda', torch.version.cuda, '| transformers', transformers.__version__)"
} | tee "$JOB/env.txt"

mkdir -p data
python scripts/get_chinook.py
curl -sSL -o data/northwind.db https://github.com/jpwhite3/northwind-SQLite3/raw/main/dist/northwind.db
python -m scripts.get_spider --width
sha256sum -c - <<'EOF'
7651ba378ac2fcd0dfc3c66fb101f7a7eed3ba39a612ec642b96e20702061f15  data/chinook.db
2f4f5c68dfcd33ba27373eae48c7a4869800c68095ee0f9f0da494f83382a877  data/northwind.db
EOF
git diff --quiet eval || { echo "the downloaded Spider data gives different question files"; git diff --stat eval; exit 1; }

run() {  # set name, question files
  python -m scripts.width_sweep --pairs $2 --local fp16 --hf-model "Qwen/Qwen2.5-${SIZE^^}-Instruct" --elbow \
    ${LIMIT:+--limit $LIMIT} --out "$JOB/$1_qwen${SIZE}_fp16.jsonl" > "$JOB/$1.log" 2>&1
}
DEV="eval/spider_dev_full.json eval/chinook_pairs.json eval/northwind_pairs.json"
python -c "from huggingface_hub import snapshot_download as s; s('Qwen/Qwen2.5-${SIZE^^}-Instruct')"  # one download for both runs
if [ -n "$LIMIT" ]; then run dev "$DEV"; else run dev "$DEV" & run train eval/spider_train_width.json & wait; fi
tail -n 9 "$JOB"/*.log
mkdir -p "/cluster/scratch/$(id -un)/j26-width" && cp "$JOB"/*.jsonl "$JOB/env.txt" "/cluster/scratch/$(id -un)/j26-width/"
