# PP1 Panel Response — J.K.B. Ekanayake (IT23199262)

Component: **Agent 1 — Complexity-adaptive, data-minimised schema context for small language models** | Project J26-DS-336
Answers the proposal-presentation panel comments (panel DS-P03) for Progress Presentation 1. Rewritten 19 Oct 2026 with the new results; the earlier draft is in git history. Figures marked **[MEASURED]** come from this repository's own runs; the commands are in Section 9. Updated 19 Oct 2026.

---

## 1. The proposal panel comments and the PP1 answer

Proposal-presentation comments: *"Implement standalone application. Don't have proper component breakdown. Not explained novelty properly (what's the importance of SLM over LM). Need to think about practical usage."*

| Panel comment | PP1 answer (one line) | Evidence to show | Section |
|---|---|---|---|
| Implement standalone application | Agent 1 runs on its own as a service with its own pages; the full pipeline also runs end to end. | Live demo: Explorer, chat with pipeline trace, add-database panel, dashboard | 5 |
| No proper component breakdown | Five sub-agents, each with one decision and a defined input and output. | Component diagram + the chat page's per-agent input/output trace | 4 |
| Novelty not explained (SLM over LM) | The idea is sizing and minimising schema context for small models; I measured that small models need it and large ones do not. | Simple questions: phi3 .35 with wide context vs .71 with narrow | 2, 3 |
| Practical usage | A bank analyst on the bank's own read-only database, with personal data protected and answers promoted to BI dashboards. | Scenario run on PostgreSQL, value hints on coded columns | 6 |

---

## 2. Novelty: one named idea

**Complexity-adaptive, data-minimised schema context for small language models.**

Agent 1 decides how much of the database a small model sees, based on how complex the question is, and shows it the least data that still answers it. Three parts:

| Part | What it does | Evidence [MEASURED] |
|---|---|---|
| Complexity-aware sizing | Predicts complexity from the question **and the database's structure**, then sets the context width (anchor table only for simple questions, connected tables for joins) | Classifier .588 → .676 on 148 questions (22 fixed / 9 broken, McNemar p = .029). Adaptive width, phi3: .44 → .52 with correct labels (12 / 1, p = .003), .49 with the classifier (p = .065) |
| Data-minimised context | Column-level pruning inside the retrieved tables, with a recorded reason for every kept column | Tokens −27 [−34, −20] (−16%) at column recall .98; −24% on the unseen Northwind database |
| Value hints with a privacy switch | Shows a column's stored codes (`/* values: '0', '1' */`) so the model stops guessing; switched off for personal-data databases | Value-coded questions: Qwen2.5-Coder-1.5B .12 → .56 (p = .016), phi3 .31 → .69 (p = .11); no harm on 148 ordinary questions |

**Say:** "Schema linking already exists. What is new here is sizing the schema to the question's complexity for small models, and showing the model the minimum data, with measured evidence of why small models need it."

**Do not say:** "a new retrieval algorithm", or "multi-agent small-model text-to-SQL is new".

| Prior work | What it already does | Difference |
|---|---|---|
| GRASP, RASL, RSL-SQL, SchemaGraphSQL | Stronger schema retrieval, aimed at large models | I target small local models, context width and data minimisation, not retrieval accuracy alone |
| QCMA-SQL (Findings of NAACL 2025) | Routes questions by difficulty with a schema selector | Closest work: read the full paper and state the difference before PP1. Mine sets schema width from predicted complexity, measured on 1.5–4B models |
| AutoLink (arXiv 2511.17190) | Re-retrieves schema after "no such column" errors, on large models | Not used as a claim |
| MATS (arXiv 2512.18622) | Multi-agent small-model text-to-SQL | The pipeline shape is not claimed as new |
| CHESS, CodeS | Match database values | Value hints are a measured fix with a privacy switch, not a new technique |

---

## 3. Why a small model, and why it needs this component

