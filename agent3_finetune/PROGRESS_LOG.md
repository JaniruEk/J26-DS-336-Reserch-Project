# Agent 3 Progress Log: LoRA vs HydraLoRA

**Owner:** K.G.Y.V. Thathsarani (IT23404250)
**Branch:** `thathsarani-lora-baseline`
**Project:** J26-DS-336, Distributed Multi-Agent SLM Framework

How to read this file: the newest entry is at the top of each section. Every entry says what was done, what was found, and what was decided, so the work can be explained to supervisors later.

---

## Current status

| Phase (from Execution Plan) | Status |
|---|---|
| Environment setup | Done (2026-10-06) |
| Phase 1: Dataset from Spider train | Done, v1 (2026-10-06); refinements pending |
| Phase 2: Standard LoRA baseline | Not started |
| Phase 3: HydraLoRA module | Not started |
| Phase 4: Placeholder comparison | Not started |

**Next step:** choose the base model and training platform (Kaggle or Colab), then write the LoRA baseline.

---

## Work log

### 2026-10-06: Setup and Phase 1 dataset

**Done**
- Cloned the team repo and created branch `thathsarani-lora-baseline`.
- Installed Python 3.11.9 (3.14 is too new for the ML libraries) and created a `venv`.
- Installed `requirements.txt` and the spaCy model `en_core_web_md`.
- Ran the repo tests: 11 passed, 4 skipped (the skipped ones need the Chinook database).
- Added `venv/` to `.gitignore` after GitHub Desktop showed 11,608 changed files.
- Ran `python -m scripts.get_spider` to get the Spider data.
- Wrote `agent3_finetune/build_dataset.py`. Run it with `python -m agent3_finetune.build_dataset`.

**What the dataset builder does**
1. Reads Spider train from `data/spider.zip`.
2. Removes nested and compound queries (the same rule the rest of the repo uses).
3. Removes any question that also appears in `eval/*.json` (leakage guard).
4. Labels each query with the shared `classify_sql` function.
5. Attaches the database schema (CREATE TABLE text) as context.
6. Splits by database, so validation uses schemas the model never saw.

**Result (seed 42, 10% of databases held out)**

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

140 databases in total, 14 held out for validation.

---

## Findings

1. **Multi-join is the thin bucket.** Only 375 training examples and 21 validation examples. HydraLoRA's multi-join head depends on this bucket, so it is the main data risk.
2. **Validation is too small for multi-join (n=21).** Conclusions will come from the shared `eval/spider_pairs.json` (30 per bucket) with the paired statistics in `stats.py`, not from this validation split.
3. **Aggregation dominates** (2,661 of 5,456 training examples, about 49%). Training without balancing could bias the model toward aggregation.
4. **Counts match the Execution Plan.** Train plus val gives simple 1,815, single-join 858, multi-join 396, aggregation 2,912, the same as the plan's bucket counts.

---

## Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-10-06 | Split by database, not by random row | Validation then tests unseen schemas, which is the honest way to evaluate on Spider |
| 2026-10-06 | Reuse `classify_sql` for labels | Keeps results comparable with the other three agents |
| 2026-10-06 | Remove questions that appear in `eval/*.json` | Prevents leakage into the shared evaluation sets |
| 2026-10-06 | Use Python 3.11.9 | Python 3.14 is not supported by the ML libraries |

---

## Open items

- [ ] Over-sample multi-join during training (the plan says to).
- [ ] Balance the aggregation bucket for training.
- [ ] Swap the full schema for Agent 1's pruned `ddl` so training matches inference (Execution Plan, Phase 1).
- [ ] Sign off the Agent 1 to Agent 3 handoff format with Ekanayake (JSON with `query, complexity, mode, anchor, tables, ddl, tokens, latency_ms`).
- [ ] Choose the base model (placeholder for now) and fix the shared fine-tuning configuration with Wathsala (rank, learning rate, epochs, seed, split).
- [ ] Choose the training platform (the laptop has no NVIDIA GPU, so Kaggle or Colab).
- [ ] Download Chinook (`python -m scripts.get_chinook`) so the skipped tests can run.

---

## Environment notes

- Laptop: Intel Iris Xe graphics (no NVIDIA GPU), 16 GB RAM, Windows. Training must happen on Kaggle or Colab.
- Python 3.11.9 with a `venv` in the project folder.
- Run scripts as modules from the project root, for example `python -m scripts.get_spider`.
- The project folder is inside OneDrive. If syncing slows the laptop, pause OneDrive or move the project to `C:\Projects`.

---

## AI use disclosure (for Appendix 3)

Claude (Anthropic) was used as a tutor and coding assistant for environment setup, Git workflow guidance, and drafting `build_dataset.py`. The code was run and the outputs above were produced and checked by the author.
