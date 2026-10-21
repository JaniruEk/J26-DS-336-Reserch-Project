# J26-DS-336 Project Status and Component Connections

**Status date:** 21 October 2026  
**Overall estimated completion:** approximately **60%**

This document records each member's completed work, remaining work, and current
connection to the shared application.

## 1. Current pipeline

```text
User question
      |
      v
Agent 2 question gate (optional)
      |
      v
Agent 1 schema retrieval and pruning
      |
      | pruned DDL, tables, columns, complexity label, trace
      v
Agent 3 generation slot
      |
      | currently phi3/Ollama or Agent 4 adaptive Qwen stand-in
      v
Agent 4 execution slot
      |
      | currently shared read-only SQL runner
      v
Answer, rows, or bounded retry
```

### Important current-state summary

- **Agent 1 is genuinely connected** to the FastAPI application.
- **Agent 2 is optionally connected** as a question gate.
- **Agent 3's real fine-tuned generator is not connected yet.**
- **Agent 4's adaptive Qwen model is connected as an experimental generator
  option**, but it is not yet quantized from Agent 3's final model.
- **Agent 4's final error-diagnosis and empty-result retry component is not
  connected yet.**
- The application currently works end to end using stand-in generation and
  execution components.

## 2. Agent 1 — Retrieval and column-level pruning

**Owner:** J.K.B. Ekanayake  
**Estimated completion:** **80–85%**

### Completed

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

### Remaining work

1. Re-run final evaluations using Qwen2.5-1.5B-Instruct.
2. Re-run evaluation using Agent 3's final fine-tuned model.
3. Re-run evaluation using Agent 4's final quantized model.
4. Complete complexity-adaptive context-width experiments.
5. Improve the complexity classifier using retrieved-table and FK features.
6. Extend evaluation to the full Spider development set where practical.
7. Confirm the DDL/JSON handoff format with Agent 3.
8. Complete final integration and dissertation result tables.
9. Ensure Agent 3 training uses the same value-hinted DDL format as the live
   application.

### Current connections

```text
Agent 1 -> FastAPI harness                         CONNECTED
Agent 1 -> Retrieval Explorer                     CONNECTED
Agent 1 -> question matching/off-topic check      CONNECTED
Agent 1 -> generation context/DDL                 CONNECTED
Agent 1 -> retry context                          CONNECTED
Agent 1 -> final Agent 3 model                    NOT CONNECTED
```

Agent 1 is the most complete and most integrated component.

## 3. Agent 2 — Knowledge distillation and foundation model

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

## 4. Agent 3 — LoRA versus HydraLoRA SQL generation

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
Agent 3 generation interface                     RESERVED in harness
Agent 3 real LoRA adapter -> FastAPI              NOT CONNECTED
Agent 3 HydraLoRA adapter -> FastAPI             NOT CONNECTED
Agent 3 winner -> Agent 4                        NOT CONNECTED
Agent 3 runner-up -> Agent 4                     NOT CONNECTED
```

The FastAPI generation slot already expects:

```python
generate(question, ddl, hint=None, dialect="SQLite") -> sql
```

The slot currently uses phi3 through Ollama by default, or Agent 4's adaptive
Qwen model when explicitly selected.

## 5. Agent 4 — Adaptive mixed-precision quantization and execution

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

## 6. Shared application and infrastructure

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
| Agent 3 generation | phi3 through Ollama by default |
| Alternative generation | Agent 4 adaptive Qwen, not fine-tuned for SQL |
| Agent 4 execution | Shared read-only SQL runner |
| Error diagnosis | Raw database error used as the retry hint |
| Deployment runtime | Development runtime; final GGUF deployment not complete |

## 7. Current runnable configurations

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

## 8. Required connection order

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

## 9. Final conclusion

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