1. **Why an SLM at all.** Regulated enterprises cannot send their data to cloud generative-AI vendors under their AI-governance and vendor-risk policies, so the model must run on-premise. A large model does not fit on mid-range hardware, and a local SLM has no per-query fees. The SLM is the only option that fits.
2. **Why the SLM needs Agent 1.** Strong large models cope with the whole schema ("The Death of Schema Linking?", arXiv 2408.07702). Small models gain most from schema linking (BRACIS 2025, models up to 3B). My own data shows the same thing.

| Simple questions, n = 33 [MEASURED] | Wide context (3 tables) | Narrow context (anchor table) |
|---|---|---|
| phi3 | .35 | .71 |
| Qwen2.5-Coder-1.5B | .61 | .74 |

The extra tables distract the small model into joins the question never asked for. Real example (tvshow): wide context gave `SELECT pc.Package_Option FROM Cartoon c JOIN TV_Channel tc ...` (fails); narrow context gave `SELECT Package_Option FROM TV_Channel WHERE series_name = 'Sky Radio'` (correct).

**One line for the panel:** "With a large model you can paste the whole schema. With a small model you can't. I measured what that costs and built the component that fixes it."

---

## 4. Component breakdown: five sub-agents

| # | Sub-agent | Decision | Input → Output | Code |
|---|---|---|---|---|
| 1 | Complexity classifier | How complex is the question? | question + schema names/FKs → label + confidence | `complexity.py` (`classify_query`, `p_simple`, `schema_features`) |
| 2 | Anchor selection | Where does retrieval start? | question → top-3 tables (ChromaDB semantic match, or keyword match) | `retrieval.py` |
| 3 | FK traversal and bridging | Which connected tables are needed? | anchors → tables joined by shortest FK paths, bridge tables added | `retrieval.py`, `schema.py` |
| 4 | Pruning and value hints | Which columns, and which values to show? | tables + question → kept columns, each with a reason; code values for coded columns | `pruning.py`, `linking.py` |
| 5 | Context sizing and handoff | How wide, and what goes to Agent 3? | label + tables → pruned DDL + complexity + trace (JSON) | `retrieval.py`, `agent.py` |

Output contract to Agent 3: `query, complexity, mode, anchor, matched, tables, ddl, tokens, latency_ms, trace`. JSON with the DDL inside; still needs Thathsarani's sign-off.

**Diagram:** draw the five boxes left to right with the data on each arrow, in draw.io, black and white (the template does not allow AI-generated diagrams).

---

## 5. Standalone application: demo plan

Start: `uvicorn harness.app:app --port 8765`, then open http://localhost:8765.

| Page | Shows | Panel point |
|---|---|---|
| Retrieval Explorer `/` | One question in all four modes; each sub-agent's output; kept vs removed columns with reasons | Component breakdown, Agent 1 on its own |
| Chat `/chat` | Four-stage pipeline strip (gate → retrieval → generation → execution); each agent's input and output; stand-ins badged honestly | How Agent 1 fits the system |
| Add a database (on `/chat`) | Drag a SQLite file, or paste a PostgreSQL link; "don't read data values" switch | Works on any database, not sample data |
| Dashboard `/dashboard` | Saved answers as live charts; CSV link for Power BI / Excel | Practical usage |
| API | `POST /retrieve` (Agent 1 only), `POST /query`, CLI `python -m agent1_retrieval "question" --json` | Standalone service |

Warm the service up with one question per database before the demo (the first query loads the models).

---

## 6. Practical usage: one bank scenario

1. An analyst connects the bank's PostgreSQL database through a **read-only** login and ticks "don't read data values" because it holds customer data.
2. They ask "total deposits per branch this month". Agent 1 sends only the tables and columns the question needs; nothing leaves the bank's data centre.
3. The answer shows its SQL, so the analyst can check it (Section 8: plausible-looking wrong answers exist).
4. They save it to the dashboard. The Power BI report reads the CSV link every morning: the saved SQL is re-run read-only and the model is not called again.

