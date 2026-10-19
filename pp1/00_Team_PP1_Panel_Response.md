# J26-DS-336 — PP1 Panel Response (Team Document)

Distributed Multi-Agent SLM Framework for Privacy-Preserving Enterprise Data Intelligence
Panel: DS-P03 | Prepared 16 Oct 2026, updated 19 Oct 2026 with each member's measured results | PP1 window noted in lecture: 20–27 Oct 2026

This document turns the panel's comments and the extra feedback notes into **answers** (what we say) and **fixes** (what we build or show). Each member also has an individual file (01–04) with their own answers, two key functions, a 2-minute script and a checklist.

The lecture's rule for PP1 is the test for everything below: *"Do not say the system is fast, secure or usable. Show early evidence."* Anything marked **[EVIDENCE NEEDED]** is a number, screenshot, recording or user comment that only the team can produce. Nothing in these documents should be presented as a result until it has been measured.

---

## 1. The feedback, decoded

The panel comments are the ones in the topic-assessment table (identical for all four students, plus one extra for Ekanayake). The second list is the set of notes taken during feedback. Correct any reading below that is wrong.

| # | What was said | What it means | The fix | Evidence to show |
|---|---|---|---|---|
| P1 | "Don't have proper component breakdown" | The panel could not see four distinct components with clear boundaries | Show four separate components, each with input, processing, output and owner (Section 3) | Component diagram + I/O contract table + a live trace panel showing each agent's output separately |
| P2 | "Not explained novelty properly (what's the importance of SLM over LM)" | We never justified why a small model, and what is new | A crisp SLM-over-LM answer and a one-line novelty claim per component (Section 2.2) | Measured accuracy/latency/VRAM table; optional large-model reference run |
| P3 | "Need to think about practical usage" | Who actually uses this, in what situation | A named persona, a realistic demo scenario, and a chatbot front end (Sections 2.3, 4, 9) | User-task feedback sessions |
| P4 | "Implement standalone application" (Ekanayake only) | His component should be a runnable application, not only code or a notebook | Agent 1 runs on its own as a service plus a small explorer UI (see file 01) | Live standalone demo |
| F1 | "Testing, feedbacks" | We need testing evidence and real user feedback | Test plan + feedback sessions (Section 5) | Test report, feedback log, Planner tasks created from feedback |
| F2 | "Flow eka (diagram or anything)" | Show the flow of the system | Overall flow + offline flow diagram (Section 3) | Diagram on the design slide and in the 1–2 minute video |
| F3 | "Frontend ekath oni (chatbot)" | A front end is required, in the form of a chatbot | Thin chat UI over the FastAPI orchestrator (Section 4) | Live chat demo |
| F4 | "Ekkanek explain karannalu (samaharwita nam karailu eyawa)" | Ambiguous. Read as: everyone must be able to explain the whole system, and one person gives the overall introduction | One memorised 30-second whole-system explanation per member (Section 2.5); one presenter for the overall slides | Rehearsal round 1 |
| F5 | "Separate components 4 ... flow ekalu" | Show the four components separately, with the flow between them | Same as P1, with the flow arrows labelled with the data that moves | Trace panel in the UI |
| F6 | "Wrong inputs dala pennannat onilu" | Also demonstrate wrong or invalid inputs | Wrong-input matrix (Section 6); demo at least two live | Test results table |
| F7 | "API hadagena yana sample data witarak neme" | Do not demo only on the sample data we prepared while building | Unseen databases, held-out questions, and a live question typed by the panel (Section 7) | Held-out results, separate from development data |
| F8 | "Security, fast wage non-functional req cover wena widiha pennanna" | Show how non-functional requirements (security, speed and so on) are actually covered | NFR evidence table (Section 8) | One measurement or demo per NFR |
| F9 | "Backup / demo tiyaganna" | Keep backups and a prepared demo | Demo script, backup layers, recorded fallback (Section 9) | Recording stored in two other places |

---

## 2. Answers to the panel comments

### 2.1 "Don't have proper component breakdown"

**Answer.** The system is a four-agent pipeline. Each agent has one owner, one defined input and one defined output. Agents depend on each other only through a shared JSON contract, never through each other's internal code. Since the proposal, we have also dropped a fifth, loosely connected OLAP/MDX idea to keep the breakdown clean. Agent 3 and Agent 4 now exchange a *winner and runner-up* artefact rather than being merged under one owner.

**Fix.** Show the table in Section 3.3 and the flow in 3.1, and make the live UI show each agent's output separately.

### 2.2 "What is the importance of SLM over LM, and where is the novelty?"

