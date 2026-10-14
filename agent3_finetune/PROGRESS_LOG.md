# Agent 3 Progress Log: LoRA vs HydraLoRA

**Owner:** K.G.Y.V. Thathsarani (IT23404250)
**Branch:** `thathsarani-lora-baseline`
**Project:** J26-DS-336, Distributed Multi-Agent SLM Framework

How to read this file: every entry says what was done, what was found, and what was decided, so the work can be explained to supervisors later.

---

## Current status

| Phase (from Execution Plan) | Status |
|---|---|
| Environment setup | Done |
| Phase 1: Dataset from Spider train | Done (v1, full-schema context) |
| Phase 2: Standard LoRA baseline | **Training done (seed 42). Evaluation (exact match, execution accuracy) not yet written** |
| Phase 3: HydraLoRA module | Not started |
| Phase 4: Placeholder comparison | Not started |

**Next step:** write the evaluation script (exact match + execution accuracy per complexity bucket on the shared eval pairs), then score the LoRA baseline.

---

## Work log

### 2026-10-14 (reported): Full LoRA baseline run, seed 42
- Trained standard LoRA on Qwen2.5-1.5B-Instruct (placeholder base) with the full-schema dataset.
- 969 steps (5,162 examples / effective batch 16 = 323 steps per epoch, 3 epochs).
- Validation loss 0.288 (524 validation examples). This is a sanity check only, not an accuracy result.
- Trainable parameters: 18,464,768 of 1,562,179,072 (1.18%).
- Memory cap of 8 GB was enforced in code (a run over the cap would have crashed). The smoke test peaked at 5.31 GB.
- The run was split across Colab sessions. The final `run_info.json` (peak 5.62 GB, 11 s) therefore describes only the last session (evaluation). The loss history is preserved in `checkpoint-969/trainer_state.json`.
- Outputs are on Google Drive: `agent3/runs/lora_seed42/` (adapter, checkpoints, run_info.json).

### 2026-10-08: Colab setup and smoke test
- Kaggle phone verification failed (asked for identity verification), so Colab (free T4, 15 GB) is used.
- Wrote `agent3_finetune/train_lora.py` (LoRA training, 8 GB cap, checkpoint saving and automatic resume).
- Fixes needed on first runs:
  - Removed Colab's old `torchao` (version conflict with the newer `peft`).
  - `warmup_ratio` is no longer accepted by the newer `transformers`; replaced with `warmup_steps=20`.
  - Batch 4 ran out of memory under the 8 GB cap (the large vocabulary makes the output layer big); switched to batch 2 with gradient accumulation 8 (effective batch still 16).
- Smoke test (50 steps, 300 examples): worked, peak 5.31 GB, about 6 s per step.

### 2026-10-06: Setup and Phase 1 dataset
- Cloned the team repo and created branch `thathsarani-lora-baseline`.
- Installed Python 3.11.9 (3.14 is too new for the ML libraries) and a `venv`; repo tests: 11 passed, 4 skipped.
- Added `venv/` to `.gitignore` after GitHub Desktop showed 11,608 changed files.
- Wrote `agent3_finetune/build_dataset.py` (run with `python -m agent3_finetune.build_dataset`).

**What the dataset builder does:** reads Spider train, removes nested/compound queries, removes questions that appear in `eval/*.json` (leakage guard), labels each query with the shared `classify_sql`, attaches the database schema (CREATE TABLE text), and splits by database so validation uses unseen schemas.

| Step | Count |
|---|---|
| Spider train examples | 7,000 |
| After removing nested/compound | 5,981 |
| After removing eval questions | 5,980 |

| Bucket | Train | Val |
|---|---|---|
| simple | 1,644 | 171 |
| single-join | 776 | 82 |
| multi-join | 375 | 21 |
| aggregation | 2,661 | 250 |
| **Total** | **5,456** | **524** |

140 databases in total, 14 held out for validation (seed 42).

---

## Findings

1. **Multi-join is the thin bucket.** 375 training and 21 validation examples. Conclusions will come from the shared eval pairs with paired statistics, not from this validation split.
2. **Aggregation dominates** (about 49% of training examples).
3. **Long schemas cause drops.** With the full schema in the prompt, 669 of 5,831 training rows (11.5%) exceeded 1,024 tokens and were dropped:

   | Bucket | Dropped | Share |
   |---|---|---|
   | simple | 141 | 8.6% |
   | single-join | 107 | 13.8% |
   | multi-join | 96 (48 unique, counted twice by over-sampling) | 12.8% |
   | aggregation | 325 | 12.2% |

   The model therefore never saw the largest databases (a limitation to state). Agent 1's pruned schema is much shorter, which is an extra reason to test pruned context in Phase 8b.
