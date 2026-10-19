# Agent 3 Progress Log: LoRA vs HydraLoRA

**Owner:** K.G.Y.V. Thathsarani (IT23404250)
**Branch:** `thathsarani-hydra` (built on `thathsarani-lora-baseline`, which is kept as a snapshot of the baseline phase)
**Project:** J26-DS-336, Distributed Multi-Agent SLM Framework

How to read this file: every entry says what was done, what was found and what was decided. Dates marked "(reported)" are approximate; the exact history is in GitHub Desktop under History.

---

## Current status

| Phase (Execution Plan / WBS) | Status |
|---|---|
| Requirement analysis | Done (`REQUIREMENTS_TRACE.md`) |
| Dataset (Spider train, labelled by the shared taxonomy) | Done (full-schema context). **Synthetic, Python-generated pairs promised in the proposal: not done** |
| Standard LoRA baseline on a placeholder base | Done (two runs: first PEFT run and same-script run, seed 42) |
| HydraLoRA module (shared A, one B head per bucket, hard-coded routing) | Done, tested (7 self-checks, 10 + 13 automatic tests) |
| Initial comparison on the placeholder model | **Done (seed 42): HydraLoRA not better than LoRA; heads specialise; router accuracy is the practical limit** |
| Re-validation on Agent 2's real base model | Waiting for Wathsala's checkpoints |
| Winner and runner-up identified | **Preliminary: LoRA = winner, HydraLoRA (true routing) = runner-up** |
| Hand-off packaging for Agent 4 | Not started |
| Live Head-Selection and Generation sub-agents (`generate()`) | Not started |

**Next step:** presentation material for 22 October; then packaging, the `generate()` sub-agent, and the optional follow-ups (synthetic multi-join data, 3 seeds, larger evaluation set).

---

## Results (placeholder base Qwen2.5-1.5B-Instruct, seed 42, full-schema context)

Execution accuracy, pooled Spider dev + Chinook, 128 scored questions (95% Wilson interval for ALL).

| Bucket | Untrained base | LoRA, first run (PEFT) | **LoRA, same script** | **HydraLoRA, true label** | HydraLoRA, live classifier |
|---|---|---|---|---|---|
| simple | 0.55 (17/31) | 0.74 (23/31) | 0.77 (24/31) | 0.71 (22/31) | 0.55 (17/31) |
| single-join | 0.29 (9/31) | 0.68 (21/31) | 0.74 (23/31) | 0.65 (20/31) | 0.35 (11/31) |
| multi-join | 0.25 (8/32) | 0.19 (6/32) | 0.16 (5/32) | 0.16 (5/32) | 0.12 (4/32) |
| aggregation | 0.56 (19/34) | 0.59 (20/34) | 0.59 (20/34) | 0.56 (19/34) | 0.53 (18/34) |
| **ALL** | 0.41 [0.33-0.50] (53/128) | 0.55 (70/128) | **0.56 (72/128)** | **0.52 (66/128)** | 0.39 (50/128) |

