# PP1 Panel Response — K.G.Y.V. Thathsarani (IT23404250)

Component: **Agent 3 — Complexity-routed HydraLoRA for SQL generation (vs standard LoRA)** | Project J26-DS-336 | Panel DS-P03
Answers the proposal-presentation comments for Progress Presentation 1. Rewritten 19 Oct 2026 from the results on branches `thathsarani-lora-baseline` / `thathsarani-hydra` (`agent3_finetune/`); the earlier draft is in git history. **[MEASURED]** = from those result files; **[TO RUN]** = not done yet.

---

## 1. The proposal panel comments and the PP1 answer

Comments: *"Don't have proper component breakdown. Not explained novelty properly (what's the importance of SLM over LM). Need to think about practical usage."*

| Panel comment | PP1 answer (one line) | Evidence to show | Section |
|---|---|---|---|
| No proper component breakdown | One offline comparison (LoRA vs HydraLoRA, same base, data and budget) and two live sub-agents (head selection, SQL generation), each with a defined input and output. | Component diagram; the routing self-test; per-bucket results table | 4 |
| Novelty not explained (SLM over LM) | One small model must handle easy lookups and multi-table joins; a single adapter shares its little capacity across both. HydraLoRA gives each complexity type its own head, routed by an auditable label. | LoRA helps single-join (+.39) but not multi-join; HydraLoRA vs LoRA per bucket; routing sensitivity | 2, 3 |
| Practical usage | One shared base model plus small adapter heads swapped per question on one mid-range GPU, instead of several separate models. | Trainable parameters, one base for all heads | 6 |

---

## 2. Novelty

**Complexity-routed HydraLoRA for text-to-SQL:** one shared LoRA down-projection (A), one up-projection head (B) per query complexity (simple / single-join / multi-join / aggregation), chosen by a **hard-coded** complexity label rather than a learned router.

| Prior work | What it does | Difference |
|---|---|---|
| HydraLoRA (arXiv 2404.19245, NeurIPS 2024) | Shared A, several B heads, routing learned without supervision; evaluated on general multi-task benchmarks | Applied to text-to-SQL, heads keyed to query complexity, routing by a supervised, auditable label |
| Standard LoRA (PEFT) | One adapter for every query type | The control condition, same base, data, epochs and budget |
| MATS (arXiv 2512.18622) | Several separate small models (about 9B in total) | One shared base with adapter heads instead of several models |

**Say:** "HydraLoRA itself is not new. What is new is keying its heads to SQL query complexity with an auditable router, and measuring when that helps a small model and how much it depends on routing accuracy."

**Why hard-coded routing:** the team already has a complexity classifier (Agent 1); a fixed rule makes every head choice explainable and avoids the gating collapse a learned router can suffer. The cost is that routing errors pass straight through, which is measured (Section 7).

---

## 3. Why a small model, and why it needs complexity heads

- A small model has little spare capacity. With one adapter, the training signal goes where the data is: Spider train has 2,661 aggregation and 1,644 simple examples but only 375 multi-join.
- The measured result fits that: standard LoRA raised single-join accuracy from .29 to .68 (+.39, p = .002) but did nothing for multi-join (.25 → .19, p = .73, not significant). **[MEASURED]**
- A large model can usually handle all query types with prompting or one adapter. A small model on mid-range hardware cannot afford a second model per query type, but it can afford one extra up-projection matrix per type: HydraLoRA adds heads, not models.

**One line for the panel:** "A large model can be told how to write a join. A small model has to learn it, and one shared adapter doesn't leave enough room for the hard cases."

---

## 4. Component breakdown

| # | Part | Decision | Input → Output |
|---|---|---|---|
| Offline | LoRA vs HydraLoRA comparison | Which architecture wins? | Spider train (5,456 examples labelled by `classify_sql`, split by database) + base model → winner **and** runner-up adapters, eval logs |
| Live 1 | Head selection | Which head answers this question? | complexity label from Agent 1 → head id (or the single LoRA adapter) |
| Live 2 | SQL generation | What SQL answers it? | question + Agent 1's pruned schema (`ddl`) + head + retry hint from Agent 4 → candidate SQL |

