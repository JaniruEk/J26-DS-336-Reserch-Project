# Distributed Multi-Agent SLM Framework for Privacy-Preserving Enterprise Data Intelligence (J26-DS-336)

This is a complete, standalone scope document — what the project is and how it works, top to bottom. It is not the formal proposal and does not follow that template; it exists so anyone (team member, supervisor, new reader) can understand the whole project without needing the proposal's academic structure.

**Restructuring note (2026-09, second revision):** the team briefly consolidated fine-tuning-architecture selection (standard LoRA vs. HydraLoRA) and quantization strategy (QAT vs. PTQ) under one owner, and explored replacing the resulting vacant research slot with an independent OLAP/MDX query-translation pillar. On further review, both changes were reconsidered: the consolidated component overloaded one person's scope, and the OLAP/MDX pillar added a fifth, only loosely-integrated line of work without a correspondingly strong payoff. The team reverted to the project's original four-component shape — Ekanayake (retrieval), Wathsala (foundation model), Thathsarani (fine-tuning-architecture selection), Karunanayake (quantization strategy selection) — now wired as one sequential, fully deployed pipeline with no independent track. The one change kept from the consolidation experiment is a smaller cross-check: Karunanayake's quantization comparison is also run against Thathsarani's runner-up fine-tuning architecture, preserving the "do these two decisions interact" question without requiring single-owner control over both variables. This document reflects that reversion; sections below describe the current, four-agent sequential structure rather than any intermediate version.

**Agent 4 scope change (19 Oct 2026, final):** Karunanayake's component is now adaptive mixed-precision quantization (per-layer INT4/INT8 chosen by SQL-task sensitivity) instead of QAT vs. PTQ. The restructuring note above is kept as history.

**Update note (19 Oct 2026):** this revision brings the scope in line with what has been built and learned since: claims corrected against the research reports in `reports/`, the closest existing system (MATS) named, dashboards described as something the system works *with*, server databases (PostgreSQL), security and deployment (B.5), Agent 1's additions, base-model and quantization decisions, and known limitations (D.4). Measured results live in `Execution_Plan_J26-DS-336.md` and `CLAUDE.md`, not here.

---

# PART A — Overview & Context

## A.1 The Problem

A regional bank manager wants to ask: **"Show me total loan revenue by branch, for customers who have been with us over five years."**

Today, two options exist to get that answer, and both fail:

