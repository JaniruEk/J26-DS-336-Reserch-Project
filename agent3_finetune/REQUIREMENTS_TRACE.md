# Agent 3: Requirements Traceability (status as of 2026-10-15)

Component: **Fine-tuned generation (LoRA vs complexity-routed HydraLoRA + live SQL generation)**
Owner: K.G.Y.V. Thathsarani (IT23404250)

Purpose: every requirement from the individual proposal, mapped to the code that implements it, the test or measurement that proves it, and an honest status. Status values: **Done**, **Partial**, **Not started**.

---

## 1. Component breakdown

| Part | Job | File | Status |
|---|---|---|---|
| Dataset builder | Labelled Spider-train data, no eval leakage, split by database | `build_dataset.py` | Done |
| Adapter module (LoRA / HydraLoRA) | Shared A, one B per complexity bucket, router; one head = standard LoRA | `hydra.py` | Written, self-test pending |
| Training | Same loop for LoRA, HydraLoRA and the parameter-matched control | `train.py` + `configs/shared_config.json` (first LoRA run used `train_lora.py`) | Written, smoke test pending |
| Head-selection sub-agent | Complexity label (from Agent 1) to head index, with safe fallback | not yet | Not started |
| SQL generation sub-agent | `generate(question, ddl, hint) -> sql`, pluggable into the harness | not yet | Not started |
| Evaluation and comparison | Execution accuracy and exact match per bucket; paired statistics | `evaluate.py`, `compare.py` | Done |
| Artefact packaging | Winner and runner-up as versioned artefacts for Agent 4 | not yet | Not started |

---

## 2. Functional requirements

| ID | Requirement (short) | Implemented by | Test / evidence | Status | Gap / next step |
|---|---|---|---|---|---|
| FR1 | Fine-tune base SLM with standard single-adapter LoRA (control) | `train_lora.py` | `results/lora_seed42_run_info.json`, `compare_lora_vs_base.txt` | Done (preliminary) | Re-train with the unified loop so LoRA and Hydra share identical code |
| FR2 | Fine-tune the same base with HydraLoRA (complexity-specialised heads) | `hydra.py` | Self-test: `python -m agent3_finetune.hydra` | Partial | Run self-test in Colab; add to training script; train |
| FR3 | Route each training and inference example to the correct head using the shared complexity classifier | Training: `complexity` label from `classify_sql` (in the dataset). Inference: `classify_query` from Agent 1 | Unit tests for label to head mapping; evaluation with the live classifier and with true labels | Partial | Integrate inference routing; add fallback (see NFR-Reliability) |
| FR4 | Separately report exact match, JOIN/aggregation accuracy and trainable parameter count, per bucket, both architectures | `evaluate.py`, `compare.py`, `run_info.json` | Report tables per bucket (multi-join and aggregation buckets = JOIN/aggregation accuracy) | Partial | Hydra results missing; add parameter counts to the comparison report |
| FR5 | Identify and package winner and runner-up as versioned artefacts | not yet | Manifest with version, config, hash and evaluation log; load test | Not started | Write `package_artifacts.py` |
| FR6 | Live per-query head selection and SQL generation, using the deployed configuration's architecture and weights | not yet | `generate()` end-to-end test through `harness.create_app(generate=...)` | Not started | Write the sub-agents and a deployment config file |

---

## 3. Non-functional requirements