**Answer (say this).** We are not claiming a small model is more accurate than a large one. We are claiming it is the only option that can be deployed under three real constraints. The accuracy gap can then be narrowed by engineering, and our four components do that.

1. **Where the data may go.** Most regulated enterprises do not send live schema or customer data to a *generative-AI vendor*. That is mainly internal AI-governance and vendor-risk policy, reinforced by regulation such as GDPR and CCPA. It is not that all third-party sharing is banned; banks share data with approved vendors every day. A model that runs on the organisation's own hardware needs no vendor approval.
2. **Cost and dependency.** A large model costs more per query as usage grows, and depends on one network-reachable cluster. A small quantized model runs close to the users.
3. **Hardware.** Our target is mid-range hardware (a single mid-range GPU, no cluster), which rules out large models.

The honest concession: an organisation that already runs large GPU clusters can self-host a large model. Our market is the much larger group that cannot.

**Why novelty is in the components, not in "multi-agent small models".** Multi-agent small-model Text-to-SQL already exists in the literature; the market-research note identifies MATS as the closest system. So we do not claim to be first at that. Each component addresses one measured weakness of small models:

| Component | What is new (one line) | Why it matters for a small model (measured) | Status, 19 Oct |
|---|---|---|---|
| Agent 1 (Ekanayake) | Complexity-adaptive, data-minimised schema context: the schema's width is set from the question's predicted complexity, and only the needed columns are shown. Retrieval itself is a crowded field and is not claimed | A wide schema distracts a small model: phi3 scores .35 on simple questions with 3 tables, .71 with the right one | Built and running; two significant gains (value hints p = .016, classifier p = .029) |
| Agent 2 (Wathsala) | Distillation as the base-model choice for SQL: distilled vs native student of the same size, identical fine-tuning, plus a gold-answer control (C0) | Only a small model can ship; the 7B teacher is used once, offline, never deployed | Pipeline validated on a pilot classifier; SQL distillation and the checkpoints for Agent 3 not built yet (critical path; fallback: released Qwen base) |
| Agent 3 (Thathsarani) | HydraLoRA heads keyed to SQL query complexity, routed by an auditable label, vs one shared LoRA adapter | One adapter helped single-join (.29 → .68) but not multi-join: a small model's capacity goes where the data is | LoRA .55 vs base .41 (p = .012); HydraLoRA .52 with correct labels (n.s. vs LoRA), .39 with the live classifier |
| Agent 4 (Karunanayake) | SQL-task-sensitive mixed precision: INT8 for the layers SQL depends on, INT4 for the rest, against generic and random layer choices with the same memory (scope changed from QAT vs PTQ) | SQL fails on one wrong character: uniform 4-bit lost 8 of 100 questions, mostly to garbled table names | Preliminary on Phi-3 (100 questions, one database); layer ranking still noise; moving to Qwen2.5-1.5B |

Each member's individual file (01–04) has the full answer, the evidence and the prior work.

**Fix.** Add one slide line for this answer and one table of measured results per component (above). Optional but strong: run the same held-out questions through a large hosted model on a *public* database (Chinook or Spider, which contain no private data) as a reference column, so the small-vs-large trade-off is shown as a measured number. **[EVIDENCE NEEDED]**

### 2.3 "Need to think about practical usage"

**Answer.**
- **Who uses it:** analysts and BI managers (daily users), DBAs (need queries to respect schema boundaries), compliance officers (need proof that no data leaves).
- **Who pays:** regional banks, mid-size insurers, credit unions and growth-stage FinTech firms, delivered as a licensed on-premise appliance.
- **Why not their existing dashboards:** dashboards answer known, pre-built questions. A new question needs a request to the BI team and can take days. Commercial conversational-BI products already sell this exact capability, which shows the demand is real. They are cloud-hosted, so regulated firms are often blocked from using them by AI-governance policy.

**Fix.** Make the demo a realistic scenario (Section 9.1), put the chatbot in front of it, and collect feedback from people in or near this role (Section 5).

### 2.4 "Implement standalone application" (Ekanayake)

See file 01. Agent 1 runs on its own: a CLI, `POST /retrieve`, and the Retrieval Explorer page (`GET /`). It also runs inside the full application: chat with a per-agent trace, adding a database by file upload or PostgreSQL link, and a dashboard of saved answers.

### 2.5 Everyone explains the whole system (F4)

Each member memorises this and can say it in 30 seconds:

> "A user types a question in plain English. Agent 1 looks at the database and keeps only the tables and columns that matter. Agent 3 is a small fine-tuned model that picks the right specialist for the question's difficulty and writes the SQL. Agent 4 runs that SQL on the local database, and if it fails it explains the error back to Agent 3 for a limited number of retries. Agent 2 built the base model that Agent 3 starts from, and Agent 4 chose the compression that lets it all run on modest hardware. Nothing leaves the organisation's own machines."

The lecture notes also say the introduction can be given by any team member; agree one person for the overall slides.

---

## 3. The flow and the four components

### 3.1 Live flow (per query) — redraw this by hand or in draw.io

The proposal template required black-and-white diagrams not made with AI tools. Treat the text below as a specification to redraw.

```
 User (analyst)
     │ types a question
     ▼
┌──────────────────────┐
│ Chatbot front end    │  validates input, shows trace + result
└─────────┬────────────┘
          │ HTTP  POST /query
          ▼
┌──────────────────────┐
│ Orchestrator (FastAPI)│  sequences agents, logs every handoff
└─────────┬────────────┘
          ▼
┌──────────────────────┐   input : question + live DB connection
│ AGENT 1  Retrieval   │   does  : reflect schema → anchor table (ChromaDB)
│ (Ekanayake)          │           → FK-graph traversal → column pruning
└─────────┬────────────┘   output: PrunedSchema JSON + complexity label
          ▼
┌──────────────────────┐   input : question + PrunedSchema + label
│ AGENT 3  Generation  │   does  : Head-Selection → Generation sub-agent
│ (Thathsarani)        │           (uses base model from Agent 2)
└─────────┬────────────┘   output: candidate SQL
          ▼
┌──────────────────────┐   input : candidate SQL
│ AGENT 4  Execution   │   does  : safety check → execute on DB
│ (Karunanayake)       │           on error: Error-Diagnosis → hint ──┐
└─────────┬────────────┘   output: result rows, or bounded failure    │
          │                                        retry (max N) back to Agent 3 ◄─┘
          ▼
 Result table + SQL + trace shown to the user
```

### 3.2 Offline flow (done once, before any query)

```
Agent 2 (Wathsala)           Agent 3 (Thathsarani)            Agent 4 (Karunanayake)
teacher ~7B → dataset   →    LoRA vs HydraLoRA on base   →    SQL-sensitive INT8/INT4 mix on Agent 3's winner
student SFT + native         winner AND runner-up              cross-check on the runner-up
baseline, compare            published as artefacts            deployable mixed-precision GGUF model
  │ base model artefact        │ finetuned_architecture          │ model used by live pipeline
```

### 3.3 Component contract table (use as the "component breakdown" slide)

| Component | Owner | Receives | Produces | Live per query? |
|---|---|---|---|---|
| Agent 1 — Retrieval and pruning | Ekanayake | Question, live DB connection | PrunedSchema JSON, complexity label | Yes |
| Agent 2 — Foundation model | Wathsala | Teacher prompts | Versioned base-model artefact (with model card) | No (built once) |
| Agent 3 — Fine-tuned generation | Thathsarani | Question, PrunedSchema, label, base model | Candidate SQL (live); winner and runner-up artefacts (offline) | Yes |
| Agent 4 — Quantized execution | Karunanayake | Candidate SQL, winner and runner-up artefacts | Result or bounded failure (live); quantization findings (offline) | Yes |

**Contracts status:** `shared/schemas/` does not exist yet and must be created and agreed before PP1. Today, only Agent 1's output is defined. It is the dict returned by `Agent1(db, mode).run(query)` (`query, complexity, mode, anchor, matched, tables, ddl, tokens, latency_ms, trace`) and still needs Thathsarani's sign-off. The harness calls Agent 3 as `generate(question, ddl, hint=None, dialect=...)` and Agent 4 as `execute(db, sql)`. The proposed checkpoint formats are in `reports/Base model selection for local Text2SQL.md`: HF safetensors, PEFT adapter folders, and GGUF/AWQ for quantized models.

---

## 4. The chatbot front end

The lecture's list of common PP1 failures includes "front end not covered, done only the back end" and "customer couldn't understand the system". A thin front end fixes both, and also demonstrates the four separate components.

**Built (19 Oct):** `harness/app.py` provides `POST /query` (Agent 1 → generate → execute with bounded retry, 3 attempts, every handoff logged to `data/handoff.log.jsonl`) and three pages:
- `/chat`: the chatbot. Each answer shows a four-stage pipeline strip (question gate → retrieval → generation → execution), each badged **real** or **stand-in**, and a trace with every agent's input and output, including the retry hint passed back.
- `/` Retrieval Explorer, and `/dashboard` (saved answers as live charts, with a CSV link for Power BI or Excel).
- Adding a database on the chat page: drop a SQLite file or paste a PostgreSQL link (read-only).