- **A cloud AI tool** could answer it, but doing so means sending the bank's live schema and customer data into a third-party generative-AI system — a category most banks' internal AI-governance and vendor-risk policy treats far more cautiously than an established vendor relationship (a payment processor, a core-banking software vendor) that has already been through years of audited approval. The restriction isn't that third-party data sharing is illegal — banks route data through third parties constantly, under contract. It's that a generative-AI vendor is a newer, less-precedented category — open questions about prompt logging, retention, cross-region processing and auditability — that internal AI-governance and vendor-risk policy, reinforced by data-protection regulation (GDPR, CCPA), treats with caution for live, sensitive data. (Training on customer data is not the argument: the major vendors' terms now exclude it.) Policies vary: in a 2025 survey of US banks under $100B, 66% had an AI-use policy and 15% had restricted or banned AI tools pending evaluation; no regulator requires on-premise hosting, but regulators hold the institution accountable for what its vendors do.
- **A small, locally-run AI model** avoids that exposure entirely, but small models are unreliable at exactly this kind of question — multi-table joins and aggregations (SUM, AVERAGE, GROUP BY) are where they hallucinate most.

**A note on "can't leave the bank":** to be precise, banks already share data with third parties every day — payment processors, core banking vendors, cloud hosting, KYC/verification providers — all under contract and audited controls built up over years. What's actually restricted is narrower: sending live schema and customer data into a *generative-AI* vendor specifically, a newer category that hasn't been through that same audited vendor-risk process, and one most banks' internal AI-governance policy explicitly treats with more caution regardless of what the underlying law technically permits under the right contract.

**The project's core question:** can a small, fully local AI system be made good enough at this kind of question to be genuinely usable — private *and* accurate, not one or the other?

There is no single fix. Several separate technical problems all have to be solved at once, which is why the work is split into independent, evaluated research questions rather than one team building one system end to end.

## A.2 Who This Is For

**Target verticals:** Corporate Business Intelligence, FinTech, and Data Warehousing — organisations legally bound by data-protection regimes (GDPR, CCPA, sector-specific banking/finance regulation).

**The specific customer profile:** regional banks, mid-size insurers, credit unions, and growth-stage FinTech firms — organisations that need natural-language data access but do **not** already operate large-scale GPU infrastructure or a dedicated ML engineering team. This is a deliberate scope choice: a small number of very large institutions could plausibly self-host a large LLM privately and sidestep this problem entirely; this project is not built for them. It targets the much larger population of organisations for whom that capital and operational cost isn't realistic.

**Who inside the organisation uses it:** enterprise data analysts and BI managers (day-to-day users), database administrators (need assurance generated queries respect schema/access boundaries), compliance and data-protection officers (need assurance no data ever leaves the organisation's infrastructure).

**How it's delivered:** as a licensed, on-premise software appliance — installed and run entirely within the organisation's own private infrastructure, not a service the team hosts on the customer's behalf. A bank deploys this the same way it already runs core banking systems: one centralised instance inside its own private data center, accessed by branches over the bank's own private internal network — never touching the public internet or a third party. An internal API in front of the system is a normal access pattern and doesn't conflict with the privacy story; the privacy concern is specifically about where the model is *hosted*, not about using an API as an interface.

**Why not just use a large LLM if an organisation can afford it?** For an organisation already running large-scale GPU infrastructure and an ML team, self-hosting a large model is a legitimate alternative — that's conceded honestly. But even for organisations that could afford it, a large model carries a recurring per-query compute cost that scales with usage, plus a latency/single-point-of-failure dependency on one centralised cluster reachable only over the network. Small, efficient models avoid both costs regardless of an organisation's budget, which is why the target market and the value proposition hold even where the "just use a big model" objection is raised.

**Why not just use the bank's existing BI dashboards?** Dashboards answer known, recurring questions that a BI team anticipated and built in advance — quarterly revenue by branch, monthly claims by region. The moment someone asks something that wasn't pre-built — a new filter, a one-off combination of fields — the dashboard can't answer it, and the person either can't get the answer or has to file a request with IT/BI and wait for an analyst (how long is not well measured; the only figure found is an old vendor survey). That gap (ad hoc, unanticipated questions) is real and is exactly what commercial conversational-BI tools like Snowflake Cortex Analyst, Databricks Genie, Power BI Copilot and ThoughtSpot already sell — so the demand for natural-language ad hoc querying beyond dashboards isn't speculative. Almost all of those tools run their language model in the vendor's or a large cloud provider's cloud. A few local options now exist (Oracle Select AI with a privately hosted model on Oracle's own database; Metabase Metabot with a self-hosted model since October 2026), so this project does not claim to be the only local option; its gap is a small, fully local, database-agnostic system that runs on mid-range hardware without a licence tie to a particular warehouse or BI platform.

**The system complements dashboards rather than replacing them.** Routine, high-stakes reports (regulatory, financial statements) stay on fixed, tested SQL. The system answers the ad hoc questions, always shows its SQL, and an analyst can **promote** a checked answer into a dashboard: the answer's SQL is frozen and the dashboard replays it, so the language model is never involved when a dashboard refreshes ("explore, then promote"; works with on-premise BI such as Power BI Report Server, Tableau Server, Apache Superset or Metabase).

**A precondition, stated honestly:** the system needs one queryable database. Many smaller institutions keep data in source systems and spreadsheets (in the same 2025 survey only about 39% of banks used a data warehouse or lake), so adoption may first need a warehouse or a reporting copy. Natural-language querying also lowers the SQL barrier but does not fix data literacy.

## A.3 The Research Aspect — Not Just a Product Build

This is a final-year research dissertation, and the actual deliverable is evidence, not software. Each component exists to answer a genuine open question nobody has already answered — not "build a feature," but "does X actually outperform Y, under this constraint, by how much." Each comparison is a **controlled experiment**: same data, same hardware budget, same evaluation metrics, one variable changed at a time.

Following Design Science methodology, each component produces two things: an **evaluated artefact** (the working engine/module/model) and **empirical findings** (the measured comparison results). The findings are the primary contribution; the software is what makes obtaining the findings possible, not the end goal itself. **A negative result is still a valid result** — if a technique doesn't help, that's a legitimate, reportable finding, not a failed deliverable.

The business framing (A.1–A.2) is what makes the research *relevant*; the rigor of the independent studies is what actually gets defended and evaluated.

**What is and isn't new.** A multi-agent, small-model Text-to-SQL pipeline is not new in itself: the closest existing system, MATS (arXiv 2512.18622), already uses five small agents (about 9B parameters in total, on a 24GB GPU) for schema filtering, planning, validation and repair. This project does not claim the pipeline shape as its contribution. It claims (1) the four controlled comparisons — column-level pruning, distillation, complexity-routed HydraLoRA for SQL (the strongest novelty claim), and SQL-task-sensitive mixed-precision (INT4/INT8 per layer) quantization — and (2) efficiency: one shared small base model with adapters and quantization on mid-range hardware. Schema retrieval is a crowded area (GRASP, RASL, RSL-SQL), so Agent 1's contribution is the measured ablation, not a new retrieval algorithm.

---

# PART B — System Architecture

## B.1 The Components, At a Glance

The system has four components, wired into one deployed, per-query pipeline — no independent or unwired track.

| Component | Owner | Role |
|---|---|---|
| **Agent 1 — Retrieval** | Ekanayake | Decides which parts of the database schema the model actually needs to see |
| **Agent 2 — Foundation Model** | Wathsala | Builds the underlying small AI model everything else runs on top of |
| **Agent 3 — Fine-Tuned Generation** | Thathsarani | Selects the winning fine-tuning architecture (standard LoRA vs. HydraLoRA) and performs live, per-query SQL generation |
| **Agent 4 — Quantized Execution** | Karunanayake | Builds an adaptive mixed-precision model (INT8 for the layers most sensitive for SQL, INT4 for the rest) and executes the generated SQL with self-healing retry |

Each agent has a defined input, a defined output, and no dependency on another agent's internal implementation — only on the handoff contract between them. The one deliberate exception to strict independence is the cross-check: Agent 4 consumes not only Agent 3's winning architecture but also its runner-up, specifically to test whether Agent 4's own findings are stable across fine-tuning architectures.

## B.2 How the System Actually Runs — Execution Model

**The four-agent chain runs fresh, once per query — it is not a continuously running background process.** Ask one question, the full chain executes once, top to bottom, and returns an answer. Ask a second question, it runs again from the start; nothing is remembered between queries.

| | Built / trained | Runs |
|---|---|---|
| Agent 1 (retrieval logic) | Once, offline, during development | Fresh, every single query |
| Agent 2 (foundation model) | Once, offline (distillation + training) | Reused as-is, every query |
| Agent 3 (fine-tuning architecture selection) | Once, offline (LoRA vs. HydraLoRA comparison) | Live Head-Selection and Generation sub-agents run fresh, every query |
| Agent 4 (quantization strategy selection) | Once, offline (layer sensitivity, precision allocation, comparison with uniform INT4/INT8) | Live Execution and Error-Diagnosis sub-agents run fresh, every query |

**Within a single query**, if Agent 4's execution sub-agent fails, the system doesn't give up — its Error-Diagnosis sub-agent constructs an error-informed hint and loops back to Agent 3's own generation sub-agent, retrying up to a bounded number of attempts, before surfacing a failure to the user. The retry loop spans Agents 3 and 4 by design: Agent 3 owns generation, Agent 4 owns execution and diagnosis.

## B.3 Shared Foundations

- **Hardware constraint:** every component is designed and evaluated against mid-range consumer hardware — the single root cause behind the project's research questions. It rules out simply using a bigger model to sidestep any of them.
- **Query-complexity taxonomy:** every test query is classified as simple / single-join / multi-join / aggregation, based on its ground-truth SQL structure. Built by Ekanayake, used across every other component — Agent 3 for HydraLoRA head routing and complexity-stratified evaluation, Agent 4 for complexity-stratified quantization evaluation.
- **Database proxies:** Chinook (primary, everyday testing), Spider (schema diversity across many domains), TPC-H (deep, join/aggregation-heavy enterprise schema), Northwind (an unseen business database, about 625,000 rows, used to check that nothing is tuned to the other three), and a value-coded question set (questions whose stored values are codes such as `'1'` for "discontinued").
- **Any connected database:** every component reaches data through one read-only database layer that accepts SQLite files and PostgreSQL servers (the dialects whose read-only mode, one-statement rule and timeout are enforced). A fix that only works on the test datasets is not a fix: each change is checked on SQLite, PostgreSQL and the unseen database.
- **Shared base model (agreed 19 Oct 2026):** Qwen2.5-1.5B-Instruct (general instruct model, Apache 2.0) is the native baseline and distillation student, fine-tuned by Agent 3 and quantized by Agent 4. The teacher should share its tokenizer (Qwen2.5-7B-Instruct, to be confirmed). Results measured on earlier stand-ins (phi3, Phi-3 Mini, Qwen2.5-Coder-1.5B) are preliminary and are re-run on this model.

## B.4 Orchestration and Observability Harness

The four agents are coordinated by a **lightweight orchestration and observability harness**, deliberately not a general-purpose agentic framework (e.g. LangGraph). The pipeline's control flow is deterministic — a fixed sequence of agent calls with one bounded retry branch — not a system where agents autonomously choose their next action, so a full agentic framework was judged to add complexity disproportionate to what the system actually does.

The harness is a FastAPI-based routing layer with three jobs:
1. **Sequencing** — calling each agent in order and passing its output to the next, exactly per the interface contracts (Part D.1).
2. **Structured logging** — every agent-to-agent handoff (inputs, outputs, timing) is logged, so the pipeline's behaviour is inspectable, not opaque.
3. **Retry control** — the bounded retry branch, spanning Agent 4's error-diagnosis sub-agent and Agent 3's generation sub-agent, is implemented as an explicit conditional, with every attempt logged individually.

Beyond those three jobs, the harness also: refuses anything other than a read-only `SELECT` (a refused query is not retried); declines off-topic questions before any model call; serves a chat page (answer, SQL and a per-agent trace) and a Retrieval Explorer for Agent 1; and offers the BI "promote" step (save a checked answer, replay its frozen SQL as a CSV link or a Superset chart).

This harness is shared infrastructure, built collaboratively, and is not attributed as any individual member's research novelty.

## B.5 Security and Deployment

**Deployment shape.** One instance in the institution's own data centre, reached by branches over its private network; the model, the questions and the data never leave that network. During development the model runs under Ollama; for deployment the plan is to run it inside the application with `llama-cpp-python`, loading Agent 4's quantized model and Agent 3's adapters directly (`reports/Deployment_runtime_plan.md`).

**Guarantees in place.** Read-only database connections; exactly one statement per query (a multi-statement string could otherwise end the read-only transaction — found and fixed in testing); a query timeout; passwords never shown in errors; databases chosen by configured name, never by path; a personal-data setting under which Agent 1 never reads data values; saved dashboard answers come only from the pipeline, never from client-supplied SQL; every handoff logged for audit.

**Required at deployment.** A database login with SELECT-only permission (the backstop in every case).

**Still open.** Login on the application (ideally the institution's single sign-on); per-role visibility of tables and columns (a branch clerk must not see other branches' customers), enforced before Agent 1 reads the schema and by a per-role read-only login; a retention or masking policy for logged questions; HTTPS and rate limiting on the internal network. These are deployment requirements, not research contributions.

---

# PART C — Each Component In Full Detail

## C.1 Agent 1 — Ekanayake: Dynamic Schema Retrieval & Column-Level Pruning

**What it does:** Decides which tables and columns from the database schema are relevant to a given query, so the downstream model isn't handed the entire schema every time.

**Why it's necessary:** Small AI models have a limited context window. Handing over 50 tables' worth of columns when only 3–4 matter wastes that budget and increases the chance of the model making mistakes.

**How it's achieved — internal sub-agent structure:**
This agent decomposes into three cooperating sub-agents, each making one bounded decision:
1. **Anchor-Selection Sub-Agent** — finds the starting table, either via ChromaDB semantic embedding search or (in structural-only mode) simple keyword/name matching — no embeddings in that path.
2. **Traversal Sub-Agent** — follows foreign-key relationships outward from the anchor table, via `PRAGMA foreign_key_list`-based graph reflection, when the active mode calls for it.
3. **Pruning Sub-Agent** — for every non-key column, checks lemma overlap between the column name and the query first; if there's no overlap, falls back to spaCy word-vector cosine similarity against a tuned threshold.

**Four switchable configurations, compared against each other:**

| Mode | Anchor finding | Pulls related tables? | Filters columns? |
|---|---|---|---|
| Semantic-only | AI similarity | No | No |
| Structural-only | Keyword/name match | No | No |
| Hybrid | AI similarity | Yes (FK traversal) | No — full tables |
| Hybrid + pruning | AI similarity | Yes (FK traversal) | **Yes — the novel contribution** |

**The research question:** does column-level pruning, layered on structural+semantic table retrieval, improve context efficiency and downstream SQL accuracy under a fixed token budget — and does the effect vary by query complexity?

**Additions since the proposal (all switchable, so the original four-mode comparison still runs as designed):**
- **Multi-anchor retrieval** — the top three semantically matching tables, connected along the shortest foreign-key paths (bridge tables included), because most missed multi-join columns came from whole tables never reached.
- **Richer word matching in pruning** — splitting run-together and abbreviated names (`acctbal`, lower-case `firstname`), a small business-synonym list ("spent" → `Total`), and matching data values the question names ("Canada" → `Country`), read-only.
- **Value hints and glossary** — columns that hold short codes are shown with their values (`Discontinued TEXT /* values: '0', '1' */`), and an institution's data dictionary can add meanings ("C = closed"). Columns whose values differ on every row (names, emails, account numbers) are never shown, and the whole feature is off for databases marked as holding personal data.
- **Off-topic decline and explanation** — a question that matches no table or column is declined before generation; every kept or removed column carries the reason, shown in the trace.

**Inputs:** the user's query; a live database connection (SQLite or PostgreSQL); optionally the institution's glossary.
**Outputs:** pruned schema context → Agent 3, as a JSON handoff (`query, complexity, mode, anchor, matched, tables, ddl, tokens, latency_ms, trace`). Also produces the shared complexity classifier, used by Agents 3 and 4.

**Dependency status:** none — starts immediately, day one, in parallel with Agent 2.

---

## C.2 Agent 2 — Wathsala: Foundation Model via Knowledge Distillation

**What it does:** Builds the small AI model that everything else is built on top of, using knowledge distillation — a larger "teacher" model's behaviour is compressed into a small "student" model — rather than simply picking an off-the-shelf small model.

**Why it's necessary:** Off-the-shelf small models are generic and were never optimised for multi-step reasoning. Fine-tuning later can sharpen a skill the model already has some trace of — it can't install reasoning ability that was never there. Distillation builds a stronger starting point *before* any SQL-specific training happens.

**How it's achieved:** Response-based distillation — the teacher (~7B parameters) runs inference only (never modified), generating ~1,500–3,000 prompt-response pairs across general reasoning and SQL-adjacent schema-comprehension prompts, an explicit proof-of-concept scope. The student is trained via standard supervised fine-tuning on those teacher-generated responses. Validation happens in two stages: (1) distilled vs. native comparison on general reasoning, *before* any SQL fine-tuning — isolates distillation's effect alone; (2) the same comparison *after* both models go through identical fine-tuning (coordinated with Agent 3) — confirms whether the advantage survives.

**Model choice and fairness:** the student is the team's base model, Qwen2.5-1.5B-Instruct (agreed 19 Oct 2026). A teacher from the same family keeps tokenizer, chat template and SQL style consistent (Qwen2.5-7B-Instruct, to be confirmed). A third arm — the native model fine-tuned on the same prompts with gold-SQL answers — separates a genuine distillation effect from simply more fine-tuning. Teacher prompts come only from training splits, never from evaluation databases; only teacher answers whose SQL executes are kept.

**No internal sub-agent decomposition:** unlike the other agents, this one makes no per-query runtime decision — its output (the trained model) is built once, offline, before any query is ever answered.

**The research question:** does a distilled small model retain stronger multi-join/aggregation reasoning than a natively small model of equal size, after identical fine-tuning?

**Inputs:** teacher model (inference only); a prompt pool.
**Outputs:** two base models (distilled, native) → Agent 3.

**Dependency status:** none — starts immediately, day one, in parallel with Agent 1. **This is the critical-path component** — Agent 3 cannot begin core fine-tuning until this delivers. It is also the most compute-intensive agent, since teacher-model inference exceeds the local hardware budget and needs rented compute.

---

## C.3 Agent 3 — Thathsarani: Complexity-Specialised Fine-Tuning Architecture Selection

**What it does:** Takes the foundation model (Agent 2) and specialises it for SQL generation, comparing standard LoRA against an asymmetric multi-head HydraLoRA architecture. Also owns the live, per-query generation step: given the pruned schema context, the routed complexity-specialised head, and whichever quantized weights Agent 4 has prepared, it produces the candidate SQL statement.

**Why it's necessary:** A simple question and a hard question require genuinely different reasoning, and training one model identically on both tends to make it "average" at both rather than actually good at the hard ones. This project's own problem statement identifies multi-join and aggregation reasoning as the specific failure mode of off-the-shelf small models.

**How it's achieved — two architectures compared:**
- **Standard LoRA** — one shared low-rank adapter (A, B matrices) fine-tuned on the full dataset. The control condition.
- **HydraLoRA** — a shared down-projection matrix (A) with multiple up-projection heads (B), one per complexity bucket. Routing is hard-coded via the shared classifier — a deliberate simplification of HydraLoRA's original unsupervised auto-clustering.

**Live sub-agents:** the **Head-Selection Sub-Agent** consumes the complexity label from Agent 1's shared classifier and routes to the correct head (or the single adapter, if standard LoRA won). The **Generation Sub-Agent** produces the SQL statement.

**The research question:** does complexity-specialised HydraLoRA improve multi-join/aggregation reasoning over standard LoRA without a proportional increase in trainable parameters?

**A first-class output beyond the winner:** this component reports both the winning and the runner-up architecture as versioned artefacts, specifically so Agent 4 can test whether its layer-sensitivity ranking is stable across fine-tuning architectures.

**Inputs:** pruned schema context (Agent 1); base model checkpoints, distilled and native (Agent 2); complexity-labelled training data.
**Outputs:** winning and runner-up fine-tuned architectures → Agent 4; live candidate SQL → Agent 4 for execution.

**Dependency status — and the parallel-work fix:** rather than sitting idle until Agent 2's real distilled model is ready, the full LoRA-vs-HydraLoRA comparison is run *immediately*, in parallel, on a plain off-the-shelf placeholder base model. Once Agent 2's actual winning base model is ready, the comparison is re-run against it as a shorter validation pass.

---

## C.4 Agent 4 — Karunanayake: Adaptive Mixed-Precision Quantization and Execution

*Scope changed 19 Oct 2026 (final): adaptive mixed-precision quantization replaces the earlier QAT vs. PTQ comparison.*

**What it does:** Compresses the fine-tuned model for deployment by giving each transformer layer its own precision. Layers that matter most for SQL generation stay at INT8; the rest go to INT4. Also owns the live execution step: running the generated SQL against the local database and, on failure, diagnosing the error and routing a retry back to Agent 3.

**Why it's necessary:** Even a small fine-tuned model is often too large and slow to run responsively on mid-range hardware at full precision. Uniform INT4 saves the most memory but can damage exactly the reasoning the project cares about (joins, SUM/AVG/COUNT); uniform INT8 is safer but keeps memory high. Layers are not equally important, so one bit-width for all of them is likely to waste memory in some places and lose accuracy in others.

**How it's achieved:**
1. **Layer sensitivity.** Each of the model's transformer layers (28 in Qwen2.5-1.5B-Instruct, the team's base model) is quantized to INT4 on its own while the rest stay at full precision, and the damage to SQL generation is measured on a calibration set of training questions (never the test sets), per complexity bucket. Ranking uses a continuous score (how much less likely the gold SQL becomes, or how far the output distribution moves from full precision), confirmed with execution accuracy.
2. **Precision allocation.** The most sensitive layers are assigned INT8 and the rest INT4. The number of INT8 layers is swept, giving a memory-vs-accuracy curve rather than a single model.
3. **Comparison.** Against full precision (ceiling), uniform INT8, uniform INT4, llama.cpp's built-in mixed format (`Q4_K_M`), and two controls with the same number of INT8 layers: randomly chosen layers, and layers chosen by a generic (perplexity-based) sensitivity score. Accuracy is reported by complexity bucket, separating syntax errors from wrong results, with peak GPU memory, model size and speed measured in the runtime that ships (llama.cpp).

