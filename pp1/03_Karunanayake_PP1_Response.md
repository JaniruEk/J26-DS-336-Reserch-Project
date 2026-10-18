# PP1 Panel Response — K.M.I.N. Karunanayake (IT23179912)

Component: **Agent 4 — Quantization Strategy Selection, Cross-Check and Live Execution** | Project J26-DS-336 | Panel DS-P03
Read this with the team document (00). Items marked **[EVIDENCE NEEDED]** must be produced and measured by you.

---

## 1. Panel comments: answers and fixes

| Panel comment | What to say | Fix before PP1 | Evidence to show |
|---|---|---|---|
| **Don't have proper component breakdown** | Agent 4 has an offline part and a live part. Offline, I compare QAT and PTQ on Agent 3's winning model, then run the cross-check on its runner-up. Live, per query, the Execution sub-agent runs the SQL. When execution fails, the Error-Diagnosis sub-agent turns the error into a hint and sends it back to Agent 3, for a bounded number of retries. | Show the offline pipeline and the two live sub-agents as separate boxes, with the retry arrow back to Agent 3 clearly drawn. | Component diagram; live trace section |
| **Not explained novelty properly (SLM over LM)** | Even a small fine-tuned model can exceed memory at full precision, so it must be compressed to run on mid-range hardware. Compression can quietly break aggregation, because SUM, AVG and COUNT queries need precise reasoning. Tools usually apply whichever quantization is convenient. I compare QAT against PTQ at INT8 and INT4 and score syntax and logical correctness separately. I then check whether the ranking still holds on a different fine-tuning architecture; the literature treats those two choices as independent. | Run the comparison and report syntax accuracy, JOIN/aggregation accuracy, VRAM and latency per configuration. | Results table and degradation curve (**[EVIDENCE NEEDED]**) |
| **Need to think about practical usage** | A compressed model is what actually fits on the customer's own hardware. The execution sub-agent protects live data: it runs only safe queries, and when a query fails the user gets a corrected attempt instead of an error. | Show the self-healing retry live, and show that a destructive request is refused. | Live retry demo; safety test results |

---

## 2. The nine feedback points, for Agent 4

| Feedback | What you do |
|---|---|
| Testing, feedbacks | Unit tests for the metric suite, the SELECT-only guard and the retry loop; a component test that PTQ and QAT run end to end on a placeholder model; an integration test that your hint is accepted by Agent 3. |
| Flow diagram | SQL arrives → safety check → execute → success, or diagnose → hint → Agent 3 → retry (bounded); plus the offline quantization flow. |
| Frontend (chatbot) | Agent 4's trace section: execution status, retry count, error hint, time taken. |
| Everyone explains | Memorise the 30-second whole-system explanation. |
| Separate components and flows | Your two live sub-agents and the retry boundary with Agent 3. |
| Wrong inputs | Section 4. Your component carries most of the security and robustness evidence. |
| Not only sample data | Run the quantized model on held-out questions and more than one database; report syntax and logic accuracy separately from the development set. |
| NFRs | VRAM and latency per configuration, retry-loop termination, safe execution. |
| Backup / demo | Quantized model files and placeholder-run results in two other places; a recorded retry demo. |

**Integration note:** the harness (`harness/app.py`) already has a stand-in executor. It opens the DB read-only and retries up to `MAX_ATTEMPTS=3`, but its retry hint is just the raw DB error. Your Error-Diagnosis sub-agent replaces that hint. Plug in through `create_app(execute=...)`.

---

## 3. Two key functions

1. **PTQ and QAT quantization with the error-rate metric suite:** quantize at INT8 and INT4 (GGUF and AWQ for PTQ). Score syntax validity separately from logical correctness, and record VRAM and latency. *Demo:* the comparison table and the point where accuracy drops sharply.
2. **Execution with error diagnosis and bounded retry:** run SQL against the database; on failure, inspect the error and send a hint back to Agent 3, stopping at the retry limit. *Demo:* a bad query that fails once, gets a hint and succeeds on retry; then a hopeless one that stops cleanly.