Normalised exact match overall (stricter than Spider's official metric): base 0.19, LoRA 0.37, HydraLoRA true label 0.40, live classifier 0.29. Exact match is unreliable for multi-join, so execution accuracy is the headline metric.

### Paired tests (difference A - B, 95% bootstrap CI, exact McNemar; `compare.py` with the shared `stats.py`)

| Comparison | Bucket | Difference [CI] | A only / B only | p |
|---|---|---|---|---|
| LoRA - base | ALL | +0.13 [+0.05, +0.23] | 29 / 12 | 0.012 |
| LoRA - base | single-join | +0.39 [+0.19, +0.58] | 13 / 1 | 0.002 |
| LoRA - base | multi-join | -0.06 [-0.25, +0.09] | 3 / 5 | 0.727 |
| **HydraLoRA (true) - LoRA** | ALL | **-0.05 [-0.11, +0.02]** | 5 / 11 | 0.210 |
| HydraLoRA (true) - LoRA | simple | -0.06 [-0.16, 0.00] | 0 / 2 | 0.500 |
| HydraLoRA (true) - LoRA | single-join | -0.10 [-0.23, +0.03] | 1 / 4 | 0.375 |
| HydraLoRA (true) - LoRA | multi-join | 0.00 [-0.16, +0.16] | 3 / 3 | 1.000 |
| HydraLoRA (true) - LoRA | aggregation | -0.03 [-0.12, +0.06] | 1 / 2 | 1.000 |
| **HydraLoRA (live) - LoRA** | ALL | **-0.17 [-0.25, -0.09]** | 4 / 26 | <0.001 |
| HydraLoRA (live) - LoRA | single-join | -0.39 [-0.58, -0.23] | 0 / 12 | <0.001 |
| HydraLoRA (live) - LoRA | simple | -0.23 [-0.39, -0.10] | 0 / 7 | 0.016 |
| HydraLoRA true - live | ALL | +0.12 [+0.06, +0.20] | 18 / 2 | <0.001 |

### Head specialisation (every question sent to ONE fixed head; execution accuracy; `head_matrix.py`)

| Question bucket | simple head | single-join head | multi-join head | aggregation head | LoRA |
|---|---|---|---|---|---|
| simple | **0.71** (22/31) | 0.06 (2/31) | 0.10 (3/31) | 0.32 (10/31) | 0.77 |
| single-join | 0.16 (5/31) | **0.65** (20/31) | 0.42 (13/31) | 0.39 (12/31) | 0.74 |
| multi-join | 0.03 (1/32) | 0.03 (1/32) | **0.16** (5/32) | 0.06 (2/32) | 0.16 |
| aggregation | 0.35 (12/34) | 0.29 (10/34) | 0.29 (10/34) | **0.56** (19/34) | 0.59 |
| ALL | 0.31 | 0.26 | 0.24 | 0.34 | 0.56 |

The best fixed head is on the diagonal in every row, so the heads do specialise (clearly for simple and single-join; small counts for multi-join). A single shared LoRA still does as well as or better than the best head in every bucket.

### Cost numbers

| Item | LoRA | HydraLoRA |
|---|---|---|
| Trainable parameters (rank 16) | 18,464,768 (1.18%) | 49,430,528 (3.10%), 2.68x LoRA; 0.67x four separate LoRA adapters (73.9M) |
| Parameter-matched LoRA (not yet run) | rank 43 = 49,624,064 | |
| Training time (969 steps) | 7,402 s (2 h 03 min) | 7,109 s (1 h 59 min) |
| Training peak GPU memory | 6.82 GB | 7.28 GB (under the 8 GB budget, little room) |
| Inference peak GPU memory | 3.73 GB | 3.85 GB |
| Validation loss | 0.294 | 0.253 |
| Generation speed (148 questions, batch 4, T4) | 155 s (about 1.0 s/question) | 98-235 s depending on the head used |
| Adapter size in fp16 (calculated) | about 37 MB | about 99 MB |

Training data per head after dropping too-long rows (5,162 rows): simple 1,503, single-join 669, multi-join 654 (327 unique, each counted twice), aggregation 2,336.

---

## Work log

### 2026-10-17 (reported): Fair comparison, fixed-head test, results organised
- Same-script LoRA run (`lora_r16_seed42`) finished: 969 steps, 7,402 s, peak 6.82 GB, validation loss 0.294.
- Evaluated LoRA and ran HydraLoRA five more times (one fixed head each for the four heads, plus plain LoRA). The fixed-head option of `evaluate.py` worked on the GPU at the first attempt.
- Scored with `evaluate.py score`, compared with `compare.py`, built the head table with `head_matrix.py`.
- Results folder reorganised into `results/lora/`, `hydra/`, `base_model/`, `comparisons/`; `tests/test_agent3.py` now searches subfolders (`rglob`).
- Findings 1-6 below.

### 2026-10-16/17 (reported): HydraLoRA full run and evaluation
- `train.py --method hydra`: 969 steps, 7,109 s, peak 7.28 GB, 49,430,528 trainable parameters, validation loss 0.253.
- `evaluate.py` extended: loads adapters from `train.py`, routes each batch to a head (`--routing oracle|nl|<bucket>`), stores the live classifier's label (`nl_complexity`), prints how often the live classifier agrees with the true label (87/148 = 0.59).
- Evaluated with true-label routing and with the live classifier.

### 2026-10-15/16 (reported): Unified training script, HydraLoRA module, tests, new branch
- `hydra.py`: `HydraLinear` (frozen base, shared A, one B head per bucket), `Router`, save/load, routing with fallback (unknown, empty or missing label goes to the `single-join` head). With one head it equals standard LoRA, so LoRA and HydraLoRA share one code path.
- `train.py` + `configs/shared_config.json` (version-controlled settings, `config_used.json` saved with every run, checkpoint and resume, total time and peak memory logged across resumes).
- Tests: `tests/test_hydra.py` (10, pass in Colab), `tests/test_agent3.py` (13, pass on the laptop; the test found and led to a fix of a trailing-space bug in `normalise`).
- `REQUIREMENTS_TRACE.md`, `HANDOVER_Agent3.md` written. Branch `thathsarani-hydra` created and published; draft pull request for Teams (confirm it is a draft).

### 2026-10-14 (reported): Evaluation of the first LoRA run, scoring fix, paired tests
- `evaluate.py`, `compare.py` written. The first base-model score (0.05) was a code-fence artefact; `clean_sql` added; corrected base = 0.41.

### 2026-10-08 to 10-13 (reported): Colab, first LoRA run
- Kaggle verification failed, Colab (T4) used. `train_lora.py` (PEFT). Fixes: removed `torchao`, `warmup_steps`, batch 2 x accumulation 8 (batch 4 ran out of memory under the 8 GB cap). First LoRA run: 969 steps, validation loss 0.288, 18,464,768 parameters.

### 2026-10-06: Setup and dataset
- Python 3.11.9, venv, tests; `venv/` added to `.gitignore`; `build_dataset.py`.

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

140 databases, 14 held out (seed 42). With the full schema, 669 of 5,831 training rows (11.5%) exceeded 1,024 tokens and were dropped (simple 141, single-join 107, multi-join 96, aggregation 325).

---

## Findings

1. **The hypothesis "HydraLoRA beats standard LoRA" was not supported in this setup.** With true routing: 0.52 vs 0.56, difference -0.05 [-0.11, +0.02], p = 0.21; no bucket differs detectably; multi-join identical (5/32 each). The overall interval's upper end (+0.02) makes a large gain unlikely; a small gain or loss cannot be excluded.
2. **The heads do specialise** (head table), clearly on simple and single-join, but a single shared adapter does as well or better in every bucket. Specialisation is not the same as improvement.
3. **Router accuracy is the practical limit.** The live classifier agrees with the true label on only 59% of questions; used for routing, HydraLoRA loses 17 points against LoRA (4 wins to 26, p < 0.001), mostly on simple and single-join questions.
4. **Plain LoRA clearly helps over the untrained base overall (+0.13, p = 0.012) and on single-join (0.29 to 0.74), but not on multi-join or aggregation.** Multi-join stays at about 0.16 for every fine-tuned variant (untrained base 0.25, difference within noise).
5. **Winner and runner-up (preliminary):** LoRA wins on simplicity (2.7x fewer parameters, no router, -0.46 GB training peak) and on accuracy (not worse); HydraLoRA with true routing is the runner-up.
6. **Both training loops agree:** the first PEFT LoRA (70/128) and the same-script LoRA (72/128) give the same result, so the training code is not a hidden factor. Both models show the same large gap between training loss (about 0.02) and validation loss (0.25-0.29), so overfitting is not specific to HydraLoRA; HydraLoRA's validation loss is lower (0.253 vs 0.294), yet its accuracy is not better.
7. **Limits (state openly):** one seed; about 31 questions per bucket (only large differences are detectable, roughly 20-25 points with almost no losses the other way); one placeholder base model; untuned rank, learning rate and epochs; the multi-join head had only 654 training rows; the model never saw the largest database schemas (11.5% of rows dropped); exact match is unreliable for multi-join; evaluation uses the full schema, not Agent 1's pruned context.
8. **Data source differs from the proposal:** the proposal promises a synthetic, Python-generated dataset; Spider train (human-written, public) was used instead. Synthetic multi-join data is a natural follow-up because the multi-join head learned from the least data.

---

## Decisions and alternatives

| Date | Decision | Alternatives not (yet) tested | Status |
|---|---|---|---|
| 10-06 | Split by database; reuse `classify_sql`; remove eval questions from training | random split | final |
| 10-06 | Python 3.11.9 | 3.14 | final |
| 10-08 | Colab T4 instead of Kaggle | Kaggle (failed) | final |
| 10-08 | Placeholder base Qwen2.5-1.5B-Instruct | other 0.5-1.5B models | suggestion; Wathsala's final model overrides |
| 10-08 | Rank 16, alpha = 2 x rank, lr 2e-4, 3 epochs, seed 42, batch 2 x 8, max_len 1024, multi-join x2 | other ranks, learning rates, epochs (including 1 epoch, since training loss is far below validation loss) | untuned defaults |
| 10-14 | Execution accuracy is the headline metric; exact match secondary | Spider's official exact-set-match | final for now |
| 10-14 | Clean outputs of all models the same way (strip code fences, cut at first `;`) | chat template or few-shot for the base model | best effort |
| 10-15 | Same code path for LoRA and HydraLoRA (one head vs four) | PEFT for LoRA only (confounded) | final |
| 10-15 | Fallback head `single-join` for unknown or missing labels | most-data head, or the average of all heads | design choice, not evaluated |
| 10-17 | Winner = LoRA, runner-up = HydraLoRA (true routing), preliminary | decide after 3 seeds and Agent 2's models | preliminary |
| 10-17 | Results organised per model under `results/` | flat folder | final |

---

## Open items

- [ ] Presentation material (22 October); confirm presentation length with the team.
- [ ] Hand-off packaging: winner and runner-up as versioned artefacts (weights, config, evaluation log) for Agent 4.
- [ ] `generate(question, ddl, hint=None) -> sql` live sub-agent with head selection; plug into `harness.create_app`.
- [ ] Latency, memory and size benchmark script (non-functional evidence).
- [ ] `requirements-colab.txt` with recorded library versions (`pip list` in Colab).
- [ ] Re-validation on Wathsala's distilled and native bases (ask for a date and the model name).
- [ ] 3 seeds for the final comparison; a larger evaluation set (full Spider dev, about 1,000 questions) so per-bucket differences can be detected.
- [ ] Parameter-matched LoRA (rank 43) to answer "is it just more parameters?".
- [ ] One-epoch versions of both models (training loss far below validation loss).
- [ ] Synthetic multi-join data (decide with the supervisor): generator, then retrain and compare.
- [ ] Train on Agent 1's pruned schema context and compare with full-schema (Ekanayake's Phase 8b).
- [ ] Confirm the pull request is a draft; ask the leader whether branch commits count and who merges.