**What is and isn't new:** per-layer mixed precision is established (HAWQ, OWQ, SpQR, SliM-LLM, and llama.cpp's own mixed formats). The contribution is measuring sensitivity on the *task* (SQL generation, by query complexity) and testing whether that picks different layers, and gives better accuracy per unit of memory, than generic sensitivity or a fixed heuristic.

**Cross-check (proposed, to confirm):** the sensitivity ranking is measured again on Agent 3's *runner-up* fine-tuning architecture, to test whether the layers that matter depend on how the model was fine-tuned.

**Live sub-agents:** the **Execution Sub-Agent** runs the generated SQL against the local database using the deployed quantized model. On failure, the **Error-Diagnosis Sub-Agent** constructs an error-informed hint and routes control back to Agent 3's Generation Sub-Agent for a bounded number of retries. It should also treat a filtered query that returns **no rows** as suspicious: look up the filtered column's real values and retry once with a hint (a query using `'yes'` for a column that stores `'1'` runs without error but answers nothing). The Execution Sub-Agent must keep the guarantees in B.5 by using the shared read-only database layer rather than its own connection.

**The research question:** does a layer-wise INT4/INT8 model, allocated by SQL-task sensitivity, preserve SQL accuracy (especially on multi-join and aggregation questions) better than uniform INT4, and close to uniform INT8, while using less GPU memory and running at least as fast?