4. **Validation loss alone proves nothing.** Accuracy needs the evaluation script.

---

## Decisions and alternatives

| Date | Decision | Alternatives not (yet) tested | Status |
|---|---|---|---|
| 10-06 | Split by database, not by row | Random row split | Final: tests unseen schemas |
| 10-06 | Reuse `classify_sql` for labels | Own labelling | Final: keeps results comparable across agents |
| 10-06 | Remove questions that appear in `eval/*.json` | none | Final |
| 10-06 | Python 3.11.9 | 3.14 | Final: 3.14 unsupported by the ML libraries |
| 10-08 | Colab T4 instead of Kaggle | Kaggle (verification failed), local GPU (none) | Final; GPU is recorded beside each result |
| 10-08 | Placeholder base: Qwen2.5-1.5B-Instruct | Other 0.5B-1.5B models | **My suggestion; Wathsala's final model overrides it** (plan re-runs on her bases) |
| 10-08 | LoRA rank 16, alpha 32, LR 2e-4, 3 epochs, seed 42 | Rank 8/32, other LRs | **Untuned defaults. A small sweep is needed before claiming a fair baseline** |
| 10-08 | Batch 2 x accumulation 8 (effective 16) | Batch 4 (ran out of memory at the 8 GB cap) | Final |
| 10-08 | Max length 1024 tokens (longer examples dropped) | Larger limit, or pruned schema | Revisit with Agent 1 pruned context |
| 10-08 | Multi-join over-sampled x2 | x1 or other factors | Untested design choice |
| 10-08 | Plain-text prompt template (`### Schema / ### Question / ### SQL`) | Chat template | Must stay identical for LoRA and HydraLoRA |
| 10-08 | Own training loop (Transformers + PEFT) | TRL SFTTrainer | Engineering choice |

**Needed for a fair final comparison (from the Execution Plan's research protocol):** tune the LoRA baseline with the same budget as HydraLoRA; add a parameter-matched LoRA control; run 3 seeds; report execution accuracy as well as exact match, per bucket with paired statistics.

---

## Open items

- [ ] Write the evaluation script (exact match + execution accuracy by bucket; use `exec_match` and `stats.py`).
- [ ] Score the LoRA baseline on `eval/spider_pairs.json`, Chinook and TPC-H.
- [ ] Small rank / learning-rate sweep on one seed, then freeze the config.
- [ ] Build the HydraLoRA module (shared A, one B head per bucket, hard-coded routing) and test on a tiny subset first.
- [ ] Parameter-matched LoRA control.
- [ ] Re-train on Agent 1's pruned `ddl` and compare to this full-schema control (Ekanayake's Phase 8b).
- [ ] Over-sample or generate extra multi-join examples; consider raising the length limit.
- [ ] Confirm base model and shared config with Wathsala; confirm the handoff format with Ekanayake (messages not yet sent or answered).
- [ ] Commit small result files (`run_info.json`, `trainer_state.json`) under `agent3_finetune/results/`.

---

## Where things live

- **Code:** this repo (branch `thathsarani-lora-baseline`), edited in VS Code, pushed with GitHub Desktop.
- **Training data (not in Git):** Google Drive `agent3/train.jsonl`, `agent3/val.jsonl`.
- **Run outputs (not in Git):** Google Drive `agent3/runs/<run name>/` (adapter, checkpoints, run_info.json).
- **Colab routine each session:** mount Drive, clone/pull the branch, install `peft accelerate`, remove `torchao`, then train.

## Environment notes

- Laptop: Intel Iris Xe (no NVIDIA GPU), 16 GB RAM, Windows. Training runs on Colab.
- Python 3.11.9 with a `venv` locally. The project folder is inside OneDrive; pause syncing if the laptop slows down.
- Run scripts as modules from the project root, for example `python -m scripts.get_spider`.

---

## AI use disclosure (for Appendix 3)

Claude (Anthropic) was used as a tutor and coding assistant for environment setup, Git workflow guidance, and drafting `build_dataset.py` and `train_lora.py`. The code was run and the outputs above were produced and checked by the author.