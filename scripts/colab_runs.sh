#!/usr/bin/env bash
# Width sweeps for the model-size study on one Colab GPU (plan: reports/agent1_width/plan_weeks5-6.md, Task 6).
# Resumable: after a disconnect, run it again; every sweep skips the questions already in its file.
# Phase A in parallel: 0.5B dev+train, 1.5B dev, 3B dev+train. Phase B: 7B dev+train (parallel if the GPU has room).
OUT=${1:-/content/drive/MyDrive/j26_width/results}
exec 9>/tmp/j26_runs.lock
flock -n 9 || { echo "the runs are already going (another colab_runs.sh holds the lock)"; exit 0; }
mkdir -p "$OUT"
DEV="eval/spider_dev_full.json eval/chinook_pairs.json eval/northwind_pairs.json"
TRAIN="eval/spider_train_width.json"
export TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=2

run() {  # size (0.5b|1.5b|3b|7b), set name (dev|train), question files
  python -m scripts.width_sweep --pairs $3 --local fp16 --hf-model "Qwen/Qwen2.5-${1^^}-Instruct" --elbow \
    --out "$OUT/$2_qwen$1_fp16.jsonl" >> "$OUT/$2_qwen$1_fp16.log" 2>&1
  echo "$(date +%H:%M) $2 $1 exit $?"
}

echo "$(date +%H:%M) phase A"
run 0.5b dev "$DEV" & run 0.5b train "$TRAIN" & run 1.5b dev "$DEV" & run 3b dev "$DEV" & run 3b train "$TRAIN" & wait
echo "$(date +%H:%M) phase B"
if [ "$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)" -ge 39000 ]; then
  run 7b dev "$DEV" & run 7b train "$TRAIN" & wait
else
  run 7b dev "$DEV"; run 7b train "$TRAIN"
fi
echo "$(date +%H:%M) ALL DONE"