Agents 3 and 4 plug in through `create_app(generate=..., execute=...)`; their badges then switch from stand-in to real automatically. Agent 2's gate becomes real once its classifier is exported.

**Screen layout:**
- Chat area: question box, database selector, the generated SQL, the result table, and a plain-language error message when something fails.
- **Pipeline trace panel** (collapsible, one section per agent, each built by that agent's owner):
  - Agent 1: tables and columns kept, tokens before vs after pruning, retrieval mode.
  - Agent 3: complexity label, head chosen, candidate SQL.
  - Agent 4: execution status, retry count, error hint if any, time taken.
  - Agent 2: model-info panel (base model, version, distilled vs native).
- Footer: end-to-end time and a "no data left this machine" indicator backed by a real check (see Section 8).

**Ownership:** one person builds the chat shell; each member builds only their own trace section. The team needs to decide who owns the shell.

---

## 5. Testing and feedback

Use the lecture's hierarchy: unit → component → integration → system → user.

| Level | Question | Example for this project | Owner |
|---|---|---|---|
| Unit | Does this function work? | FK-graph builder, column scorer, head router, SELECT-only guard | Each member |
| Component | Does my whole module work? | Agent 1 returns a valid PrunedSchema for all four modes | Each member |
| Integration | Do two components work together? | Agent 1 output accepted by Agent 3; Agent 4 hint accepted by Agent 3 | Pairs |
| System | Does the main workflow work? | Question in the chatbot → correct result, end to end | Team |
| User | Can a real user finish a task? | Analyst completes three tasks without help | Team |

**Feedback (the lecture's "strong feedback" definition):** real users perform tasks, you observe where they struggle, record comments and evidence, and convert them into Planner tasks. Compliments and friends do not count.

Sessions: supervisor and co-supervisor (the lecture asks for a presentation to them before PP1), plus at least two people who work with databases or reports. Give each person the same three tasks, such as "find which customers spent more than 40 in total". Note hesitations and errors, and ask "what did you expect to happen?" rather than "do you like it?".

Feedback log columns: date, user and role, task, success, where they struggled, comment, change made, Planner task link. **[EVIDENCE NEEDED]** Do not write feedback you have not collected.

---

## 6. Wrong-input matrix (demo at least two live)

| Input | Expected behaviour | Handled by |
|---|---|---|
| Empty or whitespace question | Message asking for a question; nothing sent to agents | Front end + orchestrator |
| Gibberish | "I couldn't match this to the database"; no crash | Agent 1 (low-confidence anchor) |
| Question unrelated to the database | Says the data doesn't contain that | Agent 1 / Agent 3 |
| Unknown database key | 404 with valid choices (**implemented**) | Orchestrator |
| Refers to a table or column that doesn't exist | Error-diagnosis hint, bounded retry, then a clear failure message | Agent 4 → Agent 3 |
| Destructive request ("delete all customers") | Refused; read-only connection (**implemented** in harness) and SELECT-only check | Agent 4 guard |
| Very long input | Truncated or rejected with a message | Front end / orchestrator |
| Schema has missing foreign keys | Retrieval continues with declared relationships | Agent 1 |
| Missing or wrong model artefact | Startup check fails with a readable message | Agent 3 |

Record each as a test case with input, expected result, actual result and pass/fail. If a row is not implemented yet, implement it before demonstrating it.

---

## 7. Beyond the sample data

1. **More than one database:** Agent 1 is already evaluated on Chinook, TPC-H and 20 Spider dev databases (148 questions). Add the Enterprise-style database from the repository plan.
2. **A held-out question set** that nobody tuned against, kept separate from development questions and reported separately. Teacher and fine-tuning prompts must never come from the Spider dev databases used in evaluation.
3. **Awkward schemas:** one with missing foreign keys, and one larger than Chinook.
4. **A live question** typed by a panel member. Rehearse the safe path (Section 9.2) in case it fails.

Done for Agent 1 with stand-in SQL models: Northwind (never tuned on) and PostgreSQL copies, plus per-bucket execution accuracy on Chinook + Spider (file 01). **[EVIDENCE NEEDED]** End-to-end accuracy per complexity bucket with Agent 3's fine-tuned model.

---

## 8. Non-functional requirements — evidence, not claims

| NFR | What to measure or demonstrate | Evidence |
|---|---|---|
| Performance | Agent 1 (warm, n=148): **median 278 ms**, p95 380, max 617; 1/148 over the 500 ms target. End-to-end latency (median and slowest over N runs) | Timing table |
| Resource use | Memory per quantization configuration on the mid-range target hardware. Preliminary (Agent 4, Phi-3): INT8 86% and INT4 53% of FP16 peak memory | Table (file 03) + `nvidia-smi` screenshot |
| Security: data stays local | Run a query with the network disabled, or show outbound-connection logs are empty | Screenshot/recording |
| Security: safe execution | Read-only DB connection (done), SELECT-only validator, rejects multiple statements; destructive inputs refused | Test cases from Section 6 |
| Security: input boundary | DB chosen by configured key, never a raw path (done) | Test case |
| Security: access control | Simple API key on the UI/API; request logging (handoff log exists) | Screenshot |
| Reliability | Same question run repeatedly succeeds; retry loop always terminates (MAX_ATTEMPTS=3) | N-run result |
| Usability | Task success from user sessions | Feedback log |
| Maintainability | Modular repo, contracts, README, tests passing | Repo screenshot, test run |
| Scalability | Retrieval time vs number of tables (Chinook → larger schema) | Small chart |

Present the two or three strongest; say plainly which are not yet measured.

---

## 9. Demo and backup plan

### 9.1 Demo as a story (lecture: user problem → input → processing → output → evidence)

1. **Problem (20 s):** a branch analyst needs an answer that no dashboard shows, and filing a report request takes days.
2. **Input:** the analyst types the question in the chatbot.
3. **Processing:** open the trace panel and walk the four agents in order, one sentence each, with each owner pointing at their own section.
4. **Output:** SQL and result rows.
5. **Failure moment, deliberately shown:** one wrong input and one self-healing retry.
6. **Evidence:** the comparison table, the NFR measurements, the feedback log.

### 9.2 Backup layers

| Risk | Backup |
|---|---|
| Live demo fails | A recorded screen video of the whole run (1–2 minutes) |
| Model won't load or GPU unavailable | A second machine prepared in advance, and a saved run of the same question |
| Database file corrupt | Copies of the database files |
| Slides or repo unavailable | Offline copy of slides and the repository |

Keep backups **in two other places**. Do a full dry run of the fallback, not only the main path.

### 9.3 Rehearsal (lecture's three rounds)

Content (can each member explain problem, function, method, evidence), timing (each individual part exactly 2 minutes, roughly 180–220 words), pressure (hard questions and a demo that fails mid-way).

---

## 10. PP1 slide map

| Slide | Content | Owner |
|---|---|---|
| 1 | Panel comments and how each was addressed (Section 1, rows P1–P4) | Team |
| 2 | Problem, impact, who benefits, overall design, 1–2 min video | Team |
| Individual ×4 | Opening slide (title, specialisation, name, IT number, project ID, photo) + two content slides (sub-problem addressed, requirements addressed, design/contribution, user feedback) | Each member, 2 min |
| Last | Commercialisation and sustainability, with the **overall** project title at the top | Team |

**Commercialisation slide inputs**
- **Customer persona:** regional banks, mid-size insurers, credit unions, growth-stage FinTech firms; users are analysts and BI managers, DBAs and compliance officers.
- **Market size:** a specific segment with justifiable numbers, "not everyone". **[EVIDENCE NEEDED]** No market-size figure has been verified yet. Source a defensible number (for example, the count of licensed banks and finance companies in Sri Lanka) and cite it.
- **What is unique:** the four component claims in Section 2.2, plus an on-premise conversational query system usable under generative-AI governance limits.
- **Cost recovery:** licensed on-premise appliance, with an optional privately hosted subscription tier for smaller customers. Development budgets from the individual proposals total LKR 138,000 (Ekanayake 19,000; Thathsarani 28,000; Karunanayake 30,000; Wathsala 61,000).

---

## 11. Order of work before PP1

1. **Today:** agree the demo database, the demo scenario, the front-end owner and the held-out question set; create `shared/schemas/`.
2. **By about 18 Oct:** chatbot over `/query` (stub agents allowed); each owner's trace section; wrong-input checks.
3. **By about 19 Oct:** NFR measurements; first feedback session; record the fallback video; back up to two places.
4. **Before PP1:** present to supervisor and co-supervisor; three rehearsal rounds; fix whatever the supervisors flag.

Final checklist (from the lecture): proposal feedback addressed, problem and impact clear, 1–2 minute video ready, two key functions per student, user feedback collected, integration demonstrated, testing evidence ready, commercialisation realistic, timing rehearsed, all members ready for Q&A.
