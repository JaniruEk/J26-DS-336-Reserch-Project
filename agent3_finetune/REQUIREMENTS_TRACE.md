# Agent 3: Requirements Traceability (status after the fair comparison, 2026-10-17)

Component: **Fine-tuned generation (LoRA vs complexity-routed HydraLoRA + live SQL generation)**
Owner: K.G.Y.V. Thathsarani (IT23404250)

Every requirement from the individual proposal, mapped to the code that implements it, the test or measurement that proves it, and an honest status: **Done**, **Partial**, **Not started**.

---

## 1. Component breakdown

| Part | Job | File | Status |
|---|---|---|---|
| Dataset builder | Labelled Spider-train data, no eval leakage, split by database | `build_dataset.py` | Done |
| Adapter module (LoRA / HydraLoRA) | Shared A, one B per complexity bucket, router with safe fallback; one head = standard LoRA | `hydra.py` | Done, tested |
| Training | One script for LoRA, HydraLoRA and the parameter-matched control, shared version-controlled config | `train.py`, `configs/shared_config.json` | Done (both runs, seed 42) |
| Head-selection sub-agent | Complexity label to head index with fallback | `hydra.head_index`; live classifier used in evaluation | Partial: logic and tests exist, harness wrapper not built |
| SQL generation sub-agent | `generate(question, ddl, hint) -> sql`, pluggable into the harness | not yet | Not started |
| Evaluation and comparison | Execution accuracy and exact match per bucket, paired statistics, head table | `evaluate.py`, `compare.py`, `head_matrix.py` | Done |
| Artefact packaging | Winner and runner-up as versioned artefacts for Agent 4 | not yet | Not started |

---

## 2. Functional requirements

| ID | Requirement (short) | Implemented by | Evidence | Status | Gap / next step |
|---|---|---|---|---|---|
| FR1 | Fine-tune a base SLM with standard single-adapter LoRA (control) | `train_lora.py` (PEFT), `train.py --method lora` | `results/lora/` (two runs, 70/128 and 72/128 correct) | **Done** | 3 seeds later |
| FR2 | Fine-tune the same base with HydraLoRA (complexity-specialised heads) | `hydra.py`, `train.py --method hydra` | `results/hydra/hydra_r16_seed42_run_info.json` | **Done** | |
| FR3 | Route each training and inference example to the correct head using the shared classifier | training: true label from `classify_sql`; evaluation: true label and Agent 1's `classify_query` | oracle and live-classifier runs; `router_fallbacks = 0` in every run | **Done** for training and evaluation | live per-query routing inside the harness (FR6) |
| FR4 | Report exact match, JOIN/aggregation accuracy and trainable parameters per bucket, both architectures | `evaluate.py`, `compare.py`, `head_matrix.py`, `run_info.json` | `results/comparisons/`; parameters 18,464,768 vs 49,430,528 | **Done** (multi-join and aggregation buckets = JOIN/aggregation accuracy) | larger evaluation set |
| FR5 | Identify and package winner and runner-up as versioned artefacts | winner/runner-up identified; packaging not built | Preliminary: **LoRA = winner, HydraLoRA (true routing) = runner-up** | **Partial** | write `package_artifacts.py` (weights, config, evaluation log, version, hash) |
| FR6 | Live per-query head selection and SQL generation using the deployed configuration | not yet | none | **Not started** | `generate()` sub-agent plus a deployment config; deployed choice would be plain LoRA (no router needed) |

Data requirement from the methodology: **synthetic, Python-generated question-SQL pairs** to fill thin buckets: **not done**. Spider train (human-written, public) was used and multi-join was over-sampled x2. Synthetic multi-join data is an optional follow-up (the multi-join head had only 654 training rows).

---

## 3. Non-functional requirements

| ID | Requirement (short) | Measurement | Evidence | Status | Note |
|---|---|---|---|---|---|
| NFR-Performance | Fine-tuning completes within the compute/time budget on mid-range hardware | training time and peak GPU memory against the 8 GB budget | LoRA 7,402 s (2 h 03), peak 6.82 GB; HydraLoRA 7,109 s (1 h 59), peak 7.28 GB; a memory cap of 8 GB is enforced in code | **Done** | measured on a Colab T4, not the target RTX 3070 Ti; HydraLoRA has little headroom |
| NFR-Accuracy | Statistical comparison, not one aggregate | paired bootstrap CI and exact McNemar per bucket | `compare_lora_vs_base.txt`, `compare_hydra_oracle_vs_lora.txt`, `compare_hydra_live_vs_lora.txt`, `compare_oracle_vs_live_routing.txt` | **Done** | about 31 questions per bucket: only large differences detectable |
| NFR-Reliability | Routing handles any label without failure, including boundary cases | unit tests with unknown, empty, missing, differently written labels; fallback counter in evaluation | `tests/test_hydra.py` (10 pass); `router_fallbacks = 0` on 148 questions; labels match `classify_sql` | **Done** (tested) | fallback head `single-join` is a design choice, not evaluated |
| NFR-Reproducibility | Shared fine-tuning configuration is version-controlled | config file in Git, `config_used.json` saved per run, fixed seeds, seeded database split | `configs/shared_config.json`; tests check that each run records seed and settings | **Partial** | library versions not yet recorded (`requirements-colab.txt`) |