**Inputs:** the winning (and runner-up) fine-tuned models (Agent 3); during development, the released Qwen2.5-1.5B-Instruct.
**Outputs:** the deployment-ready mixed-precision model (one GGUF file with per-layer precision); executed SQL + results, returned to the user.

**Dependency status — and the parallel-work fix:** the whole method (sensitivity, allocation, deployable build) is developed now on the released Qwen2.5-1.5B-Instruct, so nobody waits on a teammate (earlier Phi-3 Mini results are kept as preliminary). Because sensitivity depends on the exact weights, it is measured again on Agent 3's real model, in the configuration that will be deployed (quantized base with adapters attached, `reports/Deployment_runtime_plan.md`).

---

# PART D — Coordination & Practical Execution

## D.1 Component Interfaces — Full Reference

```
Ekanayake (Agent 1) ──┐
                      ├──→ Thathsarani (Agent 3: Fine-Tuning Architecture Selection) ──→ Karunanayake (Agent 4: Quantization + Execution)
Wathsala (Agent 2) ───┘
```

| From | To | What's handed off |
|---|---|---|
| Agent 1 | Agent 3 | Pruned schema context as a JSON handoff (DDL text inside, plus complexity label, explanation trace); the shared complexity classifier (live, per query) |
| Agent 2 | Agent 3 | Two base model checkpoints (distilled, native) |
| Agent 3 | Agent 4 | Winning and runner-up fine-tuned architectures (offline artefacts); candidate SQL (live, per query) |
| Agent 4 | — | Deployment-ready quantized model; executed SQL + results, returned to the user |

