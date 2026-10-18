# PP1 Panel Response — W.A.T. Wathsala (IT23282704)

Component: **Agent 2 — Knowledge-Distilled Foundation Model** | Project J26-DS-336 | Panel DS-P03
Read this with the team document (00). Items marked **[EVIDENCE NEEDED]** must be produced and measured by you.

Your component is built once, offline, and is not called per query. That makes it the hardest one to show as "working", and the lecture says PP1 is about working, testable, defensible progress. Your best protection is to show real artefacts early: a generated dataset, a training run, a comparison table, and the handed-over model.

---

## 1. Panel comments: answers and fixes

| Panel comment | What to say | Fix before PP1 | Evidence to show |
|---|---|---|---|
| **Don't have proper component breakdown** | Agent 2 has four steps. A teacher model of about 7B parameters generates prompt-response pairs. A small student is trained on them. A native model of the same size is kept as the baseline. The two are compared, and the winner is published as a versioned artefact for Agent 3. It is built once, so it has no live sub-agents. | Draw the four steps with the artefact handoff arrow to Agent 3. | Component diagram; model card |
| **Not explained novelty properly (SLM over LM)** | This is your strongest answer to the panel's question. A small model has limited capacity, and fine-tuning can't create reasoning ability that isn't there. Distillation transfers a larger model's behaviour into the small one. Existing studies compare distilled and native small models on general tasks, not under identical SQL fine-tuning. I isolate distillation as the single variable. | Run the comparison: a reasoning score before fine-tuning, then exact-match and JOIN/aggregation accuracy after identical fine-tuning of both models. Include a "same prompts, gold-SQL targets" control (C0), so a distillation gain can't simply be extra in-domain training (see `reports/Base model selection for local Text2SQL.md`). | Comparison table (**[EVIDENCE NEEDED]**) |
| **Need to think about practical usage** | Customers cannot buy bigger hardware, so a stronger base model of the same size is the cheapest improvement available. If distillation wins, the distilled model becomes the default shipped with the product. | Be explicit that the teacher runs on rented compute because it is too large for mid-range hardware, and that the shipped model does not. | Budget line and compute log |

---

## 2. The nine feedback points, for Agent 2

| Feedback | What you do |
|---|---|
| Testing, feedbacks | Tests for dataset generation (format, size, no duplicates), a training run that completes, and the evaluation harness; a check that the published artefact loads in Agent 3's code. Get supervisor feedback on the dataset design. |
| Flow diagram | teacher → dataset → student → comparison with native → artefact registry → Agent 3. |
| Frontend (chatbot) | No live step, so show a model-info panel (base model, version, distilled vs native, model card), not a fake live trace. |
| Everyone explains | Memorise the 30-second whole-system explanation. |
| Separate components and flows | Show your artefact contract with Agent 3 and say clearly why you are not a live step. |
| Wrong inputs | Section 4. |
| Not only sample data | Keep evaluation prompts separate from distillation prompts. Teacher prompts must never come from the Spider dev databases used in evaluation. |
| NFRs | Reproducibility (versioned config and prompts), compute budget, artefact integrity (checksum), and the student's size on disk and in VRAM. |
| Backup / demo | Dataset, student checkpoint and registry entry in two other places; a recorded evaluation run. This matters most for you, because rented compute may not be available on demo day. |

---

## 3. Two key functions

1. **Distillation dataset generation:** run the teacher over general-reasoning and SQL-adjacent prompts and store the prompt-response pairs (about 1,500–3,000 pairs, as scoped in the proposal). *Demo:* the dataset file, its size and a few sample pairs.
2. **Distilled-versus-native evaluation and artefact publishing:** compare the two models and publish the chosen one with a model card for Agent 3. *Demo:* the comparison table, then Agent 3 loading the published model.

---

## 4. Wrong inputs to demonstrate (pick at least two)

| Input | Expected from Agent 2 |
|---|---|
| Teacher output that is empty or malformed | Filtered out and counted, not added to the dataset |
| Duplicate prompts | Detected and removed |
| Training interrupted | Resumable from checkpoint, or fails with a clear message |
| Artefact requested that doesn't exist | Registry returns a readable error to Agent 3 |
| Model whose size doesn't match the student configuration | Rejected at registration |

---

## 5. 2-minute script (draft, about 200 words)

Replace every bracket with a measured value before using it.

> Good [morning]. I'm W.A.T. Wathsala, and my component is Agent 2: a knowledge-distilled foundation model.
>
> The problem: models that fit on mid-range hardware are small and generic, and fine-tuning can't add reasoning ability that the base model doesn't already have. Our target is mid-range hardware, so we cannot just use a bigger model.
>
> My approach is knowledge distillation. A larger teacher model of about 7 billion parameters generates prompt-response pairs, and a small student model is trained on them. I compare that student against a native small model of the same size, and then both are fine-tuned identically, so distillation is the only difference.
>
> My two key functions are dataset generation and the distilled-versus-native comparison. I generated [N] pairs. Before any SQL fine-tuning, the distilled model scored [X] on reasoning against [Y] for the native model.
>
> My component is built once, offline, so it is not a live step. I publish the chosen model as a versioned artefact with a model card, and Agent 3 loads it. Malformed teacher outputs and duplicates are filtered out automatically.
>
> If distillation wins, the distilled model becomes the default shipped with the product. Thank you.

---

## 6. Q&A preparation

| Question | Answer skeleton |
|---|---|
| What exactly did I build? | Teacher generation, student training, native baseline, evaluation harness, artefact registry. State what has actually run. |
| Which sub-problem does it address? | Weak reasoning in small base models. |
| How does it connect to the rest? | Agent 3 loads the published base model; Agent 4 is affected only indirectly. Contract: versioned artefact plus model card. |
| What testing supports it? | Pre- and post-fine-tuning comparison, dataset tests, supervisor feedback. |
| What proves I understand it? | Explain response-based distillation vs training on labels, and why the teacher shares the student's tokenizer; show the dataset and Git history. |
| Isn't any gain just more training data? | That is why the C0 control exists: same prompts, gold-SQL targets. |
| Why only a few thousand pairs? | Proof-of-concept scale, stated in the proposal; the comparison is controlled, not a production corpus. |
| What if distillation shows no advantage? | A negative result is valid; the native model ships and the finding is reported. |
| Are you on the critical path? | Yes: Agent 3 needs your artefact for real validation. A placeholder is in use now; state the re-validation plan. |
| How did you use AI tools? | Match your AI-use record and diary. |

---

## 7. Evidence checklist

- [ ] Distillation dataset generated, with size and sample pairs **[EVIDENCE NEEDED]**
- [ ] At least one student training run completed **[EVIDENCE NEEDED]**
- [ ] Native baseline in place
- [ ] Pre-fine-tuning comparison table **[EVIDENCE NEEDED]**
- [ ] Artefact published with model card, loaded successfully by Agent 3
- [ ] At least two wrong-input cases passing
- [ ] Model-info panel in the chatbot or explorer
- [ ] Tests passing, with a screenshot
- [ ] Supervisor feedback on the dataset design recorded, converted to Planner tasks
- [ ] Git, Planner, diary, AI-use record up to date
- [ ] Backups of dataset, checkpoint and registry in two other places; fallback video recorded
- [ ] Script timed at exactly 2 minutes
