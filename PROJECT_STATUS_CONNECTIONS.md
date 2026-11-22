# J26-DS-336 Project Status and Component Connections

**Status date:** 22 November 2026 (Agent 1 and connection sections; other members' sections unchanged since 21 October 2026)  
**Overall estimated completion:** approximately **60%**

This document records each member's completed work, remaining work, and current
connection to the shared application.

## 1. User feedback and prototype trials

This section separates **recorded panel feedback and technical trials** from
formal external-user usability evidence. The repository does not currently
contain named external participants, consent records, task-completion times,
or completed user-interview forms. Therefore, the entries below must not be
reported as a completed user study.

### Recorded feedback and trials

| Who tried or reviewed it | Task performed | Where they struggled | Change made |
|---|---|---|---|
| Proposal/PP1 panel DS-P03, recorded in the team feedback notes | Reviewed the proposed four-agent system and asked how it would be used in practice | The four components and their boundaries were not clear; the panel also asked for a standalone application, a chatbot frontend, practical usage, wrong-input demonstrations, and testing feedback | Added the four-agent I/O breakdown, runtime/offline flow documentation, FastAPI application, Retrieval Explorer, chat frontend, pipeline trace, input validation, SQL safety guard, wrong-input plan, and held-out/unseen-database evaluation plan |
| Ekanayake's Agent 1 technical trials | Asked natural-language questions against Chinook, TPC-H, Spider, Northwind, and PostgreSQL schemas; compared retrieval modes and inspected kept/removed columns | Wide context distracted the small generator on simple questions; deep multi-join questions sometimes missed tables; coded or abbreviated column names were difficult; value-coded questions could produce empty results | Added complexity-adaptive context width, multi-anchor retrieval, column-level explanations, identifier segmentation, value hints with a privacy switch, schema-aware complexity features, missing-FK inference, and the Explorer trace |
| Agent 1 live harness smoke test | Asked “How many tracks does each genre have?” through the full retrieval/generation/retry flow | Pruning removed `Genre.Name`, so all bounded retries failed; retrying could not recover a column that was absent from the original context | Added richer retrieval/trace information and documented the need for retry-time re-retrieval or a wider retry context; this remains an open Agent 3/Agent 4 integration item |
| Team technical trials of the shared chat/API prototype | Submitted valid database questions, off-topic questions, invalid database keys, write attempts, multi-statement SQL, and value-coded questions | Off-topic words such as “in” or loose semantic similarity could falsely pass the original match gate; a multi-statement SQL string could bypass a first-word-only safety check; clients could previously submit arbitrary SQL for saved answers | Replaced loose matching with content-word/identifier matching, added single-statement and read-only enforcement, blocked writes and `WITH ... DELETE`, restricted answer saving to successful pipeline traces, and added CSV formula neutralisation |
| Wathsala's model trial in the application | Used the distilled Qwen2.5-1.5B model as the database/general question gate and tested prompt-injection classification | Free-text injection generation produced invalid labels for some inputs, and the application prompt was reconstructed rather than copied from the training record | Kept label-probability scoring as the reported evaluation method, marked the gate as optional, retained Agent 1 matching and SQL read-only protection as independent safeguards, and recorded that the SQL-oriented distillation handoff is still incomplete |
| Thathsarani's Agent 3 experiments | Compared base, LoRA, and HydraLoRA generation with true and predicted complexity labels | HydraLoRA performance dropped when the live complexity classifier routed to the wrong head; the real generator interface and final adapter packaging were not yet available | Recorded LoRA as the preliminary winner, HydraLoRA as the runner-up, added routing-specific evaluation, and kept the live FastAPI generator slot injectable until final checkpoints are delivered |
| Karunanayake's Agent 4 technical trial | Compared quantization configurations and ran the adaptive Qwen model through the application | The preliminary layer-sensitivity set was small; the adaptive model was not quantized from Agent 3's final fine-tuned model; raw database errors were not yet converted into targeted diagnoses | Added the `adaptive_qwen` experimental generator option, displayed quantization status in the UI, kept bounded retries, and documented final-model calibration, diagnosis, and empty-result retry as remaining work |

### What this feedback supports

- The frontend and trace were added in response to the panel's difficulty
  understanding the component boundaries and practical usage.
- The input checks, SQL guard, and off-topic gate were added or strengthened
  after technical trials exposed unsafe or misleading behaviour.
- The retrieval changes were driven by observed failures on simple questions,
  deep joins, unseen schemas, and coded values rather than by a claim that
  retrieval always improves execution accuracy.
- Agent 3 and Agent 4 changes are currently responses to controlled technical
  experiments, not to a completed external-user study.

### Feedback still required before final claims

The team still needs at least two documented user-task sessions. Each record
should identify the participant role (for example, analyst, DBA, or
supervisor), database/task, whether the task was completed, the observed
difficulty, the participant's comment, and the resulting change or rationale
for not changing the system. The final report should also record the date,
facilitator, prototype version, and whether the participant used the chat
frontend or the Explorer.

Until those records exist, the correct statement is:

> “The prototype has been reviewed by the proposal/PP1 panel and exercised
> through controlled technical trials by the project team. Formal external-user
> feedback has not yet been collected.”

## 2. Current pipeline

```text
User question
      |
      v
Agent 2 question gate (optional)
      |
      v
Agent 1 schema retrieval (width selector optional)
      |
      | selected DDL, tables, columns, complexity label, width, trace
      v
Agent 3 generation slot
      |
      | currently phi3/Ollama or Agent 4 adaptive Qwen stand-in;
      | Agent 3 adapter loader wired, not yet run with real adapter files
      v
Agent 4 execution slot
      |
      | currently shared read-only SQL runner
      v
Answer, rows, or bounded retry
(with a width selector, each retry gets the next wider schema)
```

### Important current-state summary

- **Agent 1 is genuinely connected** to the FastAPI application.
- **Agent 2 is optionally connected** as a question gate.
- **Agent 3's real fine-tuned generator is not connected yet.** A loader for
  her adapter exists (`J26_GENERATOR=agent3`), but the adapter files are not
  in the repository, so it has not run.
- **Agent 4's adaptive Qwen model is connected as an experimental generator
  option**, but it is not yet quantized from Agent 3's final model.
- **Agent 4's final error-diagnosis and empty-result retry component is not
  connected yet.**
- The application currently works end to end using stand-in generation and
  execution components.

## 3. Agent 1 — Retrieval and adaptive context width

**Owner:** J.K.B. Ekanayake  
**Estimated completion:** core retrieval **80–85%**; adaptive-width study
(the main claim since 21 November 2026): code and tests done, **no real model
run yet**.

### Main claim (approved 21 November 2026)

Agent 1 selects how much schema to show for each question (the *width*), and
learns the selection from the SQL results of the small model in use. The four
retrieval modes are now the fixed-width baselines:

| Width | Content | Existing mode |
|---|---|---|
| W1 | anchor table only | `semantic` |
| W2 | anchor tables + FK tables, columns pruned | `hybrid_pruned` |
| W3 | anchor tables + FK tables, all columns | `hybrid` |
| W4 | full schema | new |

Pruning is no longer the novelty claim; its result is "no loss, no gain".
Plan and run steps: `reports/agent1_width/README.md`.

### Completed (adaptive-width study, 21–22 November 2026)

- Width module `agent1_retrieval/width.py`: W1–W4 contexts, selector features
  (known before the SQL model runs), labels (narrowest width with correct
  SQL), fixed / complexity-rule / elbow / oracle baselines, paired statistics,
  cross-fitting with folds by database.
- Sweep and selector scripts: `scripts/width_sweep.py`,
  `scripts/width_selector.py`; Spider question sets via
  `python -m scripts.get_spider --width`.
- Selector in the application: `J26_WIDTH_SELECTOR`, new handoff key `width`,
  retry with the next wider width (log stage `agent1.wider`).
- Model-tokenizer token counts as an option (`J26_TOKENIZER`); tiktoken stays
  the default so earlier numbers reproduce.
- Whole-system evaluation script `scripts/e2e_eval.py` and Agent 4's
  calibration/test split `scripts/make_quant_split.py`.
- CLI options: `--live`, `--schema-classifier`, `--narrow-simple`,
  `--value-hints`, `--glossary`.
- Test suite on this machine (22 November 2026): 92 passed, 11 skipped
  (6 need a PostgreSQL copy via `J26_TEST_PG`; 5 need Agent 3's dataset build).

### Completed (core retrieval)

- Schema reflection and DDL rendering.
- Foreign-key graph traversal.
- Semantic, structural, hybrid, and hybrid-pruned retrieval modes.
- Multi-anchor retrieval for deeper joins.
- Column-level pruning with explanations for kept and removed columns.
- SQL complexity classification.
- Table and column precision/recall evaluation.
- Token-count and retrieval-latency measurement.
- Chinook, TPC-H, Spider, and Northwind evaluation.
- PostgreSQL support with a read-only database layer.
- Missing-FK inference.
- Value-coded column hints and per-database glossary support.
- Off-topic question matching.
- Structured Agent 1 handoff payload.
- FastAPI `/retrieve` and `/query` integration.
- Retrieval Explorer UI.
- Database upload/configuration support.
- Security improvements for read-only access and SQL execution.

### Current evidence

| Dataset | Column recall |
|---|---:|
| Chinook | 0.95 |
| TPC-H | 0.97 |
| Spider | 0.98 |
| Northwind | 0.99 |

Value hints improved the value-coded evaluation:

- Phi3: 0.31 to 0.69.
- Qwen2.5-Coder stand-in: 0.12 to 0.56.

These are stand-in model results. No adaptive-width number exists yet; none
may be reported until a `results/width/*.jsonl` file from a real run is
committed.

### Remaining work

1. Build the Spider question sets (`python -m scripts.get_spider --width`).
2. Width sweeps (the distraction curves): Qwen2.5-1.5B-Instruct first, then
   0.5B, 3B and 7B; Spider dev (full), Chinook and Northwind.
3. Train and test the learned width selector; compare with the best fixed
   width, the complexity rule, the elbow and the oracle.
4. Measure the selector's retrieval latency against the 500 ms target.
5. Run the width sweep and the whole-system evaluation with Agent 3's adapter
   (needs her adapter files).
6. Re-run evaluation using Agent 4's final quantized model.
7. Make the one end-to-end results table for PP2 (`scripts/e2e_eval.py`).
8. Confirm the DDL/JSON handoff format with Agent 3, including the new
   `width` key.
9. Ensure Agent 3 training uses the same value-hinted DDL format as the live
   application. Her adapters were trained on the full schema; the app sends
   Agent 1's selected schema.
10. Update the proposals and project scope for the new claim.

### Current connections

```text
Agent 1 -> FastAPI harness                         CONNECTED
Agent 1 -> Retrieval Explorer                     CONNECTED
Agent 1 -> question matching/off-topic check      CONNECTED
Agent 1 -> generation context/DDL                 CONNECTED
Agent 1 -> retry context                          CONNECTED
Agent 1 width selector -> FastAPI                 WIRED, no trained selector yet
Agent 1 wider-width retry                         WIRED, active only with a selector
Agent 1 complexity label -> Agent 3 head choice   WIRED, not run (adapter missing)
Agent 1 -> final Agent 3 model                    NOT CONNECTED
```

Agent 1 is the most integrated component. Its main research result (the
width study) is still to be measured.

## 4. Agent 2 — Knowledge distillation and foundation model

**Owner:** W.A.T. Wathsala  
**Estimated completion for the original SQL scope:** **45–50%**

### Completed

- Qwen2.5-7B teacher setup.
- Native Qwen2.5-1.5B student.
- Distilled Qwen2.5-1.5B student.
- Database/general question classification.
- Safe/malicious prompt-injection classification.
- Native-versus-distilled statistical comparison.
- Optional integration as the application question gate.

### Current evidence

| Task | Native | Distilled |
|---|---:|---:|
| Database/general classification | 0.988 | 0.994 |
| Prompt-injection detection | 0.836 | 0.948 |

The distilled model is currently useful as a stage-one question gate. It is
not yet the SQL-oriented foundation model required by the main research
pipeline.

### Remaining work

1. Build the SQL-oriented distillation dataset.
2. Generate SQL-related teacher outputs.
3. Filter teacher outputs using execution validity.
4. Train the SQL-distilled student.
5. Prepare the native SQL student control.
6. Add the gold-SQL control arm.
7. Freeze tokenizer, model revisions, seeds, and training configuration.
8. Deliver distilled and native SQL checkpoints to Agent 3.
9. Share the exact training prompts.
10. Re-run the comparison after Agent 3 fine-tunes both bases.
11. Include value-hinted schemas in the distillation prompts.

### Current connections

```text
Agent 2 distilled classifier -> optional question gate    CONNECTED
Agent 2 gate -> FastAPI /query                              CONNECTED
Agent 2 gate -> Pipeline Explorer                          CONNECTED
Agent 2 gate -> handoff log                                CONNECTED
Agent 2 SQL-distilled base -> Agent 3                     NOT CONNECTED
```

The important missing handoff is the SQL-distilled and native base checkpoints
for Agent 3.

## 5. Agent 3 — LoRA versus HydraLoRA SQL generation

**Owner:** K.G.Y.V. Thathsarani  
**Estimated completion:** **60–65%**

### Completed

- Spider training dataset construction.
- Complexity labels for training and evaluation.
- Standard LoRA training.
- HydraLoRA module with one head per complexity bucket.
- Hard-coded routing and safe fallback behaviour.
- Unit tests and training configuration.
- Execution-accuracy evaluation.
- Exact-match evaluation.
- Per-complexity-bucket evaluation.
- Paired statistical comparisons.
- Parameter, training-time, and memory measurements.
- Preliminary winner and runner-up identification.

### Preliminary result

| Configuration | Execution accuracy |
|---|---:|
| Base model | 0.41 |
| LoRA | **0.56** |
| HydraLoRA with true labels | 0.52 |
| HydraLoRA with live classifier | 0.39 |

Preliminary decision:

```text
Winner: LoRA
Runner-up: HydraLoRA with true complexity labels
```

This is still preliminary because it was produced on a placeholder base and
has not been validated using Agent 2's final SQL checkpoints.

### Remaining work

1. Receive Agent 2's SQL-distilled and native checkpoints.
2. Re-run LoRA on both bases.
3. Re-run HydraLoRA on both bases.
4. Freeze the final comparison configuration.
5. Add additional seeds if time and compute permit.
6. Add synthetic SQL pairs if required by the final methodology.
7. Package the winner and runner-up artefacts.
8. Implement the live head-selection wrapper.
9. Implement `generate(question, ddl, hint, dialect)`.
10. Connect the real generator to the FastAPI harness.
11. Train using Agent 1's value-hinted DDL format.
12. Re-run using Agent 1's pruned context.
13. Hand the final adapter artefacts to Agent 4.

### Current connections

```text
Agent 3 training/evaluation code                 CONNECTED to experiments
Agent 3 generation interface                     LOADER WIRED (J26_GENERATOR=agent3)
Agent 3 real LoRA adapter -> FastAPI              NOT RUN (adapter files not in git)
Agent 3 HydraLoRA adapter -> FastAPI             NOT RUN (adapter files not in git)
Agent 3 winner -> Agent 4                        NOT CONNECTED
Agent 3 runner-up -> Agent 4                     NOT CONNECTED
```

The FastAPI generation slot already expects:

```python
generate(question, ddl, hint=None, dialect="SQLite") -> sql
```

The slot currently uses phi3 through Ollama by default, or Agent 4's adaptive
Qwen model when explicitly selected. Since 21 November 2026,
`J26_GENERATOR=agent3` (with `J26_AGENT3_ADAPTER` and optional
`J26_AGENT3_BASE`) loads Thathsarani's adapter with her own
`agent3_finetune.hydra` code and training prompt, and passes Agent 1's
complexity label to choose the HydraLoRA head. It falls back to phi3 when the
adapter or torch is missing. Thathsarani should check this loader against her
training setup and send the adapter folders; her `thathsarani-hydra` branch is
not merged into `main`.

## 6. Agent 4 — Adaptive mixed-precision quantization and execution

**Owner:** K.M.I.N. Karunanayake  
**Estimated completion:** **50–55%**

### Completed

- FP16 baseline.
- Uniform INT8 baseline.
- Uniform INT4 baseline.
- Per-layer sensitivity analysis.
- Migration to Qwen2.5-1.5B-Instruct.
- Adaptive INT4/INT8 allocation.
- Six selected Qwen layers assigned INT8 and the remaining layers assigned
  INT4 in the current allocation.
- Bitsandbytes mixed-precision model construction.
- Quantization result files.
- Optional application generator integration.
- Quantization result display in the Pipeline Explorer.

The current adaptive model can be selected using:

```text
J26_GENERATOR=adaptive_qwen
```

### Remaining work

1. Add all required baselines:
   - FP16.
   - Uniform INT8.
   - Uniform INT4.
   - GGUF Q4_K_M.
   - Generic-sensitivity layer selection.
   - Random layer selection.
2. Use a larger calibration set.
3. Use continuous sensitivity scores.
4. Sweep the number of INT8 layers.
5. Check interactions between individually sensitive layers.
6. Quantize Agent 3's final winner.
7. Quantize Agent 3's runner-up for the cross-check.
8. Build and validate the final deployable GGUF configuration.
9. Measure model size, runtime memory, tokens per second, and latency in the
   intended deployment runtime.
10. Implement the error-diagnosis sub-agent.
11. Implement SQL error classification.
12. Implement empty-result diagnosis for coded values.
13. Produce targeted retry hints instead of forwarding only raw database errors.
14. Re-run the final test sets with the final model.

### Current connections

```text
Agent 4 adaptive Qwen -> FastAPI generation slot       CONNECTED experimentally
Agent 4 read-only SQL runner -> FastAPI                CONNECTED as stand-in
Agent 4 raw database error -> retry hint                CONNECTED
Agent 4 diagnosis -> targeted retry hint                NOT CONNECTED
Agent 4 empty-result diagnosis -> retry                 NOT CONNECTED
Agent 4 final quantized Agent 3 winner -> deployment    NOT CONNECTED
```

The current application execution path uses a shared read-only SQL runner.
This provides safety behaviour, but it is not yet Agent 4's final
error-diagnosis and execution sub-agent.

## 7. Shared application and infrastructure

### Connected components

| Connection | Status |
|---|---|
| User to FastAPI application | Connected |
| FastAPI to Agent 1 retrieval | Connected |
| Agent 1 to DDL/context handoff | Connected |
| Agent 2 optional gate to FastAPI | Connected |
| Current generator to SQL executor | Connected |
| SQL executor to bounded retry loop | Connected |
| Pipeline trace to Explorer/chat UI | Connected |
| Saved answers to dashboard/BI replay | Connected |
| PostgreSQL/read-only database layer | Connected |

### Stand-ins still in use

| Research component | Current implementation |
|---|---|
| Agent 3 generation | phi3 through Ollama by default (Agent 3 loader wired, adapter files missing) |
| Agent 1 width selection | Fixed width (no trained selector yet) |
| Alternative generation | Agent 4 adaptive Qwen, not fine-tuned for SQL |
| Agent 4 execution | Shared read-only SQL runner |
| Error diagnosis | Raw database error used as the retry hint |
| Deployment runtime | Development runtime; final GGUF deployment not complete |

## 8. Current runnable configurations

### Default demo

```text
Agent 1 retrieval
-> phi3 through Ollama
-> shared read-only SQL runner
-> raw-error retry
```

### Demo with Agent 2 question gate

```text
Agent 2 distilled question gate
-> Agent 1 retrieval
-> phi3 through Ollama
-> shared read-only SQL runner
```

Enable with:

```text
J26_GATE=kd_multitask
```

### Demo with Agent 4 adaptive model

```text
Agent 2 optional gate
-> Agent 1 retrieval
-> Agent 4 adaptive Qwen2.5-1.5B
-> shared read-only SQL runner
```

Enable with:

```text
J26_GENERATOR=adaptive_qwen
```

This demonstrates Agent 4's adaptive model, but it is not yet the final
four-agent research pipeline because Agent 3's final fine-tuned model is not
being used.

### Planned: Agent 3 adapter and width selector

```text
J26_GENERATOR=agent3
J26_AGENT3_ADAPTER=<folder with adapters.pt + adapter_meta.json>
J26_WIDTH_SELECTOR=agent1_retrieval/width_selector.joblib
```

Both parts are wired but not yet runnable: the adapter files and the trained
selector do not exist in the repository. Whole-system results for each
configuration come from `python -m scripts.e2e_eval`.

## 9. Required connection order

```text
1. Agent 2 creates SQL-distilled and native checkpoints
       |
       v
2. Agent 3 fine-tunes LoRA and HydraLoRA on both checkpoints
       |
       v
3. Agent 3 packages the winner and runner-up
       |
       v
4. Agent 4 quantizes the final winner and runner-up
       |
       v
5. Agent 4 implements diagnosis and empty-result retry
       |
       v
6. Replace the harness stand-ins
       |
       v
7. Run final end-to-end experiments
       |
       v
8. Complete dissertation evidence, discussion, and conclusions
```

## 10. Final conclusion

The project has a strong working prototype and substantial preliminary
research evidence. The current application is connected enough for a demo, but
the final research pipeline is not complete.

The principal dependency is:

```text
Agent 2 SQL base models
-> Agent 3 final fine-tuned adapters
-> Agent 4 final quantized model and diagnosis
-> final end-to-end evaluation
```

Until this chain is completed, current accuracy results should be described as
preliminary or stand-in-model results rather than final system results.
