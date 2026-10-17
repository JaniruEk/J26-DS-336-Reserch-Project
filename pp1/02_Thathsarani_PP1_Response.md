# PP1 Panel Response — K.G.Y.V. Thathsarani (IT23404250)

Component: **Agent 3 — Complexity-Specialised Fine-Tuning Architecture Selection and Live Generation** | Project J26-DS-336 | Panel DS-P03
Read this with the team document (00). Items marked **[EVIDENCE NEEDED]** must be produced and measured by you.

---

## 1. Panel comments: answers and fixes

| Panel comment | What to say | Fix before PP1 | Evidence to show |
|---|---|---|---|
| **Don't have proper component breakdown** | Agent 3 has an offline part and a live part. Offline, I train standard LoRA and HydraLoRA under identical conditions and publish both the winner *and* the runner-up as versioned artefacts. Live, per query, a Head-Selection sub-agent routes by the question's complexity label, then a Generation sub-agent writes the SQL. | Show two boxes for the live sub-agents and one for the offline comparison; show the inputs (PrunedSchema + label + base model) and outputs (candidate SQL; winner/runner-up artefacts). | Component diagram; live trace section |
| **Not explained novelty properly (SLM over LM)** | Text-to-SQL is not one task: a single-table lookup and a multi-join aggregation need different reasoning. Standard LoRA forces one shared adapter to cover both, and a small model, with little spare capacity, suffers most. HydraLoRA shares one down-projection and gives each complexity bucket its own up-projection head. I route by a hard-coded complexity label instead of HydraLoRA's unsupervised clustering. HydraLoRA has been tested across different tasks, not across difficulty levels within one domain. | Run the controlled comparison: same base model, dataset, epochs and hardware budget. Report exact-match, JOIN/aggregation accuracy and trainable parameter count per complexity bucket. | Comparison table (**[EVIDENCE NEEDED]**) |
| **Need to think about practical usage** | Analysts' hard questions are the multi-join and aggregation ones, which is exactly where small models fail. Improving that bucket is what makes the tool usable rather than a toy. | Use a multi-join business question in the demo and show the head that was selected. | Scenario run in the chatbot |

---

## 2. The nine feedback points, for Agent 3

| Feedback | What you do |
|---|---|
| Testing, feedbacks | Unit tests for the router (every complexity label, including boundary cases) and for generation; a component test that the LoRA-vs-HydraLoRA harness produces a winner and runner-up; an integration test that Agent 1's output is accepted. |
| Flow diagram | label arrives → head selected → SQL generated; plus the offline training flow ending in the artefact registry. |
| Frontend (chatbot) | Agent 3's trace section: complexity label, head chosen, candidate SQL. |
| Everyone explains | Memorise the 30-second whole-system explanation. |
| Separate components and flows | Your two sub-agents and the handoff artefacts to Agent 4. |
| Wrong inputs | Section 4. |
| Not only sample data | Evaluate on held-out questions and a database not used in training; report per complexity bucket. |
| NFRs | Generation latency per query; adapter size and trainable parameters; behaviour when a head or artefact is missing. |
| Backup / demo | Adapter files and registry entries in two other places; a recorded run of head selection plus generation. |

**Integration note:** Agent 3 plugs into the existing harness through `create_app(generate=...)` in `harness/app.py`. Agent 1's output contract (`query, complexity, mode, anchor, tables, ddl, tokens, latency_ms`) is waiting for your sign-off.

---

## 3. Two key functions

1. **Complexity-based head routing:** given the complexity label, choose the correct HydraLoRA head, or the single adapter if standard LoRA won. *Demo:* a simple question and a multi-join question going to different heads, shown in the trace.
2. **LoRA vs HydraLoRA comparison with winner and runner-up:** the evaluation that selects and packages both architectures. *Demo:* the comparison table, then the two published artefacts.

---

## 4. Wrong inputs to demonstrate (pick at least two)

| Input | Expected from Agent 3 |
|---|---|
| Missing or unknown complexity label | Falls back to a defined default route; logged |
| Label at a bucket boundary | Handled without failure |
| Empty or malformed PrunedSchema | Rejected with a clear contract error, not a model crash |
| Hint from Agent 4 after a failed execution | Accepted and used for the retry |
| Missing adapter or base-model artefact | Readable startup error |
| Very long schema context | Truncated or rejected within the token budget |

---

## 5. 2-minute script (draft, about 200 words)

Replace every bracket with a measured value before using it.

> Good [morning]. I'm K.G.Y.V. Thathsarani, and my component is Agent 3: complexity-specialised fine-tuning for SQL generation.
>
> The problem: Text-to-SQL is not one task. A simple lookup and a multi-table join with aggregation need different reasoning, but standard LoRA fine-tuning gives one shared adapter for both. A small model has little spare capacity, so it fails most on the hard queries.
>
> My solution is HydraLoRA: one shared down-projection and separate up-projection heads per complexity bucket, selected by the complexity label from Agent 1. I train standard LoRA and HydraLoRA under identical conditions, and I publish both the winner and the runner-up, because Agent 4 uses the runner-up to test whether its quantization findings hold.
>
> I'll show two key functions: head routing, and the winner-versus-runner-up comparison. In the demo, a simple question and a multi-join question go to different heads. On the comparison, HydraLoRA scored [X] on join and aggregation accuracy against [Y] for standard LoRA, with [Z] percent more trainable parameters.
>
> Wrong inputs, like a missing label or a malformed schema, produce clear errors instead of crashes. Agent 3 receives its input from Agent 1 and hands its SQL to Agent 4. Thank you.

---

## 6. Q&A preparation

| Question | Answer skeleton |
|---|---|
| What exactly did I build? | LoRA baseline, custom HydraLoRA module, router, evaluation harness, artefact registry, the two live sub-agents. State what is working today. |
| Which sub-problem does it address? | Weak multi-join and aggregation accuracy in small models. |
| How does it connect to the rest? | Takes PrunedSchema and label from Agent 1 and the base model from Agent 2; hands artefacts and SQL to Agent 4 through agreed entry points only. |
| What testing supports it? | The comparison table, router tests, held-out results. |
| What proves I understand it? | Explain the shared A / multiple B matrices and why only B is duplicated; walk through the router; show Git history. |
| Why hard-coded routing instead of clustering? | The project already has a complexity classifier, and routing by it keeps the head choice auditable and avoids gating collapse. |
| What if the winner is standard LoRA? | A negative result is a valid finding; the pipeline falls back to the single adapter. |
| How did you use AI tools? | Match your AI-use record and diary. |

---

## 7. Evidence checklist

- [ ] Router working, with a recording of two questions taking different heads
- [ ] LoRA vs HydraLoRA comparison on a placeholder base, per complexity bucket **[EVIDENCE NEEDED]**
- [ ] Winner and runner-up published as versioned artefacts
- [ ] Held-out evaluation on an unseen database **[EVIDENCE NEEDED]**
- [ ] At least two wrong-input cases passing
- [ ] Generation latency and adapter-size measurements **[EVIDENCE NEEDED]**
- [ ] Agent 1 handoff contract signed off
- [ ] Trace section integrated in the chatbot
- [ ] Unit and integration tests passing, with a screenshot
- [ ] One user feedback session recorded, converted to Planner tasks
- [ ] Git, Planner, diary, AI-use record up to date
- [ ] Backups in two other places; fallback video recorded
- [ ] Script timed at exactly 2 minutes
