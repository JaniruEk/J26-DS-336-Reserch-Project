# PP1 — Fixes, System Changes and Flow (one-page-per-question summary)

Project J26-DS-336 | Panel DS-P03 | 16 Oct 2026
Companion files: `PP1_Runtime_Flow.png` (the live flow with component breakdown), `PP1_Offline_Build_Flow.png` (the build pipeline), and the team and per-student documents (00–04).

**Update 21 Oct 2026:** both diagrams were redrawn (`python -m scripts.draw_flows`) to match the system as built. Agent 4 is now adaptive mixed-precision quantization (INT8 for the layers SQL depends on, INT4 for the rest) instead of QAT vs PTQ (scope change, 19 Oct). Agent 2's distilled model now runs live as the question gate. The chat front end, input checks and SQL guard are built, so they are no longer marked new. In both diagrams, solid boxes run today and dashed, shaded boxes are stand-ins or planned. Sections 3–5 below are updated to match; the rest of this file is the 16 Oct PP1 snapshot.

---

## 0. Reality check against this repository (read first)

This document was drafted against an engineering plan whose paths do not exist in this repo or on any teammate branch: `shared/orchestrator/routes.py`, `shared/schemas/`, `shared/db_proxies/`, `IMPLEMENTATION_PLAN.md`, `configs/models.yaml`, `agent4_*/…/execution_diagnosis.py`, `generation_agent.py`. The real shared code is [harness/app.py](../harness/app.py) (FastAPI). Against that code:

| Item | Doc says | Actually in the repo today |
|---|---|---|
| C3 retry ownership | Must move the retry loop into the controller | **Already done.** `POST /query` owns the loop (`MAX_ATTEMPTS=3`). It calls `generate` and `execute` separately and logs every attempt to `data/handoff.log.jsonl`. Agents 3 and 4 plug in through `create_app(generate=..., execute=...)`, so Agent 4 never imports Agent 3. Remaining task: Karunanayake's error-diagnosis hint replaces the raw DB-error hint. |
| C5 read-only connections | New | **Done** for SQLite (`file:...?mode=ro`). SELECT-only / single-statement guard: **not done**. Note that the read-only connection already blocks writes. |
| C4 input validation | New | **Partly done.** Unknown DB key → 404 (never a raw path); invalid mode → 422. Empty question, maximum length and API key: **not done**. |
| C2 public API | New `POST /query` + `QueryResponse` | **Partly done.** `POST /query` returns `trace, ok, sql, rows / error, attempts, context` (Agent 1's payload). Missing: per-agent timings in the response, `GET /health`, `GET /models`, and a written schema file. |
| C6 standalone Agent 1 | New | **Done:** `POST /retrieve` + CLI (`python -m agent1_retrieval "q" --json`). Explorer page: **not done**. |
| C9 vertical slice (M0) | New milestone | **Exists already** with stand-ins: real Agent 1 → phi3 via Ollama → sqlite execution with retry. The model report recommends replacing phi3 with Qwen2.5-Coder-1.5B-Instruct. |
| "Enterprise HR schema" (runtime diagram) | Target DB | **Not in the repo.** Only Chinook, TPC-H and Spider exist. Remove it from the diagram or build it. |
| Complexity classifier | Planned | **Done:** `classify_query` (TF-IDF + LogReg), accuracy .57 on Spider dev. Also `classify_sql` for gold labels. |

**Update (16 Oct, branch `pp1-demo`):** C1 chat UI (`GET /chat`, per-agent trace), C2 timings + `/health`, C4 empty/long/off-topic checks, C5 stand-in SELECT-only guard (blocked requests are refused, not retried), and C6 Agent 1 explorer (`GET /`) are now built in `harness/`. Remaining: Agent 4's real guard and error-diagnosis hint, fixtures (C7), the end-to-end benchmark (C8), and replay mode (C10, optional).

---

## The short answers

1. **Does the system need changes?** Yes, but the research design does not. The four-agent split, each component's research question and the offline pipeline all stay. What changes is the *product around them*: a front end, input checks, a SQL guard, and a demo-ready end-to-end slice. The slice already runs with stand-in models in `harness/app.py`.
2. **What is the flow?** One query passes through a front end and a controller, then three live agents (retrieval, generation, execution) with a bounded retry loop owned by the controller. Agent 2's distilled classifier now runs live as the question gate, after Agent 1 (updated 21 Oct). See `PP1_Runtime_Flow.png`.
3. **What is the breakdown?** Four layers (user and presentation, orchestration, live agents, data and model stores). Each agent is split into sub-components with a stated input and output (Section 3).

---

## 1. Each comment, in brief, with its fix

| ID | Brief description | Fix |
|---|---|---|
| P1 | "Don't have proper component breakdown". | Show the four-layer breakdown and the I/O of every component (Section 3 and the runtime diagram). Make the live UI show each agent's output in its own panel. |
| P2 | "Not explained novelty properly (importance of SLM over LM)". | Three-reason answer (data may not go to a generative-AI vendor; recurring cost and dependency; mid-range hardware) and one novelty line per component, backed by a measured accuracy, latency and VRAM table. |
| P3 | "Need to think about practical usage". | Named persona (analyst, DBA, compliance officer at a regional bank or insurer), a realistic demo scenario, a chatbot front end, and user sessions with real task feedback. |
| P4 | Ekanayake only: "Implement standalone application". | `POST /retrieve` and the CLI already exist; add the explorer page (C6). It also plugs into the full chatbot. |
| F1 | "Testing, feedbacks". | Test pyramid from unit to user level; at least two user sessions with observed tasks; feedback turned into Planner tasks (team doc, Section 5). |
| F2 | "Flow eka (diagram or anything)". | The two diagrams delivered with this file. Redraw by hand or in draw.io if the PP1 rules require it (Section 6). |
| F3 | "Frontend ekath oni (chatbot)". | Chat UI with a trace panel (C1) on top of `POST /query` (C2). |
| F4 | "Ekkanek explain karannalu..." | One memorised 30-second whole-system explanation per member; one presenter for the overall slides. |
| F5 | "Separate components 4 ... flow ekalu". | The runtime diagram shows them separately with labelled arrows; the controller-owned retry keeps them separate in code too (already true in the harness). |
| F6 | "Wrong inputs dala pennannat onilu". | Input validation (C4), SQL guard (C5), and the wrong-input matrix with at least two cases shown live. |
| F7 | "API hadagena yana sample data witarak neme". | Held-out question sets, more than one database, awkward schemas, and a live question from the panel (C7). |
| F8 | "Security, fast wage non-functional req...". | A benchmark and checks that produce real numbers for two or three requirements (C8); say honestly which are not measured. |
| F9 | "Backup / demo tiyaganna". | Recorded fallback video, backups in two other places, and an optional clearly labelled replay mode (C10). |

---

## 2. Changes needed to the system

| # | Change | Why | Where in this repo | Owner | Priority | Status |
|---|---|---|---|---|---|---|
| C1 | **Chat front end with pipeline-trace panel** (question box, DB selector, SQL, result table, one trace section per agent). Streamlit or Gradio. | F3, P3, P1, F5 | new `frontend/` | Team decides the shell; each member their trace section | Must | Not started |
| C2 | **Complete the public API:** add per-agent timings to the `POST /query` response, `GET /health`, `GET /models` (Agent 2's model card); write the response shape down as a schema. | F3, F5, F8 | `harness/app.py`, new `shared/schemas/` | Harness owner | Must | Partly done |
| C3 | **Controller-owned retry.** | P1, F5 | `harness/app.py` | — | — | **Done**; only the error-diagnosis hint is still a stand-in (Karunanayake) |
| C4 | **Input validation and access check:** empty / too long → clear message; optional API key. | F6, F8 | `harness/app.py` (`Query` model) | Harness owner | Must (validation), Should (API key) | DB key + mode checks done |
| C5 | **SQL safety guard:** SELECT-only, one statement. | F6, F8, P3 | Agent 4's `execute` | Karunanayake | Must | Read-only connection done; guard not done |
| C6 | **Standalone entry points per agent;** Agent 1 explorer page. | P4, F1, F5 | Agent 1: `/retrieve` exists | Each member | Must for Agent 1 | Endpoint done; explorer not done |
| C7 | **Held-out and wrong-input fixtures.** | F7, F6, F1 | `tests/fixtures/` | Each member; team for the shared set | Must | Agent 1 already evaluated on TPC-H + 20 Spider DBs |
| C8 | **NFR benchmark:** per-agent time, end-to-end latency (median and slowest over N runs), VRAM, no outbound network during a query. | F8 | new `benchmarks/` | Team; Karunanayake for VRAM | Must for 2–3 NFRs | Agent 1 mean latency measured (317 ms) |
| C9 | **Vertical slice with placeholder models**, labelled as placeholder. | F1, F3, F5, F7 | `harness/app.py` | Team | Must | **Runs today** (phi3 stand-in); swap to the agreed placeholder |
| C10 | **Optional replay mode** with a visible "recorded replay" banner. | F9 | harness + `demo/` | Harness owner | Should | Not started |
| C11 | **Update the plan and docs** with the above. | all | `Execution_Plan_J26-DS-336.md`, `pp1/` | — | Should | — |

**Note on retry ownership.** All four proposals say the harness executes the bounded retry branch "between Agent 4's Error-Diagnosis Sub-Agent and Agent 3's Generation Sub-Agent", with each attempt logged. `harness/app.py` already works this way. If any teammate's own code has Agent 4 calling Agent 3's package directly, that code should switch to returning `(ok, rows | error + hint)` and let the harness retry. Otherwise Agent 4 depends on Agent 3's internals, which is exactly what the "component breakdown" comment would probe.

**What does not need to change:** the four-agent split and owners; the research design and metrics; the offline pipeline. The Agent 1 → Agent 3 contract (`query, complexity, mode, anchor, tables, ddl, tokens, latency_ms`) still needs Thathsarani's sign-off. The generation stand-in already accepts an optional `hint`.

---

## 3. Component breakdown

Status key: **Built** = runs in this repo today; **Stand-in** = runs with a placeholder; **Planned** = specified, not built; **New** = not in the plan before PP1.

| Layer | Component | Owner | Input | Output | Status |
|---|---|---|---|---|---|
| 1 Presentation | Chat front end with trace panel | Team | Question, DB choice | Answer, SQL, rows, trace | New |
| 2 Orchestration | Input validation and access check | Harness owner | Raw request | Validated request or clear error | Partly built (DB key, mode) |
| 2 Orchestration | Pipeline controller (sequence + bounded retry) | Harness owner | Validated request | Response | **Built** |
| 2 Orchestration | Trace and structured log | Harness owner | Every handoff | Log file; trace id in response | **Built** (UI exposure new) |
| 3 Agent 1 | Complexity classifier | Ekanayake (shared) | Question | Complexity label | **Built** |
| 3 Agent 1 | Anchor selection | Ekanayake | Question, schema index | Anchor table(s) | **Built** |
| 3 Agent 1 | FK-graph traversal | Ekanayake | Anchor, FK graph | Joined tables | **Built** |
| 3 Agent 1 | Column pruning | Ekanayake | Selected tables, question | Pruned schema (JSON + DDL) | **Built** |
| 3 Agent 3 | Head selection | Thathsarani | Complexity label | Chosen adapter or head | Planned |
| 3 Agent 3 | SQL generation | Thathsarani | Question, pruned DDL, label, optional hint | Candidate SQL | Stand-in (phi3 via Ollama) |
| 3 Agent 4 | SQL safety guard | Karunanayake | Candidate SQL | Pass or rejection | New (read-only connection built) |
| 3 Agent 4 | Execution | Karunanayake | Safe SQL | Rows or error | Stand-in (`run_sql`) |
| 3 Agent 4 | Error diagnosis | Karunanayake | Error text | Hint for retry | Stand-in (raw error as hint) |
| 4 Stores | Target databases (read-only) | Shared | SQL | Rows | **Built** (Chinook, TPC-H, Spider) |
| 4 Stores | ChromaDB schema index | Ekanayake | Table DDL embeddings | Nearest tables | **Built** |
| 4 Stores | Model store (Qwen2.5-1.5B-Instruct, Agent 2's gate adapter, Agent 4's INT4/INT8 layer plan, Agent 3's adapters) | Wathsala, Thathsarani, Karunanayake | Offline artefacts | Models loaded by the app | Partly built (gate adapter and Agent 4's model load today; Agent 3's adapters planned) |
| Offline | Agent 2: distillation | Wathsala | Teacher (Qwen2.5-7B-Instruct), two classification tasks | Distilled 1.5B question classifier (live gate); distilled SQL base still planned | Classifier built (KD vs native: Task 1 n.s., Task 2 p = .004) |
| Offline | Agent 3: LoRA vs HydraLoRA | Thathsarani | Base model, labelled data | Winner + runner-up artefacts | First comparison done (preliminary: winner LoRA .56, runner-up HydraLoRA .52) |
| Offline | Agent 4: adaptive mixed precision (layer sensitivity → INT8 for sensitive layers, INT4 for the rest), compared with FP16 / uniform INT8 / uniform INT4; re-run on Agent 3's winner, cross-check on the runner-up (proposed) | Karunanayake | Released Qwen2.5-1.5B-Instruct today; Agent 3's winner and runner-up later | Mixed INT4/INT8 model (in the app as `J26_GENERATOR=adaptive_qwen`) | Built on the released model (6 of 28 layers INT8); re-run on the fine-tuned model planned |

Confirm the teammates' rows against their own branches before presenting anything as working.

---

## 4. The flow of one query (matches the numbers in the runtime diagram)

1. The analyst types a question in the chat front end.
2. The front end sends `POST /query`.
3. The input check validates the request. An invalid request stops here with a clear message.
4. **Agent 1:** the question and DB go in. The classifier labels the question; anchor selection, FK traversal and column pruning produce the pruned schema. The label and the schema come back.
5. **Agent 3:** the controller sends the question, the pruned schema and the label. Head selection picks the adapter or head; generation writes candidate SQL.
6. **Agent 4:** the guard checks the SQL, and execution runs it on the read-only database. On success, rows come back.
7. **On failure:** error diagnosis returns an error and a hint to the controller, which calls Agent 3 again with the hint, up to N attempts (N = 3 today). Every attempt is logged. When attempts run out, the controller returns a clear failure instead of looping.
8. The controller assembles the response (SQL, rows, attempt count, trace) and the front end renders it with one trace section per agent.

Update 21 Oct: Agent 2 is now part of this path as the question gate. After Agent 1 (step 4), her distilled classifier and Agent 1's word check must both say the question is about the data; otherwise the question is declined before any SQL is written. Her distilled SQL base model, when it exists, will still be an offline artefact that Agent 3 loads through the model store.

## 5. The offline flow

Agent 2 (Qwen2.5-7B-Instruct teacher, two classification tasks, KD and native 1.5B students, comparison) publishes the distilled classifier used as the live question gate; a distilled SQL base for Agent 3 is planned. Agent 3 (LoRA vs HydraLoRA under identical conditions on Qwen2.5-1.5B-Instruct; winner and runner-up published) feeds Agent 4. Agent 4 measures each layer's sensitivity for SQL, keeps the most sensitive layers at INT8 and the rest at INT4, and compares the mixed model with FP16, uniform INT8 and uniform INT4; today on the released Qwen, later on Agent 3's winner, with a proposed cross-check on the runner-up. QAT vs PTQ was dropped (scope change, 19 Oct). See `PP1_Offline_Build_Flow.png`.

## 6. About the diagrams

- They are black and white; shaded, dashed boxes mark what is new.
- The proposal template said diagrams must not be produced with AI tools. If the supervisors apply that rule to PP1, redraw these by hand or in draw.io and use the PNGs only as reference.
- Done 21 Oct: "Enterprise HR schema" removed from the target-database box (the real list is shown); the SQL safety guard is drawn as built. The diagrams are produced by `scripts/draw_flows.py`, so edit the text there and re-run instead of editing the PNGs.

## 7. Order of work

1. Agree who owns the harness and the front-end shell; get Thathsarani's sign-off on the Agent 1 contract.
2. Add C4 checks and C2 timings / `/health` to `harness/app.py`; Karunanayake adds the C5 guard.
3. Build C1 (chat UI with trace sections) and the Agent 1 explorer (C6).
4. Fixtures (C7) and the benchmark (C8).
5. Record the fallback video, back up to two other places, rehearse.
6. Update the plan and docs (C11).