---

## 4. Tests

| File | Tests | Result |
|---|---|---|
| `tests/test_agent3.py` | `clean_sql` (2), `normalise` (2), Wilson interval, end-to-end scoring, split by database, valid labels and schema, labels match the shared classifier, all buckets present, no evaluation question leaks into training, every recorded run within the 8 GB budget, every run records seed and configuration | **13 pass** (laptop) |
| `tests/test_hydra.py` | routing, gradient isolation, parameter counts and one-head equals LoRA; one head per bucket; head order matches the shared buckets; unknown labels never crash (6 cases); parameter numbers for the report | **10 pass** (Colab) |
| `python -m agent3_finetune.hydra` | 7 self-checks including fp16 on the GPU | **pass** (Colab) |

A test found a real bug (trailing space in `normalise`), which was fixed. Measured non-functional checks: peak memory, training time, inference time (155 s for 148 questions on a T4), adapter size (calculated), reproducibility fields.

---

## 5. Novelty claim (as supported by the evidence)

HydraLoRA itself is not new (arXiv 2404.19245). This component's contribution is a **controlled, per-bucket evaluation of complexity-routed HydraLoRA for text-to-SQL** against standard LoRA, with a hard-coded, auditable router, under an 8 GB budget, including how much the router's accuracy matters.

Link to the user requirement: regulated organisations need a local model that is accurate on hard queries and whose behaviour can be explained to auditors; a hard-coded router is predictable and explainable.

Measured outcome (preliminary: one seed, placeholder base, about 31 questions per bucket):
- The hypothesis "HydraLoRA beats standard LoRA" was **not supported**: 0.52 vs 0.56 execution accuracy, difference -0.05 [-0.11, +0.02], p = 0.21; multi-join identical (5/32).
- The heads **do specialise** (best head on the diagonal in all four rows), but one shared adapter does as well or better in every bucket.
- **Router accuracy is the practical limit**: Agent 1's classifier agrees with the true label 59% of the time, and routing with it costs 17 points (4 wins to 26 against LoRA, p < 0.001).
- Plain LoRA clearly improves single-join queries (0.29 to 0.74) but not multi-join or aggregation.

A well-measured neutral result is a valid dissertation result (the project states that negative results count).

---

## 6. Practical usage

Scenario: an analyst at a regional bank asks a question in plain English; the SQL is produced and run on an on-premise server, so no data leaves the organisation.

| Question | Evidence |
|---|---|
| Fits modest hardware? | Inference peak 3.73 GB (LoRA) and 3.85 GB (HydraLoRA) on a T4, well under the 8 GB budget; training peak 6.82 and 7.28 GB |
| Fast enough? | About 1.0 s per question (148 questions in 155 s, batch of 4, T4; not the target RTX 3070 Ti) |
| Deployment size? | Base model about 3 GB plus an adapter of about 37 MB (LoRA) or about 99 MB (HydraLoRA), fp16, calculated |
| Which variant to deploy? | **Plain LoRA**: smaller, no router, at least as accurate. HydraLoRA would depend on a classifier that is right only 59% of the time |
| Can it be trusted? | Not autonomously: execution accuracy about 0.56, so a person reviews the SQL before acting on the result |

Intended operating mode: decision support with human review; generated SQL is shown, executed read-only, logged by the shared harness, and errors go through the bounded retry loop.

Known limitations: one seed; small per-bucket samples; untuned rank, learning rate and epochs; the model never saw the largest database schemas (11.5% of training rows were too long); no real enterprise database; placeholder base model that Agent 2's models may replace; evaluation with the full schema, not Agent 1's pruned context.

---

## 7. Priority order until 22 October

| Priority | Item |
|---|---|
| Must | Presentation material from these results; packaging of winner and runner-up (FR5); latency, memory and size numbers |
| Should | `generate()` sub-agent and a short live demo (FR6); `requirements-colab.txt` |
| After | Parameter-matched LoRA (rank 43), 3 seeds, larger evaluation set, one-epoch runs, synthetic multi-join data, pruned-context comparison, re-validation on Agent 2's models |
