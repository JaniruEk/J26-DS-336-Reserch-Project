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
| Phase 2: Standard LoRA baseline | **Done for seed 42: trained and evaluated.** Tuning sweep and extra seeds still to do |
| Phase 3: HydraLoRA module | Not started (next) |
| Phase 4: Placeholder comparison | Not started |

Next step: design and build the HydraLoRA module (shared A, one B head per bucket, hard-coded routing), then compare it with LoRA using compare.py.

---

## Baseline result (LoRA, seed 42, full-schema context)

Execution accuracy on the shared eval pairs, pooled Spider dev (120) + Chinook (14); 128 pairs scored. Values are accuracy with a 95% Wilson interval.

| Bucket | LoRA (fine-tuned) | Base Qwen (no training) |
|---|---|---|
| simple | 0.74 [0.57-0.86] (23/31) | 0.55 [0.38-0.71] (17/31) |
| single-join | 0.68 [0.50-0.81] (21/31) | 0.29 [0.16-0.47] (9/31) |
| multi-join | **0.19 [0.09-0.35] (6/32)** | 0.25 [0.13-0.42] (8/32) |
| aggregation | 0.59 [0.42-0.74] (20/34) | 0.56 [0.39-0.71] (19/34) |
| **ALL** | **0.55 [0.46-0.63] (70/128)** | 0.41 [0.33-0.50] (53/128) |