The cross-check on the runner-up architecture is your third piece. Mention it, but claim it as done only if you have results.

---

## 4. Wrong inputs to demonstrate (pick at least two)

| Input | Expected from Agent 4 |
|---|---|
| SQL referencing a missing table or column | Error captured, hint produced, bounded retry, then a clear failure message |
| Destructive SQL (DELETE, DROP, UPDATE) | Blocked by a SELECT-only check and a read-only database connection |
| Several statements in one string | Rejected |
| Syntax error | Hint built from the error text and sent back |
| Retry limit reached | Stops and reports; never loops forever |
| Model fails to load or convert | Graceful error, not a crash |

Implement any safety measure that does not exist yet before presenting it. The panel asked for security to be *shown*.

---

## 5. 2-minute script (draft, about 200 words)

Replace every bracket with a measured value before using it.

> Good [morning]. I'm K.M.I.N. Karunanayake, and my component is Agent 4: quantization strategy and live execution.
>
> The problem: even a small fine-tuned model can be too large for mid-range hardware, so it must be compressed. But careless compression can introduce errors, especially in aggregation queries, and tools usually pick whichever method is convenient.
>
> I compare Quantization-Aware Training with Post-Training Quantization at INT8 and INT4, and I score syntax validity and logical correctness separately, with VRAM and latency. I also run a cross-check: does my winning method still win on the runner-up architecture from Agent 3?
>
> Agent 4 also runs live. The Execution sub-agent runs the SQL; if it fails, the Error-Diagnosis sub-agent sends a hint back to Agent 3, up to [N] retries.
>
> My two key functions are the quantization comparison and the retry loop. On the comparison, INT4 [method] kept [X] percent logical accuracy against [Y] for the full-precision model, using [Z] GB of VRAM. In the demo, a query fails, gets a hint, and succeeds on retry. A destructive query is refused.
>
> Agent 4 receives SQL from Agent 3 and returns results to the user. Thank you.

---

## 6. Q&A preparation

| Question | Answer skeleton |
|---|---|
| What exactly did I build? | PTQ and QAT pipelines, the error-rate metric suite, the execution and error-diagnosis sub-agents, the cross-check harness. State what is working today. |
| Which sub-problem does it address? | Fitting on mid-range hardware without losing aggregation correctness; safe live execution. |
| How does it connect to the rest? | Receives SQL and artefacts from Agent 3; its hint goes back to Agent 3 through the orchestrator, which logs every retry. |
| What testing supports it? | Results table, retry-loop tests, safety tests, user session. |
| What proves I understand it? | Explain how PTQ differs from QAT, why syntax and logic are scored separately, and why the cross-check matters; show Git history. |
| Why QAT vs PTQ rather than a bit-rate sweep? | A sweep tells you what fits; the comparison tells you which method preserves reasoning, and where it breaks. |
| Isn't "QAT in AWQ format" a contradiction? | Yes, AWQ is itself a PTQ method. The QAT arm uses a fake-quantizer whose group size matches the target and exports through the normal converters. |
| What if the ranking reverses on the runner-up? | That is a reportable interaction finding, not a failure. |
| How did you use AI tools? | Match your AI-use record and diary. |

---

## 7. Evidence checklist

- [ ] PTQ and QAT run on at least a placeholder model, with a results table **[EVIDENCE NEEDED]**
- [ ] Syntax vs logic accuracy, VRAM and latency per configuration **[EVIDENCE NEEDED]**
- [ ] Retry loop demonstrated and shown to terminate
- [ ] Read-only connection and SELECT-only guard tested
- [ ] At least two wrong-input cases passing
- [ ] Cross-check run, or clearly labelled as planned
- [ ] Trace section integrated in the chatbot
- [ ] Unit and integration tests passing, with a screenshot
- [ ] One user feedback session recorded, converted to Planner tasks
- [ ] Git, Planner, diary, AI-use record up to date
- [ ] Backups in two other places; fallback video recorded
- [ ] Script timed at exactly 2 minutes