| ID | Requirement (short) | How it is measured | Evidence so far | Status | Gap / next step |
|---|---|---|---|---|---|
| NFR-Performance | Fine-tuning completes within the compute/time budget on mid-range hardware | Total training time and peak GPU memory against the 8 GB budget | Smoke test: about 6 s/step, peak 5.31 GB. Full run: 969 steps, but the run was split across sessions, so total time and training peak were not recorded. Inference: 3.67 GB peak | Partial | The unified training script will log total time and peak memory |
| NFR-Accuracy | JOIN/aggregation accuracy reported with statistical comparison, not one aggregate | Paired bootstrap CI and exact McNemar per bucket (`compare.py`, shared `stats.py`) | LoRA vs base done (`compare_lora_vs_base.txt`) | Done for LoRA vs base | Apply to LoRA vs HydraLoRA; larger eval set for power |
| NFR-Reliability | Routing handles any complexity label without failure, including bucket-boundary cases | Unit tests with unknown, missing, upper-case and boundary labels (for example a join plus an aggregate) | `head_index` falls back to the `single-join` head for unknown, empty or missing labels instead of failing (a design choice, to be evaluated); tests in `tests/test_hydra.py` | Partial: written, tests to run | Run the tests. Alternative to evaluate later: the average of all heads |
| NFR-Reproducibility | Shared fine-tuning configuration is version-controlled | Config file in Git, fixed seeds, pinned library versions, same config for both architectures | Code is in Git; seed 42 and a seeded database split exist, but settings live in command-line defaults and library versions are not pinned (the repo's `requirements.txt` has no torch/transformers/peft) | Partial | `configs/shared_config.json` and `train.py` (saves `config_used.json` with every run) are written; library versions still to be recorded in `requirements-colab.txt` |

---

## 4. Tests (`tests/test_agent3.py` and `tests/test_hydra.py`: written; the torch-free ones were run, the rest are to be run)

| ID | Test | Covers |
|---|---|---|
| T1 | No training question appears in the evaluation sets | Dataset integrity |
| T2 | Train and validation share no database | Dataset integrity |
| T3 | Every example has a valid complexity label | FR3 |
| T4 | `clean_sql` removes code fences and text after `;`; normalisation ignores case and spacing | Evaluation |
| T5 | Confidence interval and paired-test helpers return expected values on known data | NFR-Accuracy |
| T6 | Label to head mapping, including unknown, empty, None, upper-case and whitespace labels | FR3, NFR-Reliability |
| T7 | Boundary queries (join plus aggregate, nested, no rows) get the expected bucket | NFR-Reliability |
| T8 | Hydra self-test: correct head reached, gradients isolated, one head equals LoRA | FR2 |
| T9 | Adapter save then load gives identical outputs | FR5 |
| T10 | Same seed gives the same dataset split | NFR-Reproducibility |

Measured (non-functional) checks: peak memory, latency per question (median and 95th percentile), adapter size on disk, training time.

---

## 5. Novelty claim (to be stated carefully)

HydraLoRA itself is not new (arXiv 2404.19245) and must be cited. The claim for this component:

> A **complexity-routed HydraLoRA for text-to-SQL** with a **hard-coded, auditable router**, evaluated **per complexity bucket** against a standard LoRA and a parameter-matched LoRA, under an **8 GB** hardware budget.

Link to the user requirement: regulated organisations need a local model that is accurate on hard queries and whose behaviour can be explained to auditors. A hard-coded router is predictable and explainable; a learned router is not.

Motivating evidence (preliminary, one seed): plain LoRA improved single-join queries (0.29 to 0.68, p = 0.002) but showed no detectable improvement on multi-join (0.25 to 0.19) or aggregation (0.56 to 0.59). HydraLoRA is presented as a hypothesis under test until its own results exist.

---

## 6. Practical usage

Scenario: an analyst at a regional bank asks a question in plain English; the SQL is produced and run on an on-premise server, so no data leaves the organisation.

| Question | Evidence (measured unless marked) |
|---|---|
| Fits modest hardware? | Inference peak 3.67 GB (T4), under the 8 GB budget |
| Fast enough? | About 1.2 s per question on average (148 questions in 172 s, batch of 4, on a T4, not the target RTX 3070 Ti) |
| Deployment size? | Base model about 3 GB plus adapter: about 37 MB (LoRA r=16, fp16) or 99 MB (HydraLoRA r=16, 4 heads, fp16). Calculated, not yet measured |
| Can it be trusted? | Not autonomously: execution accuracy is about 0.55, so a person reviews the SQL before acting on the result |

Intended operating mode: decision support with human review. The generated SQL is shown to the user, executed read-only, every step is logged by the shared harness, and errors go through the bounded retry loop.

Known limitations to state openly: single seed, small per-bucket evaluation sets (about 32 questions), the model never saw the largest database schemas (11.5% of training rows were too long), accuracy has not been measured on real enterprise databases, and the placeholder base model may be replaced by Agent 2's models.

---

## 7. Priority order until 22 October

| Priority | Item |
|---|---|
| Must | Hydra self-test passes; unified training script; HydraLoRA trained and evaluated (or shown as preliminary); `tests/test_agent3.py`; routing fallback; shared config file and recorded library versions; latency, memory and size measurements |
| Should | `generate()` sub-agent and a short live demo or recording; artefact packaging |
| After the presentation | Parameter-matched LoRA (rank 43), 3 seeds, larger evaluation set, pruned-context comparison |