Normalised exact match (stricter than Spider's official metric), pooled: LoRA 0.34 overall (multi-join 0/33), base 0.19 (multi-join 0/33). TPC-H is schema-only (no rows), so only exact match exists: LoRA 2/14, base 3/14. Model outputs are cleaned the same way for both (code fences and text after the first `;` removed).

Raw outputs: `agent3_finetune/results/` (`*_predictions.json`, `*_predictions_scored.json`, `lora_seed42_run_info.json`, `lora_seed42_trainer_state.json`).

---

## Work log

### 2026-10-14 (reported): Paired comparison LoRA vs base
- Wrote `agent3_finetune/compare.py` (paired differences with bootstrap CI and exact McNemar per bucket, using the shared `agent1_retrieval/stats.py`).
- Result saved in `agent3_finetune/results/compare_lora_vs_base.txt`: LoRA is better overall (+0.13, p = 0.012), clearly on single-join (+0.39, p = 0.002), with no detectable difference on multi-join or aggregation (see Findings 1, 2 and 8).

### 2026-10-14 (reported): Scoring fix
- The base model's first score (0.05) was wrong: its answers start with a markdown code fence. Added `clean_sql` to `evaluate.py` (strips fences and text after the first `;`), applied to both models in `score`; no re-generation needed.
- Corrected base execution accuracy: 0.41 (53/128). LoRA unchanged: 0.55 (70/128).

### 2026-10-14 (reported): Evaluation of the LoRA baseline and the untrained base model
- Wrote `agent3_finetune/evaluate.py` with three steps: `prepare` (laptop), `generate` (Colab), `score` (laptop).
- `prepare` builds the inputs from `eval/*.json` with the schema text in the same format as training.
- `generate` uses greedy decoding, max 256 new tokens; 148 questions took about 3 min on the T4 with peak 3.67 GB.
- `score` uses the shared `exec_match` and prints exact match and execution accuracy per bucket with Wilson 95% intervals; per-item results are saved for later paired tests.
- Ran both the LoRA adapter and the base model on the same 148 questions.

### 2026-10-14 (reported): Full LoRA baseline run, seed 42
- Standard LoRA on Qwen2.5-1.5B-Instruct (placeholder base), full-schema dataset.
- 969 steps (5,162 examples, effective batch 16, 3 epochs). Validation loss 0.288.
- Trainable parameters: 18,464,768 of 1,562,179,072 (1.18%).
- The 8 GB memory cap is enforced in code; the smoke test peaked at 5.31 GB.
- The run was split across Colab sessions, so the final `run_info.json` (peak 5.62 GB, 11 s) describes only the last session. The loss history is in `lora_seed42_trainer_state.json`.
- Outputs on Google Drive: `agent3/runs/lora_seed42/`.

### 2026-10-08: Colab setup and smoke test
- Kaggle phone verification failed (asked for identity verification), so Colab (free T4, 15 GB) is used.
- Wrote `agent3_finetune/train_lora.py` (LoRA training, 8 GB cap, checkpoint saving and automatic resume).
- Fixes needed on first runs: removed Colab's old `torchao`; replaced `warmup_ratio` with `warmup_steps=20` (newer `transformers`); batch 4 ran out of memory at the 8 GB cap, so batch 2 with accumulation 8 (effective batch still 16).
- Smoke test (50 steps, 300 examples): worked, peak 5.31 GB, about 6 s per step.

### 2026-10-06: Setup and Phase 1 dataset
- Cloned the team repo, created branch `thathsarani-lora-baseline`, installed Python 3.11.9 and a `venv`; repo tests: 11 passed, 4 skipped.
- Added `venv/` to `.gitignore` after GitHub Desktop showed 11,608 changed files.
- Wrote `agent3_finetune/build_dataset.py`: reads Spider train, removes nested/compound queries and questions that appear in `eval/*.json`, labels with `classify_sql`, attaches the schema text, splits by database.

| Bucket | Train | Val |
|---|---|---|
| simple | 1,644 | 171 |
| single-join | 776 | 82 |
| multi-join | 375 | 21 |
| aggregation | 2,661 | 250 |
| **Total** | **5,456** | **524** |

7,000 Spider train examples, 5,981 after removing nested/compound, 5,980 after removing eval questions; 140 databases, 14 held out for validation (seed 42).

---

## Findings

1. **LoRA helps overall, mostly on single-join (paired test, one seed).** Execution accuracy 0.55 [0.46-0.63] vs 0.41 [0.33-0.50] for the untrained base: paired difference +0.13 [+0.05, +0.23], 29 questions only LoRA got right vs 12 only the base, exact McNemar p = 0.012. Single-join: 0.29 to 0.68, +0.39 [+0.19, +0.58], 13 vs 1, p = 0.002 (survives a Bonferroni correction over 5 buckets, threshold 0.01). Simple: +0.19 [0.00, +0.39], p = 0.109 (suggestive only). The earlier phi3 stand-in (about 0.40, CLAUDE.md) is about the same as untrained Qwen-1.5B.
2. **No detectable LoRA improvement on multi-join or aggregation.** Multi-join 0.25 to 0.19 (-0.06 [-0.25, +0.09], 3 vs 5, p = 0.73); aggregation 0.56 to 0.59 (+0.03 [-0.15, +0.21], 5 vs 4, p = 1.0). 'No detectable difference' is not 'no effect': with about 32 questions per bucket, moderate effects cannot be excluded. These are the buckets HydraLoRA targets, so this motivates the comparison. Rival explanation: multi-join also had the least training data (375 examples, about 13% dropped as too long).
3. **Intervals are wide.** About 30 questions per bucket means one answer moves a score by about 3 points. Differences between LoRA and HydraLoRA will only be detectable if large, or with a bigger evaluation set and 3 seeds.
4. **Exact match is a poor headline metric here.** It is far below execution accuracy (0.34 vs 0.55), and multi-join exact match is 0/33 even though 6 multi-join queries execute correctly: our simple text match penalises aliases, quoting, column order and similar harmless differences. Report execution accuracy as the main metric and call exact match "normalised exact match".
5. **Resolved: the first base-model score (0.05) was a formatting artefact.** The untrained model wraps SQL in code fences. `score` now strips fences and text after the first `;` for every model; the corrected base score is 0.41.
6. **Long schemas cause drops in training.** With the full schema, 669 of 5,831 training rows (11.5%) exceeded 1,024 tokens and were dropped (simple 141 = 8.6%, single-join 107 = 13.8%, multi-join 96 = 12.8% (48 unique), aggregation 325 = 12.2%). The model never saw the largest databases. Agent 1's pruned schema is shorter, which is a reason to test pruned context in Phase 8b. None of the 148 evaluation prompts exceeded the 2,048-token limit.
7. **Multi-join and aggregation are the data-thin buckets** for training (375 multi-join training examples), the main data risk for HydraLoRA's multi-join head.
8. **Low statistical power for per-bucket claims.** With about 32 questions per bucket, a LoRA vs HydraLoRA difference becomes significant only if it is large (roughly 20-25 points with almost no losses in the other direction, e.g. 9 wins vs 1 loss). A larger evaluation set (full Spider dev) and 3 seeds are needed before the final comparison. Exact match is unusable for multi-join (0/33 for both models, so no discordant pairs).

---

## Decisions and alternatives

| Date | Decision | Alternatives not (yet) tested | Status |
|---|---|---|---|
| 10-06 | Split by database, not by row | Random row split | Final: tests unseen schemas |
| 10-06 | Reuse `classify_sql` for labels | Own labelling | Final: comparable across agents |
| 10-06 | Remove questions that appear in `eval/*.json` | none | Final |
| 10-06 | Python 3.11.9 | 3.14 | Final: 3.14 unsupported by the ML libraries |
| 10-08 | Colab T4 instead of Kaggle | Kaggle (verification failed), local GPU (none) | Final; GPU recorded beside each result |
| 10-08 | Placeholder base: Qwen2.5-1.5B-Instruct | Other 0.5B-1.5B models | **My suggestion; Wathsala's final model overrides it** |
| 10-08 | LoRA rank 16, alpha 32, LR 2e-4, 3 epochs, seed 42 | Rank 8/32, other LRs | **Untuned defaults. A small sweep is needed before claiming a fair baseline** |
| 10-08 | Batch 2 x accumulation 8 (effective 16) | Batch 4 (out of memory at the 8 GB cap) | Final |
| 10-08 | Max length 1024 tokens (longer examples dropped) | Larger limit, or pruned schema | Revisit with Agent 1 pruned context |
| 10-08 | Multi-join over-sampled x2 | x1 or other factors | Untested design choice |
| 10-08 | Plain-text prompt template | Chat template | Must stay identical for LoRA and HydraLoRA |
| 10-14 | Headline metric: execution accuracy (shared `exec_match`); exact match is a secondary, normalised string match | Spider's official exact-set-match | Final for now |
| 10-14 | Greedy decoding, max 256 new tokens, evaluation with full schema | Sampling, pruned context | Pruned context comes later |
| 10-14 | Clean model output the same way for all models before scoring (strip code fences, cut at first `;`) | Chat template or few-shot prompt for the base model | Best effort: explanation text without a `;` would still fail |

**Needed for a fair final comparison (Execution Plan research protocol):** tune the LoRA baseline with the same budget as HydraLoRA; add a parameter-matched LoRA control; run 3 seeds; use a larger evaluation set (full Spider dev) so the multi-join and aggregation buckets have enough questions; paired statistics per bucket.

**HydraLoRA design notes (to decide):** train with routing from the gold complexity label; at inference compare routing with the live NL classifier (`classify_query`, Spider dev accuracy only 0.57) against oracle routing from the gold label, to separate router errors from architecture effects.

---

## Open items

- [x] Paired tests (bootstrap CI, exact McNemar) of LoRA vs base: done with `compare.py` (uses the shared `stats.py`); report in `results/compare_lora_vs_base.txt`.
- [ ] Commit the result files in `agent3_finetune/results/`.
- [ ] Build the HydraLoRA module (shared A, one B head per bucket, hard-coded routing); unit-test head routing and report the parameter count on a tiny subset first.
- [ ] Small rank / learning-rate sweep on one seed, then freeze the config for both architectures.
- [ ] Parameter-matched LoRA control.
- [ ] Build a larger evaluation set from the full Spider dev set (more multi-join and aggregation questions).
- [ ] 3 seeds for the final runs, with paired bootstrap / McNemar per bucket (`stats.py`).
- [ ] Re-train on Agent 1's pruned `ddl` and compare with this full-schema control (Ekanayake's Phase 8b).
- [ ] Over-sample or generate extra multi-join training examples; consider raising the length limit.
- [ ] Confirm base model and shared config with Wathsala; confirm the handoff format with Ekanayake.