Hand-offs: Agent 1 → label + pruned schema; Agent 2 → base model (placeholder: Qwen2.5-1.5B-Instruct until Agent 2 delivers); Agent 3 → Agent 4: winner and runner-up adapters (offline), candidate SQL (live). The harness calls `generate(question, ddl, hint=None, dialect=...)`.

**Diagram:** draw the offline comparison and the two live boxes with the data on each arrow, in draw.io, black and white.

---

## 5. Results [MEASURED]

Qwen2.5-1.5B-Instruct (placeholder base), seed 42, rank 16, 3 epochs, Colab T4. Execution accuracy on 128 scored questions (Spider dev 120 + Chinook 14), paired tests.

| Bucket (n) | Untrained base | Standard LoRA | HydraLoRA, correct labels | HydraLoRA, live classifier |
|---|---|---|---|---|
| simple (31) | .55 | .74 | .71 | .55 |
| single-join (31) | .29 | **.68** | .65 | .35 |
| multi-join (32) | .25 | .19 | .16 | .12 |
| aggregation (34) | .56 | .59 | .56 | .53 |
| **All (128)** | .41 | **.55** | .52 | .39 |

| Comparison | Result | Test |
|---|---|---|
| LoRA vs untrained base | +.13 [+.05, +.23] | 29 vs 12, McNemar p = .012 |
| HydraLoRA (correct labels) vs LoRA | −.03 [−.09, +.03] | 6 vs 10, p = .454, not significant |
| Same, normalised exact match | +.05 [+.01, +.10] (single-join .41 vs .26) | 9 vs 2, p = .065 |
| HydraLoRA: correct labels vs live classifier | +.12 [+.06, +.20] | 18 vs 2, p < .001 |
| Trainable parameters | LoRA 18.5M (1.2% of the model); HydraLoRA 49.4M | — |

**Honest reading:** LoRA clearly helps. HydraLoRA does not beat LoRA yet on execution accuracy, writes closer-to-gold SQL (exact match), and loses 13 points when the classifier routes wrongly. Neither adapter fixes multi-join.

---

## 6. Practical usage

- **One base, many heads.** All four heads share the base model and the A matrix; switching head per question costs no extra model in memory. That is what fits a single mid-range GPU in the bank's own data centre.
- **The hard questions are the business questions.** Analysts ask "revenue per region per product line", which is multi-join plus aggregation: exactly the buckets where small models fail and where the heads are aimed.
- **Auditable routing.** The trace shows which head answered and why (the complexity label), which a governance team can review.
- **Deployment (team decision pending):** heads kept as separate adapters on a quantized base, so Agent 4 quantizes the configuration that is actually deployed.

---

## 7. What the results already explain, and the next experiments

**Why multi-join fails (draft error analysis of the multi-join failures, automatic labels, to be checked by hand):**

| Failure type | LoRA (26 wrong) | HydraLoRA (27 wrong) |
|---|---|---|
| Column not found | 20 | 17 |
| → the column exists, but in another table (wrong table or alias) | 16 | 14 |
| → the column exists nowhere | 4 | 3 |
| Missing table | 11 | 9 |
| Join key differs from gold | 5 | 6 |
| Wrong aggregate | 0 | 0 |

The model mostly references a real column through the wrong table, a join-structure error that neither adapter fixes with 375 multi-join examples. A failure can carry more than one label.

**Routing is the lever:** the live classifier routed 59% correctly (87 of 148). Agent 1's new schema-aware classifier routes 68% correctly (p = .029); an offline estimate puts HydraLoRA at **.45–.54** with it, against .39 now and .52 with correct labels. **[TO RUN]** to pin it down: four fixed-head runs.

**Next experiments, in order:**

