# PP1 Panel Response — W.A.T. Wathsala (IT23282704)

Component: **Agent 2 — Knowledge distillation for a small SQL base model (distilled vs native student)** | Project J26-DS-336 | Panel DS-P03
Answers the proposal-presentation comments for Progress Presentation 1. Rewritten 19 Oct 2026 from the `Agent2/` notebooks on `main` (PRs #8, #15; branch `Tharushi`); the earlier draft is in git history. **[MEASURED]** = from the notebooks' printed outputs; **[TO RUN]** = not done yet.

**Status in one line:** the distillation pipeline works end to end on a pilot task (question classification). The SQL-oriented distillation and the two base checkpoints Agent 3 needs are not built yet. Agent 2 is on the team's critical path, so say this plainly and show the plan and dates.

---

## 1. The proposal panel comments and the PP1 answer

Comments: *"Don't have proper component breakdown. Not explained novelty properly (what's the importance of SLM over LM). Need to think about practical usage."*

| Panel comment | PP1 answer (one line) | Evidence to show | Section |
|---|---|---|---|
| No proper component breakdown | Five offline steps: choose models, build prompts, generate teacher outputs, train the student, compare against a native student; output = two base checkpoints for Agent 3. | Component diagram; the pilot run through every step | 4 |
| Novelty not explained (SLM over LM) | The shipped model must be small, but small models lack reasoning; distillation moves a 7B teacher's behaviour into a 0.5–1.5B student without ever deploying the 7B model. The test isolates distillation as the only difference. | Pilot results and the lessons they gave; controlled design with a gold-label control | 2, 3 |
| Practical usage | The bank runs only the small student on its own hardware; the teacher is used once, offline, on public training data, never on the bank's data. | Teacher vs student sizes; data sources | 6 |

---

## 2. Novelty

**Distillation as the base-model choice for SQL on small models:** does a student distilled from a ~7B teacher make a better *starting point* for SQL fine-tuning than a native model of the same size, when both are then fine-tuned identically by Agent 3?

| Prior work | What it does | Difference |
|---|---|---|
| Knowledge distillation (Hinton et al. 2015; DistilBERT and successors) | Compress a large model into a small one, evaluated on general tasks | The question here is the effect on **later SQL fine-tuning**, per complexity bucket |
| Distilled small models (e.g. distilled Qwen / DeepSeek variants) | Released models, compared on general benchmarks | Distilled vs native **of the same size and tokenizer**, then identical fine-tuning, so distillation is the only variable |

**The control that makes it a finding (C0):** the native model fine-tuned on the same prompts with **gold** answers instead of teacher answers. Without it, a distillation gain could just be extra in-domain training. The pilot already showed this risk (Section 5: a fine-tuned teacher's soft targets were almost one-hot, so "distillation" became plain label training).

**Say:** "Distillation is not new. The question is whether it gives a better base for SQL fine-tuning than a native model of the same size, with distillation as the only difference. A no-difference result is also a finding."

---

## 3. Why a small model, and why distillation

- **The deployed model must be small.** Banks keep generative AI on-premise under their AI-governance policy, on mid-range hardware, so the shipped model is 0.5–1.5B parameters. A 7B teacher does not fit that budget for serving.
- **Small models have less reasoning capacity.** Fine-tuning teaches a model the task format; it cannot easily add reasoning the model lacks. Distillation transfers some of a larger model's behaviour first.
- **The large model is used once, offline.** The teacher runs only during training, on rented compute and public training data (Spider **train**). It is never deployed and never sees the bank's data.

**One line for the panel:** "We can't ship the 7B model, so we use it once to teach the small one, and then measure whether the lesson survives SQL fine-tuning."

---

## 4. Component breakdown (all offline; built once)

| # | Step | Decision | Input → Output |
|---|---|---|---|
| 1 | Select and freeze | Which teacher, student and native baseline? | candidates → pinned model versions (teacher Qwen2.5-7B-Instruct; student and native Qwen2.5, same size and tokenizer) |
| 2 | Prompt pool | What does the teacher answer? | Spider **train** schemas + general reasoning prompts → 1,500–3,000 prompts, no overlap with `eval/*.json` |
| 3 | Teacher generation | What does the teacher say? | prompts → teacher outputs (soft targets or responses), logged and versioned; only outputs whose SQL executes are kept |
| 4 | Student training | Train the student on the teacher | outputs → distilled student checkpoint (and native + C0 control) |
| 5 | Comparison and hand-off | Which base is better? | distilled vs native (paired tests) → **both** checkpoints + shared fine-tuning config → Agent 3 |

**Diagram:** five boxes left to right, ending in an arrow "two checkpoints → Agent 3", in draw.io, black and white.

---

## 5. Pilot results: the method validated on a classification task [MEASURED]

Task 1 ("DATABASE vs GENERAL question") was used to build and debug the distillation pipeline before the SQL task.

- **Data:** database questions from `sql_create_context` (WikiSQL + Spider); general questions from 20 CLINC intents. 4,000 train, 799 validation, 1,200 test, with exact-duplicate leakage checked (0 overlaps).
- **Models:** teacher Qwen2.5-7B-Instruct (4-bit); students Qwen2.5-0.5B-Instruct with LoRA (r 8), 3 epochs. Distillation loss: KL divergence on temperature-2 soft targets. Colab T4.

| Model | Test accuracy (n = 1,200) |
|---|---|
| TF-IDF + logistic regression (baseline) | .983 |
| Native 0.5B student | .997 (4 errors, raw-text input) |
| Fine-tuned 7B teacher | .998 |
| 0.5B student distilled from the fine-tuned teacher | .999 (1 error) |
| 0.5B student distilled from the prompted teacher | .92 on validation (training prompt); .59 on test, evaluated on raw text |

**What the pilot taught (the useful part):**
1. **The pipeline works end to end:** soft targets from a 7B teacher, KL training of a 0.5B student, held-out test, leakage check.
2. **Ceiling effect.** A simple baseline already scores .983, so this task cannot show a distillation effect. That's why the real study uses SQL, where small models fail on joins and aggregations.
3. **The input format must match.** The .59 is not a teacher failure. The student was trained on a chat prompt and tested on raw text. The teacher's labels agreed with the truth on 90% of training rows. Re-evaluate with the training prompt.
4. **A fine-tuned teacher gives nearly one-hot targets,** which makes "distillation" close to plain label training. That's the reason for the C0 control.

---

## 6. Practical usage

- **Only the small student ships.** It runs on the bank's mid-range GPU as the shared base for Agent 3's adapters and is quantized by Agent 4.
- **No customer data in training.** Teacher prompts come from public datasets (Spider **train**), never from the evaluation sets or the bank's databases.
- **Cheapest improvement available.** If distillation gives a better base at the same size, every query gets better at no extra hardware cost. If it doesn't, the native model ships and the team has saved a dead end.
- **Agent 1's schema format is reused:** teacher prompts use the same pruned schema text, value comments included (`Sex VARCHAR(1) /* values: 'F', 'M' */`), so the student learns the format it will see live.

---

## 7. Plan to the SQL study (critical path)

| # | Step | Done when |
|---|---|---|
| 1 | Re-evaluate the prompted-teacher student with its training prompt; add a paired test (McNemar) between students | Pilot write-up correct |
| 2 | Agree base size with the team (0.5B kept for PP1; 1.5B to match Agent 3's placeholder) and freeze the shared fine-tuning config | Config signed by Thathsarani |
| 3 | SQL prompt pool from Spider **train** schemas + general reasoning prompts; teacher answers, keeping only SQL that executes | Versioned dataset |
| 4 | Train the distilled student; prepare the native and C0 control | Three checkpoints |
| 5 | Pre-fine-tuning comparison (general reasoning + SQL), paired tests | Early result |
| 6 | Hand both checkpoints to Agent 3; after her identical fine-tuning, per-bucket execution accuracy | Final finding |

**Fallback if time runs short:** Agent 3 keeps the released Qwen2.5 model as the native base, and Agent 2 delivers the distilled checkpoint as soon as it exists. Say this to the panel: it shows the critical-path risk is managed.

---

## 8. Limitations to state

- No SQL distillation yet. The pilot task is classification and sits at the ceiling.
- Pilot labels come from the source dataset, not from human annotation, and contain noise ("what is the spanish word for garden" is labelled DATABASE because it comes from WikiSQL).
- Pilot comparisons have no paired test yet, and the students were not all evaluated on the same input format.
- Checkpoints live on Google Drive only. Commit configs, and record checkpoint locations and hashes.

---

## 9. 2-minute script (about 230 words)

> Good morning. I'm W.A.T. Wathsala, and my component is Agent 2: the small base model every other agent builds on.
>
> The bank has to run the model on its own mid-range hardware, so the shipped model must be small, around one billion parameters. Small models lack reasoning, and fine-tuning alone can't add much. Knowledge distillation lets a seven-billion-parameter teacher teach the small student once, offline, on public data, and the teacher is never deployed.
>
> My question is whether a distilled student is a better starting point for SQL fine-tuning than a native model of the same size. Distillation is the only difference, and I add a control trained on gold answers, so a gain can't just be extra training.
>
> So far I've built and tested the whole distillation pipeline on a pilot task, classifying questions as database or general. A 0.5B student distilled from the 7B teacher reached 99.9 percent. The pilot also taught me three things: this task is too easy to show an effect, the evaluation prompt must match training, and a fine-tuned teacher turns distillation into plain label training. That's why the real study uses SQL with that control.
>
> Next I build the SQL prompt set from Spider training schemas and hand both checkpoints to Agent 3. Thank you.

---

## 10. Q&A preparation

| Question | Answer skeleton |
|---|---|
| Why is your result a classifier, not SQL? | It was a pilot to build and debug the pipeline; the SQL study is next (Section 7). |
| 99.9% vs 99.7%: is distillation better? | No claim: both are at the ceiling (a TF-IDF baseline gets 98.3%) and no paired test has been run. |
| Why did one student get 59%? | Evaluated on raw text after being trained on a chat prompt; a format mismatch, being re-evaluated. |
| Isn't distillation just more training? | Exactly the risk; the C0 control (gold answers, same prompts) separates the two. |
| Agent 3 is waiting on you. | Fallback: Agent 3 trains on the released Qwen base now and re-runs on the distilled checkpoint. |
| Does the teacher see bank data? | No: public training data only, offline, never deployed. |
| How did you use AI tools? | Match the AI-use record and diary. |

---

## 11. Evidence checklist

- [x] Distillation pipeline end to end on the pilot (teacher soft targets, KL training, held-out test, leakage check)
- [ ] Prompted-teacher student re-evaluated with its training prompt; paired tests between students
- [ ] Base size and shared fine-tuning config agreed with Agent 3
- [ ] SQL prompt pool from Spider train, teacher outputs filtered by execution
- [ ] Distilled, native and C0 checkpoints; pre-fine-tuning comparison
- [ ] Checkpoints handed to Agent 3 (location and hash recorded)
- [ ] Component diagram drawn by hand
- [ ] Script timed at 2 minutes