---

## Where things live

- **Code:** this repo (branch `thathsarani-lora-baseline`), edited in VS Code, pushed with GitHub Desktop.
- **Training data (not in Git):** Google Drive `agent3/train.jsonl`, `agent3/val.jsonl`; evaluation inputs `agent3/eval_inputs.json`.
- **Run outputs (not in Git):** Google Drive `agent3/runs/<run name>/` (adapter, checkpoints, predictions).
- **Small result files (in Git):** `agent3_finetune/results/`.
- **Colab routine each session:** mount Drive, clone/pull the branch, install `peft accelerate`, remove `torchao`, then train or evaluate.
- **Evaluation routine:** `prepare` on the laptop, upload `eval_inputs.json` to Drive, `generate` in Colab, download `predictions.json` into `results/`, `score` on the laptop. Compare two runs with `python -m agent3_finetune.compare --a <A>_scored.json --b <B>_scored.json`.

## Environment notes

- Laptop: Intel Iris Xe (no NVIDIA GPU), 16 GB RAM, Windows. Training and generation run on Colab.
- Python 3.11.9 with a `venv` locally. The project folder is inside OneDrive; pause syncing if the laptop slows down.
- Run scripts as modules from the project root, for example `python -m scripts.get_spider`.

---

## AI use disclosure (for Appendix 3)

Claude (Anthropic) was used as a tutor and coding assistant for environment setup, Git workflow guidance, and drafting `build_dataset.py`, `train_lora.py` and `evaluate.py`, and for help interpreting results. The code was run and the outputs above were produced and checked by the author.