**Handoff formats — status:**
- Agent 1 → Agent 3: **built** as a JSON dictionary with the DDL text inside; awaiting Thathsarani's confirmation. The generator is called as `generate(question, ddl, hint=None)`, with `dialect="PostgreSQL"` added for server databases.
- Agent 2 → Agent 3: **proposed** — a Hugging Face folder (safetensors, tokenizer, chat template) per checkpoint, versioned, same tokenizer for distilled and native.
- Agent 3 → Agent 4: **proposed** — PEFT adapter folders for LoRA; HydraLoRA weights plus a small config mapping heads to complexity buckets, and merged per-head folders so standard converters can quantize them.

Training prompts must use the same schema format as the live system (pruned DDL with value comments), otherwise the fine-tuned model may ignore information it was never trained to read.

## D.2 Parallel-Work Strategy — Avoiding Idle Dependency

The dependency chain (Agent 3 waits for Agent 2; Agent 4 waits for Agent 3) risks reading as a scheduling weakness if left as pure sequential waiting. The fix, applied consistently:

1. **Run the core comparison immediately, on a placeholder input.** Agent 3 runs LoRA-vs-HydraLoRA on a plain off-the-shelf base model; Agent 4 builds its quantization tooling in parallel and runs an early pass on a self-fine-tuned placeholder model.
2. **Re-validate once the real upstream artefact exists.** Once Agent 2's real base model is delivered, Agent 3 re-runs its comparison against it; once Agent 3 delivers its real winning (and runner-up) architecture, Agent 4 re-runs its comparison and cross-check against the real artefacts.

