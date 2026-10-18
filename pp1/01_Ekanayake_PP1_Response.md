# PP1 Panel Response — J.K.B. Ekanayake (IT23199262)

Component: **Agent 1 — Dynamic Schema Retrieval and Column-Level Pruning** | Project J26-DS-336 | Panel DS-P03
Read this with the team document (00). Figures marked **[MEASURED]** come from this repository's own runs (commands in Section 8). Items still marked **[EVIDENCE NEEDED]** have not been produced yet.

---

## 1. Panel comments: answers and fixes

| Panel comment | What to say | Status / fix before PP1 | Evidence to show |
|---|---|---|---|
| **Implement standalone application** | My component runs on its own as a service and also plugs into the full pipeline. Give it a question and a database and it returns the pruned schema without any other agent running. | **Done:** CLI (`python -m agent1_retrieval "question" --json`) and `POST /retrieve` in `harness/app.py`. **Done:** Retrieval Explorer at `GET /` (`uvicorn harness.app:app`, open http://localhost:8000): pick DB, type a question, see all four modes, each sub-agent's output, kept vs removed columns, tokens and the DDL handed to Agent 3. | Live standalone demo; explorer screenshot |
| **Don't have proper component breakdown** | Agent 1 has three sub-agents. Anchor-Selection decides where retrieval starts (ChromaDB semantic match, or keyword match). Traversal decides which related tables to add (FK graph). Pruning decides which columns to keep. Each one makes a single bounded decision. Input: question + live DB. Output: pruned schema + complexity label. | Show the three sub-agents as three boxes with the data passed between them; show each one's output separately in the explorer. | Component diagram; per-step output |
| **Not explained novelty properly (SLM over LM)** | A small model has a small context window and little capacity to ignore noise. Table-level retrieval pastes every column of every retrieved table into the prompt. I prune columns *inside* the retrieved tables and measure the trade-off rigorously: four switchable modes, schema-linking precision/recall, per complexity bucket, with paired confidence intervals. Schema retrieval itself is an active research area (GRASP, RASL, RSL-SQL, SchemaGraphSQL). My contribution is the controlled ablation on small local models for mid-range hardware, not a new retrieval algorithm. | Done (see Section 5). Use the measured figure in place of the proposal's "about 75% irrelevant" estimate. | Token-reduction table **[MEASURED]** |
| **Need to think about practical usage** | The analyst types a question, and my component decides what the model gets to see. With fewer tokens, the prompt is cheaper to process on the bank's own modest hardware. | Use a realistic question from the team demo scenario (00, Section 9), not a toy question. | Scenario run |

**Do not claim** "none of the local tools prune columns" or "the required columns were still retrieved". Column recall drops when pruning is on (Section 5), and the panel can check this.

---

## 2. The nine feedback points, for Agent 1

| Feedback | What you do |
|---|---|
| Testing, feedbacks | Show the existing tests (`python -m pytest tests`: `test_agent1.py`, `test_harness.py`); add wrong-input tests (Section 4); one user session with the explorer. |
| Flow diagram | reflect → anchor → traverse → prune → output, each arrow labelled with its data. Redraw by hand or in draw.io. |
| Frontend (chatbot) | Agent 1's trace section: tables and columns kept, tokens before and after, mode. |
| Everyone explains | Memorise the 30-second whole-system explanation (00, Section 2.5). |
| Separate components and flows | The three sub-agents plus the handoff contract (Section 6). |
| Wrong inputs | Section 4. |
| Not only sample data | Already evaluated on Chinook, TPC-H and 20 Spider dev databases (the Spider databases were not used for tuning). Tuning was done on Chinook only (14 pairs). |
| NFRs | Retrieval latency against the 500 ms target (Section 5); missing-FK behaviour. |
| Backup / demo | Copy `data/` (DB files) and record the explorer run; store in two other places. |

---

## 3. Two key functions

1. **Schema reflection and FK graph** — [agent1_retrieval/schema.py](../agent1_retrieval/schema.py). Reads tables, columns and FKs (`PRAGMA foreign_key_list`) with no hardcoded schema. *Demo:* point it at a Spider database you never tuned on.
2. **Column-level pruning** — [agent1_retrieval/pruning.py](../agent1_retrieval/pruning.py). Keys are always kept. Otherwise a column is kept on lemma overlap with the question, falling back to spaCy similarity ≥ 0.6. *Demo:* one question in all four modes, with tokens and surviving columns.

---

## 4. Wrong inputs

| Input | Expected | Status |
|---|---|---|
| Unknown database | 404 with list of valid DBs | **Done** (`harness/app.py`) |
| Invalid mode | 422 with valid modes | **Done** |
| Empty / whitespace / >500-char question | 422 before any agent runs | **Done** (tested) |
| Gibberish / unrelated question | `matched: false`; `/query` declines without calling the model; explorer shows a warning | **Done** (tested: "best pizza recipe", "asdkjh qwelkj", "weather in Paris") |
| Missing FKs | Retrieval continues with declared FKs; `--infer-fks` adds FKs implied by column names | **Done** (tested: `tests/test_pp1_fixes.py`) |
| Runaway traversal | Bounded by `depth` (default 1) | **Done** (config) |
| Multiple SQL statements from the model | Returned as an error, not a crash | **Done** (fixed a Python 3.10 crash; tested) |

---

## 5a. PP1 fixes (Phase 8) [MEASURED, 17 Oct 2026]

Full detail and raw outputs: `reports/agent1_phase8/README.md`. Live config: `RECOMMENDED` in `agent1_retrieval/retrieval.py`; the harness and CLI now use it.

| hybrid_pruned | Before (Phase 1–7 default) | After (PP1 recommended) | hybrid, same anchors |
|---|---|---|---|
| Chinook: column recall @ tokens | .73 @ 168 | **.95 @ 200** | .95 @ 262 |
| TPC-H | .46 @ 137 | **.97 @ 241** | .97 @ 322 |
| Spider (never tuned) | .89 @ 87 | **.98 @ 138** | .99 @ 161 |

What changed:
- **TPC-H limitation fixed.** Run-together and abbreviated names (`c_acctbal`, `o_totalprice`) are now split and expanded.
- **New signals.** A small business-synonym list, plus value linking: "Canada" is found in `Customer.Country` by a read-only lookup, and only column names leave the lookup.
- **Display columns.** These are kept for tables the question names.
- **Explanations.** Every column now carries the reason it was kept or pruned, shown in the explorer and in the handoff `trace`.
- **Speed.** Retrieval is about 3× faster with identical results, because the question embedding no longer pads to 256 tokens. Mean is now about 80–120 ms against the 500 ms target.

**Execution accuracy, recommended configuration [MEASURED]** (phi3 standing in for Agent 3; Chinook + Spider, n = 134, 128 scored; run 18 Oct 2026; raw output in `data/exec_phi3_recommended.log`):

| Mode | Tokens | Column recall | Exec accuracy |
|---|---|---|---|
| semantic | 58 | .61 | .34 |
| structural | 59 | .59 | .34 |
| hybrid (same 3 anchors) | 171 | .98 | .41 |
| **hybrid_pruned** | **145** | **.98** | **.43** |

Paired, pruned vs hybrid: tokens **−27 [−34, −20]** (−16%), column recall −.00 [−.01, .00], execution +.02 (only-pruned 4, only-hybrid 2, McNemar exact p = 0.69, **not significant**). By bucket, pruned vs hybrid: simple .35 vs .39, single-join .42 vs .39, multi-join .38 vs .38, aggregation .56 vs .50.

**Reading:** with the recommended settings, pruning no longer costs recall or accuracy. It gives a 16% smaller prompt at the same accuracy. It does not yet show an accuracy *gain*, which needs Agent 3's fine-tuned model and a larger sample (about 600 paired items to detect 5 points).

**Side finding:** on *simple* questions, the narrow single-table modes score .68–.71 against .35–.39 for the wide hybrid context. Extra tables distract phi3 on easy questions, which supports complexity-adaptive context width (narrow for simple, wide for joins) as the next experiment.

## 5. Measured results [MEASURED]

**Retrieval only**: Chinook + TPC-H + Spider (20 dev DBs), n = 148, run 16 Oct 2026 (`python -m agent1_retrieval.evaluate --pairs eval/chinook_pairs.json eval/tpch_pairs.json eval/spider_pairs.json`).

| Mode | Tokens | Mean ms | Table P / R | Column P / R |
|---|---|---|---|---|
| semantic | 59 | 370 | .97 / .62 | .38 / .61 |
| structural | 58 | 43 | .91 / .59 | .35 / .59 |
| hybrid (baseline) | 149 | 274 | .67 / .92 | .26 / .92 |
| hybrid_pruned | 100 | 317 | .67 / .92 | .44 / .83 |

Paired difference, pruned vs hybrid (95% bootstrap CI): tokens **−49 [−56, −42]** (about −33%), column precision **+.18 [.16, .21]**, column recall **−.09 [−.12, −.06]**.

Per database (from Phase 3), hybrid → pruned: Chinook 251→168 tokens, column recall .95→.73. TPC-H 240→137, recall .86→.46. TPC-H recall drops because its column names are abbreviated (`c_acctbal`), which lemma and word-vector matching can't read. Report this as a limitation. Spider: 126→87, recall .93→.89.

**Execution accuracy**, with phi3 standing in for Agent 3 (Chinook + Spider, 128 scored):
- hybrid (1 anchor): .40 at 139 tokens
- pruned, default settings: about .33–.35; the loss is concentrated in multi-join questions
- pruned with the tuned setting (`multi_anchors=3, gate=False, min_cols=8`): **.41 at 142 tokens**. That matches hybrid with 3 anchors (.41) using 17% fewer tokens.

**Honest reading:** pruning reliably cuts tokens and raises precision. It costs some recall, and with the weak phi3 stand-in it breaks even on accuracy; it does not improve it. This is a valid neutral result, to be re-tested with Agent 3's fine-tuned model.

**Latency (warm, n = 148, hybrid_pruned):** median **278 ms**, p95 380 ms, max 617 ms; 1 of 148 over the 500 ms target. The first query per database is slower (index build, model load), so warm the service up before a demo. The off-topic gate (`matched`) adds a median 15 ms and wrongly declined **0 of 148** genuine questions.

---

## 6. Handoff contract

`Agent1(db, mode).run(query)` returns a JSON-serialisable dict: `query, complexity, mode, anchor, tables{table:[cols]}, ddl, tokens, latency_ms`. Proposed by Ekanayake; **still needs Thathsarani's sign-off**. Note: `shared/schemas/` is referenced in the team document but does not exist in the repo yet.

---

## 7. 2-minute script (about 210 words)

> Good morning. I'm J.K.B. Ekanayake, and my component is Agent 1: dynamic schema retrieval and column-level pruning.
>
> A small language model has a small context window. If we hand it every column of every relevant table, most of the prompt is noise, and small models are the least able to ignore it.
>
> My component receives the question and a live database. Three sub-agents run in order. Anchor-Selection finds the starting table with semantic search. Traversal follows foreign keys to the joined tables. Pruning removes the columns the question doesn't need, but always keeps the join keys.
>
> My two key functions are schema reflection with the foreign-key graph, and column-level pruning. It runs standalone, as you'll see.
>
> I tested on Chinook, TPC-H and twenty Spider databases that I never tuned on. On Spider, column recall rose from 0.89 to 0.98. Against the same retrieval without pruning, the prompt is 16% smaller, recall is unchanged, and SQL accuracy with a stand-in model was 0.43 against 0.41. That difference is not statistically significant, so the honest result is: smaller prompts, same accuracy. I'll re-test with Agent 3's fine-tuned model. Retrieval takes about 120 milliseconds, well within our 500 millisecond target.
>
> My output goes to Agent 3, which writes the SQL. Thank you.

Time this out loud before using it.

---

## 8. Q&A preparation

| Question | Answer skeleton |
|---|---|
| What exactly did I build? | Schema reflection, the four retrieval modes, column pruning, the NL complexity classifier (TF-IDF + LogReg, accuracy .57 on Spider dev vs a .25 majority baseline), the evaluation and statistics code, and the FastAPI harness. |
| Is retrieval novel? | No; the field is crowded. The contribution is the measured four-mode ablation on small local models, by complexity bucket. |
| What if pruning removes a needed column? | It happens: recall drops by .09. Keys are always kept, and `min_cols=8` restores recall to .96. Example miss: "which customers spent the most?" drops `Invoice.Total`. |
| Why does TPC-H do worse? | Abbreviated column names; this is a known limitation of lemma/vector matching. |
| Is the result significant? | Default pruning vs hybrid: McNemar p = 0.33, not significant. The current sample only detects differences of about 10 points; we are enlarging it to 600+ items. |
| Why this design? | Lemma overlap is cheap, embeddings are only used as a fallback, and hybrid retrieval reaches join tables that semantic search misses. |
| How did you use AI tools? | Match the AI-use record and diary. |

---

## 9. Evidence checklist

- [x] Standalone CLI and `POST /retrieve`
- [x] Retrieval Explorer page (recording still to do)
- [x] Token reduction, precision/recall per bucket
- [x] Held-out databases (TPC-H, 20 Spider DBs)
- [x] Latency median/p95/max
- [x] Empty-question and low-confidence handling implemented and tested
- [ ] Missing-FK test database
- [x] Trace section in the chatbot (`/chat`)
- [ ] Test-run screenshot
- [ ] One user feedback session → Planner tasks
- [ ] Git, Planner, diary, AI-use record up to date
- [ ] Backups in two places; fallback video
- [ ] Script timed at 2 minutes
