# PP1 Panel Response — K.M.I.N. Karunanayake (IT23179912)

Component: **Agent 4 — SQL-task-sensitive mixed-precision quantization, and SQL execution with error diagnosis** | Project J26-DS-336 | Panel DS-P03
Answers the proposal-presentation comments for Progress Presentation 1. Rewritten 19 Oct 2026 from her branches (`unquantized_baseline`, `Inushki/feature/quantization-day4-clean`, `day5-clean`, `day6-layer-sensitivity`, `day7/allocate_precision` = PR #9) and the final scope in Execution Plan section 4 (adaptive mixed precision on Qwen2.5-1.5B-Instruct; **replaces QAT vs PTQ**). The earlier draft, written for QAT vs PTQ, is in git history. **[MEASURED]** = from her result files; **[TO RUN]** = not done yet.

---

## 1. The proposal panel comments and the PP1 answer

Comments: *"Don't have proper component breakdown. Not explained novelty properly (what's the importance of SLM over LM). Need to think about practical usage."*

| Panel comment | PP1 answer (one line) | Evidence to show | Section |
|---|---|---|---|
| No proper component breakdown | Offline: score each layer's sensitivity on SQL, allocate INT8/INT4, build one deployable model. Live: an Execution sub-agent and an Error-Diagnosis sub-agent inside the bounded retry. | Component diagram; Day 4–7 outputs per step | 4 |
| Novelty not explained (SLM over LM) | Uniform 4-bit breaks SQL in a way it doesn't break chat: one wrong character in an identifier fails the query. I keep the layers SQL depends on at INT8, chosen by SQL-task sensitivity rather than generic sensitivity. | INT4 accuracy loss with garbled identifiers; per-layer sensitivity | 2, 3 |
| Practical usage | The quantized model is what fits the bank's mid-range GPU next to the adapters; the live sub-agents run SQL safely and turn errors into fixes. | Memory per configuration; read-only guard; retry demo | 6 |

---

## 2. Novelty

**Task-specific mixed precision for SQL generation:** measure how much each transformer layer matters *for SQL* (per complexity bucket), keep the most sensitive layers at INT8 and the rest at INT4, and test whether that beats choosing layers by **generic** sensitivity.

| Prior work | What it does | Difference |
|---|---|---|
| HAWQ / HAWQ-V2, OWQ, SpQR, SliM-LLM | Mixed precision chosen by generic signals (Hessian, outliers, perplexity) | Sensitivity measured on the target task, SQL, per complexity bucket |
| llama.cpp `Q4_K_M` | Fixed heuristic: some tensor types kept at higher precision | A baseline to beat, not a competitor to ignore |
| "How Small Can You Go?" (arXiv 2607.25583) | Quantization of a 60M model | Different scale and task |

**Say:** "Mixed precision is not new. The question is whether layers chosen by SQL-task sensitivity keep more SQL accuracy per unit of memory than generic choices, especially on joins and aggregations." Verify these citations before using them.

**The test that makes it a finding:** the same number of INT8 layers chosen three ways: by SQL sensitivity, by generic sensitivity, and at random (several draws). Without the random control, "sensitivity helps" is not shown.

---

## 3. Why a small model, and why SQL makes quantization harder

- **An SLM has to be compressed.** The on-premise model must fit one mid-range GPU together with Agent 3's adapters and leave room to serve requests; quantization is how.
- **A small model has less redundancy.** Each layer carries more of the work, so rounding errors in the wrong layers cost more than in a large model.
- **SQL is unforgiving.** In chat, a slightly wrong word is still readable; in SQL, one wrong character in a table name fails the query. Her preliminary run shows this directly: uniform 4-bit lost 8 of 100 questions, and its failures are mostly **garbled identifiers** (`singer_inatra_concert`) and broken keywords (`BETWEANT`). **[MEASURED]**

**One line for the panel:** "A large model on a big server can stay at full precision. A small model on the bank's GPU must be compressed, and SQL breaks on a single wrong character, so where the precision goes matters."

---

## 4. Component breakdown

| # | Part | Decision | Input → Output |
|---|---|---|---|
| Offline 1 | Error-rate metrics | Is a query valid, and is it right? | predicted + gold SQL → syntax validity (`EXPLAIN`), execution match, error class (wrong join / column / aggregation / group by), per complexity bucket |
| Offline 2 | Layer sensitivity | Which layers does SQL depend on? | model + calibration questions (Spider **train**) → damage score per layer when that layer alone is INT4 |
| Offline 3 | Precision allocation | Which layers stay INT8? | sensitivity ranking + number of INT8 layers *k* → per-layer bit-width plan; *k* swept for a memory-vs-accuracy curve |
| Offline 4 | Deployable model | Does it run as shipped? | plan → one GGUF file with per-tensor types for llama.cpp; accuracy, memory and speed re-measured |
| Live 1 | Execution sub-agent | Run the SQL safely | candidate SQL → rows, or an error (read-only, one statement, timeout, non-SELECT refused) |
| Live 2 | Error diagnosis | What went wrong, and what hint fixes it? | DB error or empty result → error class + hint back to Agent 3, within the bounded retry |

**Diagram:** the four offline steps in a row ending in the deployable model, and the two live boxes with the retry arrow back to Agent 3, in draw.io, black and white.

---

## 5. Preliminary results on Phi-3 Mini [MEASURED]

`microsoft/Phi-3-mini-4k-instruct`, greedy decoding, **100 questions on one database (concert_singer)**: 19 easy, 49 medium, 32 hard. Execution accuracy compares result lists in order.

| Configuration | Execution accuracy | Exact match | Peak memory vs FP16 | Mean latency |
|---|---|---|---|---|
| FP16 | 75 / 100 | 33 | 100% | 41.5 s (likely CPU offload) |
| bitsandbytes INT8 | 79 / 100 | 33 | 86% (−14%) | 10.1 s |
| bitsandbytes INT4 (NF4) | 67 / 100 | 31 | 53% (−47%) | 5.3 s |

- **Error analysis (Day 5):** the FP16 predictions re-scored with an order-insensitive comparison give 83/100. The 17 errors break down as unclassified result mismatch 6, wrong join 3, wrong column 3, syntax 3, wrong aggregation 1, wrong group by 1.
- **Layer sensitivity (Day 6):** each of the 32 layers fake-quantized to 4-bit alone, on 25 questions (baseline 21/25). The largest drop is layer 29 (3 questions lost). Only 5 questions ever changed across all 32 layers, and 13 layers scored negative (quantizing them "helped").
- **Allocation (Day 7):** the top 4 layers (11, 14, 29, 31) go to INT8 and the rest to INT4. This is a plan only; the mixed model has not been built.

**Honest reading:**
- INT4 saves about half the memory and costs 8 points, mostly through garbled identifiers.
- INT8 vs FP16 (79 vs 75) is within noise.
- On 25 questions one question is 4 points, so the current layer ranking is **noise-level**. Layer 11 beat layers 17 and 19 only on a tie-break.

These are preliminary. The study itself moves to Qwen2.5-1.5B with a calibration split and a continuous score.

---

## 6. Practical usage

- **Fits the hardware it must run on.** INT4 roughly halves model memory, which leaves room for Agent 3's adapters and request batching on one mid-range GPU in the bank's own data centre.
- **Safe execution on live data.** Read-only connection, one statement per call, a timeout, and a refusal (not a retry) of anything that isn't a SELECT. The harness stand-in already enforces this, and her sub-agent must keep it by calling `agent1_retrieval/db.py`.
- **Errors become fixes.** Instead of showing the analyst "no such column", the Error-Diagnosis sub-agent classifies the error and sends Agent 3 a targeted hint.
- **Empty results are checked.** A filter that returns 0 rows (`Discontinued = 'yes'` when the data holds `'0'`/`'1'`) triggers one look-up of the real values and one retry with a hint. This is a silent failure no database error reveals.
- **Example the error-diagnosis step targets** (team chat demo): "How many tracks does each genre have?" failed 3 times because phi3 kept joining `Album.GenreId`, a column that does not exist. A diagnosis that says "GenreId is in Track, not Album" is exactly what the raw-error hint lacks.

---

## 7. Next steps, in order

| # | Step | Why |
|---|---|---|
| 1 | Switch `MODEL_ID` to Qwen2.5-1.5B-Instruct; evaluate on the shared `eval/*.json` sets (Spider dev, Chinook) with the shared `exec_match` | Same base and test sets as the rest of the team; more than one database |
| 2 | Same `max_new_tokens` for every configuration; one scorer | FP16 used 100 tokens and the quantized runs 128 |
| 3 | Uniform baselines in llama.cpp GGUF (`Q8_0`, `Q4_0`, `Q4_K_M`) as well as bitsandbytes | The shipped runtime decides real memory and speed |
| 4 | Sensitivity on a Spider **train** calibration split, scored continuously (log-likelihood of the gold SQL, or KL to FP16), per complexity bucket; re-run on a second sample for stability | 25-question execution accuracy is noise |
| 5 | Sweep *k* INT8 layers; controls: random layers (several draws) and generic-sensitivity layers | Shows whether SQL sensitivity actually helps |
| 6 | Build the mixed GGUF and run it in the harness | Phase 6 deliverable |
| 7 | Error-Diagnosis and empty-result sub-agents plugged into the harness retry (`create_app(execute=...)`) | Live component |
| 8 | Re-run on Agent 3's fine-tuned winner, then cross-check on the runner-up | Final allocation |

Commit the evaluation questions and prediction files the Day 5 analysis used (currently gitignored), so the results can be reproduced from the repository.

---

## 8. Limitations to state

- Preliminary results use Phi-3 Mini on 100 questions from one database. They must not be described as "Spider" results.
- Fake 4-bit (symmetric, per row) is not NF4 or GGUF. The deployable format may behave differently.
- The FP16 latency is probably inflated by CPU offload. Hardware was not recorded, so record the GPU beside every result from now on.
- No QAT is planned any more. The scope changed to mixed precision, so the proposal's QAT vs PTQ comparison must be explained as a scope change.

---

## 9. 2-minute script (about 230 words)

> Good morning. I'm K.M.I.N. Karunanayake, and my component is Agent 4: making the model small enough to run on the bank's own hardware, and running its SQL safely.
>
> A small model on a mid-range GPU has to be compressed. But SQL is unforgiving: one wrong character in a table name and the query fails. In my preliminary run on Phi-3, uniform 4-bit roughly halved the memory but lost 8 of 100 questions, mostly through garbled identifiers.
>
> So instead of one bit-width for everything, I measure how much each layer matters for SQL, keep the sensitive layers at 8-bit and put the rest at 4-bit. Mixed precision itself exists. My question is whether choosing layers by SQL-task sensitivity beats generic choices and random choices with the same memory budget, especially on joins and aggregations.
>
> So far: the pipeline, FP16, INT8 and INT4 baselines, an error classifier, and a first layer-sensitivity scan. That scan was on 25 questions, so its ranking is still noise; next I move to Qwen 1.5B, the team's base, with a proper calibration set and a continuous score.
>
> Live, my execution sub-agent runs only read-only SELECT queries, and my error-diagnosis sub-agent turns failures, including empty results, into hints for Agent 3's retry. Thank you.

---

## 10. Q&A preparation

| Question | Answer skeleton |
|---|---|
| Isn't this just `Q4_K_M` / HAWQ? | Those choose precision by generic signals; I measure SQL-task sensitivity and compare against them and against random layers with the same budget. |
| Why did you drop QAT vs PTQ? | QAT on a 1.5B model needs more compute than the project has, and mixed precision answers the practical question (accuracy per unit of memory) more directly. State it as a scope change agreed with the team. |
| INT8 beat FP16? | 79 vs 75 on 100 questions is within noise, not a real gain. |
| Your sensitivity ranking looks random. | On 25 questions, yes: one question is 4 points. That's why the study moves to a calibration split and a continuous score. |
| Why is FP16 so slow? | Most likely CPU offload on a small GPU; it will be re-measured with the hardware recorded. |
| How do you keep live data safe? | Read-only connection, one statement, timeout, SELECT-only guard; destructive requests are refused, not retried. |
| How did you use AI tools? | Match the AI-use record and diary. |

---

## 11. Evidence checklist

- [x] FP16, INT8, INT4 baselines with accuracy, memory and latency (Phi-3, 100 questions)
- [x] Error classes for the FP16 errors (Day 5)
- [x] First per-layer sensitivity scan and an allocation plan (Days 6–7)
- [ ] Qwen2.5-1.5B on the shared eval sets with one scorer
- [ ] GGUF baselines incl. `Q4_K_M`; random and generic-sensitivity controls
- [ ] Mixed-precision model built and evaluated
- [ ] Error-Diagnosis and empty-result sub-agents in the harness
- [ ] Hardware recorded with every result; eval questions and predictions committed
- [ ] Component diagram drawn by hand
- [ ] Script timed at 2 minutes