This means nobody sits idle waiting for a teammate — the cost is running each core comparison twice, a real but worthwhile tradeoff against the schedule risk it removes.

## D.3 Build Order Summary

| Order | Component | Waiting on |
|---|---|---|
| 1 (parallel) | Agent 2 (Wathsala) | Nobody — start immediately, treat as priority (critical path) |
| 1 (parallel) | Agent 1 (Ekanayake) | Nobody — start immediately |
| 2 | Agent 3 (Thathsarani) | Agent 2's models + Agent 1's classifier (initial comparison runs in parallel on placeholder) |
| 3 | Agent 4 (Karunanayake) | Agent 3's winning (and runner-up) fine-tuned models (initial comparison runs in parallel on placeholder) |

## D.4 Known Limitations Found So Far

- **Coded values.** The model sees column names and types, not what values mean; "discontinued" stored as `'1'` produced an empty answer. Mitigated in layers: value hints and glossary (Agent 1), training on that format (Agent 3), distillation prompts (Agent 2), empty-result retry (Agent 4), and showing the SQL to the user.
- **Abbreviated or run-together names.** Real schemas often use names like `c_acctbal` or lower-case `firstname`; word matching splits common cases but can mis-split some words.
- **Distractor tables.** Pulling in extra tables to reach multi-join answers can bring in a table with same-named columns (Northwind: suppliers vs shippers), and the model may choose the wrong one — producing a plausible-looking but wrong answer. This is why the SQL is always shown.
- **Multi-join questions** remain the weakest category for small models, before and after fine-tuning so far.
- **Stand-in models.** Current measurements use untrained stand-ins (phi3, Qwen2.5-Coder-1.5B); conclusions wait for the fine-tuned and quantized Qwen2.5-1.5B-Instruct.

---

# PART E — Summary

Four people are each independently proving that a different design choice — how you retrieve schema context, how you build the base model, which fine-tuning architecture handles heterogeneous query complexity, and how to spend precision layer by layer so that compression preserves that architecture's reasoning under deployment constraints — matters for making small, fully local AI models good enough at complex enterprise questions to actually be usable. The two fine-tuning-and-compression questions connect through a single, deliberately lightweight cross-check — testing whether the same layers stay sensitive in a different fine-tuning architecture — without requiring either component to depend on the other's internal implementation. Each study is tested as its own controlled, standalone experiment; the four winning configurations are then assembled into one working system, which demonstrates feasibility, not an additional novelty claim. The system is scoped for organisations that need this privacy guarantee and can't or won't build large-model infrastructure themselves — which is most of the target market, not an edge case.
