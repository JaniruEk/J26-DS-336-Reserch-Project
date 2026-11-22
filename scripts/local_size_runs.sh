#!/usr/bin/env bash
# Width sweeps for the model-size study on the laptop GPU (rules: reports/agent1_width/README.md, amended 23 Nov 2026).
# Resumable: run it again after a stop; every sweep skips the questions already in its file.
# Phase 1 in parallel: 0.5B FP16 dev + train. Phase 2 alone (GPU memory): 3B FP16 dev, then 3B FP16 train. No 7B.
cd "$(dirname "$0")/.."
DEV="eval/spider_dev_full.json eval/chinook_pairs.json eval/northwind_pairs.json"
TRAIN="eval/spider_train_width.json"
export TOKENIZERS_PARALLELISM=false

run() {  # size (0.5b|1.5b|3b|7b), precision, set name (dev|train), question files
  local tag="$3_qwen$1_$2"
  local attempt
  for attempt in 1 2 3; do  # a load can fail on low Windows memory ("paging file too small"); runs resume
    python -m scripts.width_sweep --pairs $4 --local "$2" --hf-model "Qwen/Qwen2.5-${1^^}-Instruct" --elbow \
      --out "results/width/$tag.jsonl" >> "data/width_sweep_$tag.log" 2>&1 && { echo "$(date +%H:%M) $tag done"; return; }
    echo "$(date +%H:%M) $tag attempt $attempt failed"; sleep 60
  done
}

echo "$(date +%H:%M) phase 1"
run 0.5b fp16 dev "$DEV" & run 0.5b fp16 train "$TRAIN" & wait
echo "$(date +%H:%M) phase 2"
run 3b fp16 dev "$DEV"
run 3b fp16 train "$TRAIN"
echo "$(date +%H:%M) ALL DONE"