**A real problem it solves:** banks store status as codes (`'A'` / `'C'`, `0` / `1`). Without value hints the model writes `Discontinued = 'Yes'`, the query runs and silently returns 0 rows, so no error triggers a retry. With the hint it writes `= '1'` and gets the right 8 rows (Northwind, verified against the database).

Security already in place: read-only connections, a one-statement rule, a SELECT-only guard, a 10 s query timeout, no raw database paths from clients. **Open:** the harness has no login yet, so it runs on a private network only.

---

## 7. Results

### 7a. Agent 1 on its own (no language model involved) [MEASURED]

These compare Agent 1's schema with the columns the gold SQL actually uses, so no model choice can affect them.

| Measure | Result |
|---|---|
| Column recall, pruned (final config) | Spider .98, Chinook .95, TPC-H .97, Northwind .99 (never tuned on) |
| Tokens, pruned vs unpruned (same anchors) | −27 [−34, −20] (−16%) on Chinook + Spider; Northwind 299 → 227 (−24%) |
| Column precision, pruned vs unpruned | +.04 [.03, .05] (final config is tuned for recall) |
| Multi-join table recall | .75 → .94 (top-3 anchors + FK bridging) |
| Recall fixes (stop-word bug, name splitting, label columns) | Chinook .73 → .95, TPC-H .46 → .97, Spider .89 → .98 |
| Complexity classifier (148 routing questions) | .588 → .676 (p = .029); Spider dev .57 → .64; Chinook .57 → .93 |
| Latency (warm, n = 148) | median 278 ms, p95 380 ms; classifier adds about 21 ms (target < 500 ms) |
| Off-topic gate | 0 of 148 genuine questions wrongly declined |

### 7b. Effect on final answers (stand-in SQL models) [MEASURED]

Execution accuracy needs a model to write the SQL; until Agent 3's fine-tuned model is ready, phi3 and Qwen2.5-Coder-1.5B stand in. These results check that Agent 1's choices help, or at least do not break, the answers.

| Experiment | Result | Test |
|---|---|---|
| Pruned vs unpruned, phi3, n = 128 | .43 vs .41 | McNemar p = .69, not significant: smaller prompts, same accuracy |
| Pruning at column recall .92 (before fixes) | .33 vs .41; multi-join .22 vs .38 | p = .035: pruning hurts unless recall is near-perfect |
| Value hints, value-coded set, n = 16 | Qwen .12 → .56; phi3 .31 → .69 | Qwen p = .016 |
| Adaptive width, n = 134 | phi3 .44 → .52 (correct labels) / .49 (classifier); Qwen .44 → .47 | phi3 p = .003 / .065; Qwen n.s. |
| Effect of the new classifier on Agent 3's HydraLoRA | .39 → an estimated .45–.54 (correct labels .52) | Offline estimate; 12 of 128 questions need Agent 3's fixed-head runs |

**Honest reading:** pruning alone saves tokens without costing accuracy but has not been shown to raise it. Value hints and the classifier are significant gains. Adaptive width is a real effect whose size depends on how easily the model is distracted.

---

## 8. Limitations to state before the panel finds them

- All execution accuracy uses untuned stand-in models; the final numbers come from Agent 3's fine-tuned model.
- About 32 questions per bucket: only large effects reach significance.
- Plausible wrong answers: on Northwind PostgreSQL, phi3 joined suppliers instead of shippers (both have `companyname`). Hence the SQL is always shown.
- Simple vs single-join is still the classifier's main confusion (10 of 37 single-join questions labelled simple).
- Word matching needs readable column names; new naming styles may still need splitting rules.

---

## 9. Reproduce

| Result | Command | Output |
|---|---|---|
| 7a retrieval, 7b pruning | `python -m agent1_retrieval.evaluate --pairs eval/chinook_pairs.json eval/spider_pairs.json --recommended --exec phi3` | `data/exec_phi3_recommended.log` |
| Pruning at recall .92 | same with `--anchors 3 --ungated` | `data/exec_phi3_anchors3.log` |
| Value hints | `... --pairs eval/value_coded_pairs.json --recommended --exec <model>`, then with `--value-hints` | printed |
| Adaptive width | `python -m scripts.adaptive_width phi3` / `qwen2.5-coder:1.5b-instruct` | `data/adaptive_width_*.log` |
| Classifier | `python -m scripts.train_complexity_schema` | `data/train_complexity_schema.log` (FIXED / BROKE per question) |
| Tests | `python -m pytest tests` | 66 pass, 12 skip without PostgreSQL |