| # | Experiment | Why | Cost |
|---|---|---|---|
| 1 | Error analysis by hand, 20–30 multi-join failures | Explains why neither adapter helps | Laptop only |
| 2 | Routing-error curve (100 / 90 / 80 / 70 / 59% correct) | Turns "59% right" into a rule for the pipeline | Four fixed-head runs (about 12 min on Colab), then laptop |
| 3 | Parameter-matched LoRA (rank 43, 49.6M parameters, alpha 86) | Answers "HydraLoRA just has 2.7x the parameters" | One run, about 2 h |
| 4 | Head-similarity heatmap (cosine between B heads, per layer) | Shows whether the heads learned different things | CPU, adapters from Drive |
| 5 | 2 more seeds per model | Error bars | About 12 h |
| 6 | Data scaling (25 / 50 / 100%) | Tests the data-fragmentation explanation | Only if time allows |

---

## 8. Limitations to state

- One seed; about 32 questions per bucket, so only large differences reach significance.
- Placeholder base model; results must be re-run on Agent 2's distilled and native bases.
- Training dropped 11.5% of examples longer than 1,024 tokens (the largest databases); training on Agent 1's pruned schema would keep them.
- Hyperparameters untuned (rank 16, LR 2e-4); a small sweep is needed for a fair baseline.

---

## 9. 2-minute script (about 230 words)

> Good morning. I'm K.G.Y.V. Thathsarani, and my component is Agent 3, which writes the SQL.
>
> The problem: text-to-SQL is not one task. A simple lookup and a three-table join need different reasoning, and a small model has little capacity to learn both. With one standard LoRA adapter, my results show exactly that: single-join accuracy rose from 0.29 to 0.68, but multi-join did not improve at all.
>
> My approach is HydraLoRA keyed to query complexity: one shared down-projection, and a separate up-projection head for simple, single-join, multi-join and aggregation questions, chosen by the complexity label from Agent 1. The routing is a fixed rule, so every choice is auditable.
>
> On 128 Spider and Chinook questions, standard LoRA scores 0.55 against 0.41 untrained, which is significant. HydraLoRA with correct labels scores 0.52, not significantly different, but it writes closer-to-gold SQL. With the live classifier it drops to 0.39, so routing accuracy matters a lot, and Agent 1's improved classifier should recover most of that.
>
> My error analysis shows why multi-join fails: the model uses a real column through the wrong table. Next I'll run a routing-error curve and a parameter-matched LoRA, so the comparison is fair.
>
> One shared base model with small heads is what makes this practical on one mid-range GPU. Thank you.

---

## 10. Q&A preparation

| Question | Answer skeleton |
|---|---|
| Is HydraLoRA your idea? | No (arXiv 2404.19245). Keying its heads to SQL complexity with a supervised router, and measuring it on a small model, is the contribution. |
| HydraLoRA lost to LoRA. So what? | Not significantly (p = .45), and it wins on exact match. A negative or neutral result is valid; the routing curve and parameter-matched LoRA say why. |
| HydraLoRA has 2.7x the parameters. | Yes: the parameter-matched LoRA (rank 43) is the next run. |
| Why not learn the router? | Auditable, and avoids gating collapse; the cost is visible as the 13-point routing loss. |
| Why does multi-join fail for both? | Wrong-table column references and missing tables (error analysis); only 375 multi-join training examples. |
| What if the classifier is wrong? | Measured: .52 → .39. The new classifier routes 68% correctly; the curve gives the accuracy needed for HydraLoRA to beat LoRA. |
| What did you build yourself? | Dataset builder, LoRA training, the HydraLoRA module (shared A, four B heads, routing self-test), evaluation and paired-comparison scripts. |
| How did you use AI tools? | Match the AI-use record and diary. |

---

## 11. Evidence checklist

- [x] LoRA baseline vs untrained base, per bucket, paired test
- [x] HydraLoRA trained; routing self-test; correct-label vs live-classifier comparison
- [ ] Error analysis checked by hand (draft labels above)
- [ ] Four fixed-head runs → routing-error curve, and HydraLoRA with the new classifier
- [ ] Parameter-matched LoRA (rank 43)
- [ ] `generate(question, ddl, hint=None, dialect=...)` plugged into the harness (`create_app(generate=...)`), head shown in the chat trace
- [ ] Agent 1 handoff format signed off
- [ ] Component diagram drawn by hand
- [ ] Script timed at 2 minutes