---

## Where things live

- **Code:** this repo, branch `thathsarani-hydra`, edited in VS Code, pushed with GitHub Desktop.
- **Small result files (in Git):** `agent3_finetune/results/lora/`, `hydra/`, `base_model/`, `comparisons/`.
- **Large files (Google Drive, not in Git):** `agent3/train.jsonl`, `val.jsonl`, `eval_inputs.json`; `agent3/runs/<run>/` (adapter, checkpoint, predictions). Drive was 10.08 of 15 GB used: delete old `smoke*` folders if space runs short.
- **Colab routine each session:** mount Drive first, clone the branch (`git clone -b thathsarani-hydra`), install `peft accelerate pytest`, remove `torchao`, then train or evaluate.
- **Evaluation routine:** `prepare` on the laptop, upload `eval_inputs.json` to Drive, `generate` in Colab, download `predictions*.json` into `results/<model>/`, `score`, `compare`, `head_matrix` on the laptop.

## Environment notes

- Laptop: Intel Iris Xe (no NVIDIA GPU), 16 GB RAM, Windows; Python 3.11.9 venv; project inside OneDrive.
- In PowerShell paste long commands one at a time (several pasted lines can break).

---

## AI use disclosure (for Appendix 3)

Claude (Anthropic) was used as a tutor and coding assistant for environment setup, Git workflow, drafting `build_dataset.py`, `train_lora.py`, `hydra.py`, `train.py`, `evaluate.py`, `compare.py`, `head_matrix.py`, the tests and the documents, and for help interpreting results. The code was run and the outputs were produced and checked by the author.