Full write-up with before/after examples for every finding: the "Agent 1 Research Summary — Ekanayake" doc (Summary and Evidence tabs).

---

## 10. 2-minute script (about 240 words)

> Good morning. I'm J.K.B. Ekanayake, and my component is Agent 1: it decides how much of the database a small language model gets to see.
>
> Why does that matter? Banks can't send their data to cloud AI vendors, so the model has to run on their own mid-range hardware, and that means a small model. A large model can read a whole schema. A small one gets distracted: on simple questions, phi3 scores 0.35 with three tables in front of it and 0.71 with just the right one.
>
> So Agent 1 has five sub-agents. A classifier predicts how complex the question is, using the database's structure as well as the wording. Anchor selection finds the starting tables, traversal adds the tables that connect them, pruning keeps only the columns the question needs and records why, and a sizing step decides how wide the final schema should be.
>
> Results, on twenty Spider databases I never tuned on, plus Chinook, TPC-H and Northwind: prompts are 16 to 24 percent smaller with column recall at 0.98. The new classifier raised routing accuracy from 0.59 to 0.68, which Agent 3's HydraLoRA depends on. Value hints fixed coded columns, from 0.12 to 0.56.
>
> Pruning alone doesn't raise accuracy yet; it saves tokens at the same accuracy, and I'll re-test it on Agent 3's fine-tuned model.
>
> Let me show it running.

Time this out loud before using it.

---

## 11. Q&A preparation

| Question | Answer skeleton |
|---|---|
| Isn't this just RAG? | Retrieval is the standard part. The contribution is sizing and minimising the context for small models, with measured evidence of why it matters. |
| GRASP / RASL do retrieval better. | Yes, and I cite them. They target retrieval accuracy for large models; I target small local models, context width and data minimisation. |
| How is this different from QCMA-SQL? | It routes by difficulty to agents; I set the schema width from predicted complexity and measure it on 1.5–4B models. (Confirm from the full paper first.) |
| Your accuracy uses phi3. | Section 7a needs no model. Execution accuracy is checked on two stand-ins, and the final re-run uses Agent 3's fine-tuned Qwen model. |
| Is it significant? | Value hints, the classifier and adaptive width with correct labels are. Pruning alone is neutral on accuracy and saves tokens: an honest result. |
| What if pruning drops a needed column? | Retries can't recover it, so recall must be near-perfect: keys, label columns and narrow tables are always kept (recall .98). Example: Phase 6 dropped `Genre.Name`; the final config keeps it. |
| Why a hard-coded rule for width, not a learned one? | Auditable and explainable per question (the trace says why), and the training data is thin where it matters: only 396 of about 6,000 Spider training questions are multi-join. |
| Does Agent 1 read personal data? | Only if allowed: "don't read data values" turns off value linking and hints; the classifier uses names and FKs only. |
| How did you use AI tools? | Match the AI-use record and diary. |

---

## 12. Evidence checklist

- [x] Standalone service, CLI and pages (Explorer, chat, dashboard, add database)
- [x] Five-sub-agent breakdown with inputs and outputs (table above; trace in `/chat`)
- [ ] Component diagram drawn by hand in draw.io (black and white)
- [x] Model-free retrieval results on four databases incl. one never tuned on
- [x] Execution results on two stand-in models with paired tests
- [x] Before/after examples for every finding (Evidence tab)
- [ ] Read QCMA-SQL, GRASP and RASL in full; verify all citations
- [ ] Handoff format signed off by Thathsarani
- [ ] Re-run Section 7b on Agent 3's fine-tuned model
- [ ] Demo recording + backups in two places
- [ ] Script timed at 2 minutes
