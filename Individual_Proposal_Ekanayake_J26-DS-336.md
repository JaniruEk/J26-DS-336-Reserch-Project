Sri Lanka Institute of Information
Technology
J26-DS-336
Distributed Multi-Agent SLM Framework for
Privacy-Preserving Enterprise Data Intelligence
Adaptive Schema Context Width for Small Local Text-to-SQL Models
Individual Project Proposal Report
J.K.B. Ekanayake – IT23199262
B.Sc. (Hons) Degree in Information Technology
Specialized in Data Science
Department of Information Technology
Sri Lanka Institute of Information Technology, Sri Lanka
September 2026

> **Revision note**
> Revised 23 November 2026: research claim changed from column-level pruning to adaptive schema context width (approved 21 November 2026). Results: reports/agent1_width/README.md.

# DECLARATION

I declare that this is my own work, and this proposal does not knowingly incorporate any material previously submitted for a degree or diploma at any other university or higher education institution, nor does it contain any material that has been previously published or written by another person apart from where proper acknowledgment is given in the text.

| Name | Student ID | Signature |
|---|---|---|
| J.K.B. Ekanayake | IT23199262 |  |

The above candidate is conducting research for their undergraduate dissertation under my supervision.

| Name | Date | Signature |
|---|---|---|
| Prof. Nathali Silva |  |  |
| Mr. Theshan Senanayake |  |  |


# ABSTRACT

Enterprises need natural-language access to internal databases, but sending schemas into cloud-hosted generative-AI systems is restricted at most regulated enterprises by internal AI-governance policy, reinforced by data-protection regulation, while local Small Language Models (SLMs) hallucinate on complex multi-table schemas. One contributor to this hallucination is the amount of schema in the prompt. Too little schema omits tables that the SQL needs. Too much schema distracts a small model and uses its limited context. The best amount of schema (the *width*) can differ for each question and for each model. This component asks: for a given small local SQL model, how much schema should each question get? It defines four nested widths over the foreign-key graph: the anchor table only (W1), the anchor and related tables with column pruning (W2), the same tables with all columns (W3), and the full schema (W4). A selector chooses one width for each question before SQL generation. It uses only features known before generation, and it learns from labels that come from the same model's own execution results: the label is the narrowest width whose SQL returns the correct rows. The study also measures execution accuracy against width by model size (Qwen2.5-Instruct 0.5B, 1.5B and 3B) and by query complexity (simple, single-join, multi-join, aggregation); these are the "distraction curves". Per-question schema selection, routers learned from model outcomes, and accuracy-against-schema-budget studies already exist separately; the claimed contribution is only their combination for schema width on small local models, plus the distraction curves by model size and complexity. The research follows a Design Science methodology. The test set is the full non-nested Spider development set plus the Chinook and Northwind databases; the selector trains on 1,200 Spider training questions from other databases. The selector is compared with fixed widths, a complexity rule, a training-free elbow cut, a complexity-only selector, a retry with a wider width and an oracle, with paired bootstrap confidence intervals and exact McNemar tests. The retrieval engine (anchor selection, foreign-key traversal, column pruning) and its four retrieval modes remain: they build the widths and serve as the fixed-width baselines. Within the complete four-component system, this module supplies the schema context, its width and the complexity label to the fine-tuning and generation component.

# ACKNOWLEDGEMENT

I would like to thank my research supervisor, Prof. Nathali Silva, and co-supervisor, Mr. Theshan Senanayake, for their guidance and constructive feedback throughout the development of this proposal, particularly during the topic assessment review that shaped this component's research direction.

I am also grateful to the Sri Lanka Institute of Information Technology (SLIIT) and the Department of Information Technology for the academic resources and learning environment provided. I further acknowledge my project teammates — working on the other three components of this system — whose collaboration helped clarify how this individual component connects to the complete solution.

Finally, I thank my family and friends for their continued encouragement throughout this academic undertaking.

# TABLE OF CONTENT

# LIST OF TABLES

- Table 1. Evaluation Metrics for Ekanayake's Component
- Table 2. Budget Justification
- Table 3. Task Breakdown, Timeline, and Workload Distribution
- Table 4. Individual Responsibility Boundary

# LIST OF FIGURES

- Figure 1. Ekanayake's Component Structure
- Figure 2. Gantt Chart — 12-Month Timeline

# LIST OF ABBREVIATIONS

| Abbreviation | Meaning |
|---|---|
| AI | Artificial Intelligence |
| SLM | Small Language Model |
| LLM | Large Language Model |
| API | Application Programming Interface |
| RAG | Retrieval-Augmented Generation |
| LoRA | Low-Rank Adaptation |
| PEFT | Parameter-Efficient Fine-Tuning |
| QAT | Quantization-Aware Training |
| PTQ | Post-Training Quantization |
| SQL | Structured Query Language |
| FK | Foreign Key |
| DDL | Data Definition Language |
| FP16 | 16-bit floating point (model precision) |
| CI | Confidence Interval |
| GDPR | General Data Protection Regulation |
| CCPA | California Consumer Privacy Act |
| SDG | Sustainable Development Goal |
| CEAI | Computing, Engineering and AI (research cluster) |


# LIST OF APPENDICES

- Appendix 1 – Supporting Evidence and Diagrams
- Appendix 2 – Proposal Evidence and Decision Log
- Appendix 3 – AI Use Disclosure

# 1. INTRODUCTION

## 1.1 Background and Context

Large-scale enterprise data querying increasingly relies on natural-language interfaces, but sending sensitive schema and transaction data into cloud-hosted, third-party generative-AI systems is restricted at most regulated enterprises — not because third-party data sharing itself is prohibited (established vendor relationships operate under audited contracts routinely), but because a generative-AI vendor is a newer, less-precedented category that internal AI-governance and vendor-risk policy, reinforced by regulations such as GDPR and CCPA, treats far more cautiously than a long-established third-party relationship. Locally hosted Small Language Models avoid this exposure, but are known to hallucinate heavily when reasoning over complex, multi-table schemas — a limitation with direct financial and legal consequences for regulated enterprises in Corporate Business Intelligence, FinTech, and Data Warehousing verticals.

One contributor to this hallucination is the amount of schema in the prompt. A full multi-table schema has many tables and columns that a single question does not need. Small models are known to be distracted by irrelevant context, and on mid-range hardware a longer prompt also costs time and memory. But a narrow schema has the opposite risk: it can omit a table or column that the correct SQL needs. So the right amount of schema is a trade-off, and the best point on it can change with the question and with the model.

This component addresses the schema-context problem: given a natural-language question, a full enterprise schema and a given small local SQL model, how much of the schema should the system show to that model? The component builds four nested schema widths with a retrieval engine (semantic anchor selection, foreign-key graph traversal and column pruning). A selector then chooses one width for each question before generation, and it learns this choice from the execution results of the same small model. The study also measures how accuracy changes with width for different model sizes and query complexities. All work runs under the project's shared mid-range hardware constraint.

This work aligns with SDG 9 (Industry, Innovation and Infrastructure) by contributing to a resource-democratised AI infrastructure, and with the CEAI research cluster's focus on applied, resource-constrained AI systems.

## 1.2 Literature Review

The following peer-reviewed and benchmark sources were critically evaluated for their relevance to this component:

**[1] AID-SQL: Adaptive In-Context Learning of Text-to-SQL with Difficulty-Aware Instruction and Retrieval-Augmented Generation (2025)**

| Aspect | Detail |
|---|---|
| Method | Retrieval-augmented in-context learning with difficulty-aware example selection for Text-to-SQL generation. |
| Dataset / Context | Cross-domain Text-to-SQL benchmarks with varying query difficulty levels. |
| Key Findings | Adaptive retrieval strategies that account for query difficulty improve generation accuracy over static retrieval. |
| Strengths | Demonstrates that retrieval strategy should not be one-size-fits-all across query types. |
| Limitations | Adapts examples and instructions to difficulty; does not adapt the amount of schema shown to the model. |

Motivates this component's decision to stratify evaluation by query complexity rather than reporting a single aggregate accuracy figure.

**[2] To RAG or Not to RAG, That Is the Question: Effective Text-to-SQL Generation Under Ambiguity (2026)**

| Aspect | Detail |
|---|---|
| Method | Comparative analysis of RAG-based versus non-RAG Text-to-SQL pipelines under schema ambiguity. |
| Dataset / Context | Ambiguous-query subsets of standard Text-to-SQL benchmarks. |
| Key Findings | Retrieval augmentation helps disambiguate schema references, but excess retrieved context can itself introduce noise. |
| Strengths | Highlights that retrieval quantity, not just presence, affects generation accuracy. |
| Limitations | Does not measure how the best amount of context changes with model size or query complexity. |

Supports the premise of this component: more schema is not always better, so the amount of schema is a variable to choose for each question.

**[3] Efficient Inference Scheduling With Edge and Cloud Collaboration for LLMs Under Resource Constraints (2026)**

| Aspect | Detail |
|---|---|
| Method | Survey and benchmarking of inference scheduling strategies balancing edge and cloud resources for LLM deployment. |
| Dataset / Context | Simulated and real edge-hardware inference workloads. |
| Key Findings | Context length is a first-order determinant of inference latency and memory footprint on constrained hardware. |
| Strengths | Provides quantitative grounding for why context-window efficiency matters on constrained hardware. |
| Limitations | General-purpose inference scheduling; does not address domain-specific context construction (e.g. schema width). |

Provides the technical justification for treating token count as a primary evaluation metric in this component.

**[4] QCMA-SQL (Findings of NAACL 2025)**

| Aspect | Detail |
|---|---|
| Method | Multi-agent Text-to-SQL with a learned, per-question schema selector; a difficulty class (simple/complex) chooses the agent. |
| Dataset / Context | Standard Text-to-SQL benchmarks; API-scale LLMs. |
| Key Findings | A per-question schema selection can be learned. |
| Strengths | Closest prior design for a learned, per-question amount of schema. |
| Limitations | Selector labels come from gold-SQL schema relevance, not from the generator's own results; the difficulty class chooses the agent, not the amount of schema; no small local models. |

Shows that per-question schema selection is not new. This component credits it and differs in the label source and the model scale.

**[5] AttnLink (arXiv 2608.00693)**

| Aspect | Detail |
|---|---|
| Method | Schema linking with a per-question top-p cut on schema-item scores. |
| Dataset / Context | Text-to-SQL benchmarks. |
| Key Findings | States that the best precision/recall balance of schema linking "is generator-dependent". |
| Strengths | Closest recent work on a per-question amount of schema. |
| Limitations | The cut is a fixed rule, not learned from the generator's own execution results. |

Motivates learning the width for each generator, rather than fixing one rule for all models.

**[6] Adaptive-RAG (Jeong et al., NAACL 2024)**

| Aspect | Detail |
|---|---|
| Method | A question-complexity classifier, trained with labels from model outcomes, chooses the retrieval strategy for each question. |
| Dataset / Context | Open-domain question answering, not Text-to-SQL. |
| Key Findings | Routing by question complexity improves the cost/accuracy balance of retrieval. |
| Strengths | Establishes the idea of a router learned from the model's own outcomes. |
| Limitations | Chooses a retrieval strategy, not a schema width; uses complexity features only. |

This component credits the outcome-learned router to Adaptive-RAG and uses a complexity-only selector as a baseline that copies its design.

**[7] BudgetSchemaBench (arXiv 2610.00092)**

| Aspect | Detail |
|---|---|
| Method | Benchmark of Text-to-SQL accuracy at fixed schema budgets. |
| Dataset / Context | Text-to-SQL benchmarks; API-scale models. |
| Key Findings | Accuracy depends on the schema budget. |
| Strengths | Direct prior study of accuracy against schema amount. |
| Limitations | Fixed budgets; no small open models; no split by model size or query difficulty. |

Shows that accuracy-against-schema-amount studies are not new. This component adds the split by small model size and by query complexity.

**[8] LitE-SQL (arXiv 2510.09014)**

| Aspect | Detail |
|---|---|
| Method | Lightweight Text-to-SQL with vector-based schema linking at a fixed top-k and execution-guided SQL correction. |
| Dataset / Context | Text-to-SQL benchmarks; models from 1.5B to 7B parameters. |
| Key Findings | Reports that smaller models are less robust to irrelevant columns. |
| Strengths | Evidence for the distraction effect in small models. |
| Limitations | Uses one fixed k for all questions; does not select the amount of schema per question. |

Supports the hypothesis that the best width depends on model size.

**Further related work.** Other systems also vary the amount of schema per question: CHESS, Adaptive-Elbow (arXiv 2611.20979, a training-free per-question cut), and DecoSearch (arXiv 2606.17821, selection by an LLM). EllieSQL (arXiv 2503.22402) routes each question to "the most efficient capable" pipeline; this is the same idea as this component's label (the cheapest option that succeeds), applied to pipelines rather than schema width. RSL-SQL generates SQL with both a pruned and a full schema and chooses after generation, which costs two generations per question. AutoLink (arXiv 2511.17190) widens the schema on verification errors before generation; after a failed execution it revises only the SQL. MATS (arXiv 2512.18622) already combines several small language models as agents in one Text-to-SQL pipeline; this project does not claim multi-agent SLM Text-to-SQL as new.

### Existing Products and Systems

Cloud-hosted Text-to-SQL copilots achieve high accuracy but require transmitting schema and query data into a third-party generative-AI vendor — a data flow most regulated enterprises' internal AI-governance policy does not currently permit for live, sensitive data. Locally-run open-source Text-to-SQL tools typically perform table-level schema linking via either keyword matching or embedding similarity, then inject the full DDL of every retrieved table into the prompt, with one fixed setting for all questions. Research systems already vary the amount of schema per question (CHESS, QCMA-SQL, AttnLink, Adaptive-Elbow, DecoSearch). They set the amount with a fixed rule, gold-schema labels, model confidence or a large model. To our knowledge, as of November 2026, none of the reviewed systems learns the width from the execution results of the small local model that will use it, and chooses it once, before generation. This narrow combination is the limitation this component addresses.

## 1.3 Research Gap

> **Research Gap Statement**
> Per-question schema selection exists, and accuracy against schema amount has been measured for API-scale models and for fixed budgets on 1.5B–7B models. It is not yet established, for small local Text-to-SQL models, (a) how the best schema width changes with model size and query complexity, and (b) whether a selector that chooses one of several nested widths for each question before generation, trained on labels from the deployed model's own execution results, gives higher execution accuracy than the best fixed width and a simple complexity rule.

> **Research Question**
> For a given small local SQL model, how much schema (width) should each question get?

**Hypotheses** (each is reported as supported, not supported or not testable):

- **H1.** The best fixed width becomes narrower when the model becomes smaller. Primary test (pre-registered before the runs of other model sizes): with D(model) = accuracy(W4) − accuracy(W2), the difference D(3B) − D(0.5B) is greater than 0, and its 95% paired bootstrap CI excludes 0.
- **H2.** The best width is different for each complexity label.
- **H3.** The learned selector beats every fixed width and the complexity rule (threshold p < 0.0125).
- **H4.** A selector trained for one model is not the best selector for a different model. Test: on each other model size, the selector trained on that model's own rows against the selector trained on the 1.5B rows (exact McNemar; supported if p < 0.025 for at least one of the two sizes).

If H3 is not supported, H1 and H2 (the distraction curves) are the main finding.


# 2. OBJECTIVE

## 2.1 Main Objective

> **Main Objective**
> To design, implement, and evaluate, before the second progress presentation (PP2), a schema-width selector that chooses for each question one of four nested schema widths before SQL generation, trained on the execution results of the small local model in use, and to measure execution accuracy against width by model size and query complexity on mid-range hardware.


## 2.2 Specific Objectives

- To implement a dynamic schema-reflection engine that automatically extracts table structures and foreign-key relationships from a live relational database without hardcoded schema definitions.
- To implement four retrieval configurations — semantic-only, structural-only, hybrid, and hybrid with column-level pruning — as switchable modes of a single retrieval engine, and to use them, with the full schema, as four nested widths: W1 (anchor table only), W2 (anchor and related tables, columns pruned), W3 (the same tables, all columns) and W4 (full schema).
- To implement the column-level relevance-ranking mechanism that builds width W2.
- To build a query-complexity classification module (simple, single-join, multi-join, aggregation) shared across the project's evaluation pipeline.
- To measure execution accuracy and token count at each width W1–W4 for Qwen2.5-Instruct 0.5B, 1.5B and 3B (FP16) on the full non-nested Spider development set, Chinook and Northwind, stratified by query complexity (the distraction curves; tests H1 and H2), before PP2.
- To train a width selector on 1,200 Spider training questions, each labelled with the narrowest width whose SQL returns the correct rows, and to compare it with the fixed widths, the complexity rule, the adaptive elbow, the complexity-only selector, retry with a wider width and the oracle, using paired bootstrap CIs and exact McNemar tests (tests H3), before PP2.
- To test whether a selector trained for one model size is the best selector for another model size (tests H4), before PP2.
- To keep Agent 1's retrieval time, including the selector, under 500 ms per question, and to repeat the width study with Agent 3's fine-tuned model before the final submission.

# 3. METHODOLOGY

**1. Research Methodology**
The research question — how much schema each question should get for a given small model — is best answered through controlled, quantitative experimentation, since the outcome variables (execution accuracy, token count) are directly measurable and width can be isolated as the single controlled variable: for every question, the same model generates SQL once at each of the four widths, with the same prompt and greedy decoding. A Design Science approach is appropriate because the research produces evaluated artefacts (the retrieval engine and the width selector) alongside empirical findings (the distraction curves).

> **Selected Methodology**
> Design Science Research, incorporating a controlled quantitative experiment that compares four nested schema widths and several width-selection methods for small local SQL models of different sizes.

**2. Data / Participants / Experimental Inputs**
- Test set: all non-nested questions of the Spider development set, plus the Chinook and Northwind question sets. Questions whose gold SQL returns no rows are skipped, because an empty result cannot show a correct answer.
- Training set for the selector: 1,200 Spider training questions, from databases that are not in the test set. Every split is by database: a selector never predicts a question from a database that it trained on.
- Labels: for each question and model, the label is the narrowest width whose SQL returns the gold rows. A question with no correct width is not used for training.
- Selector inputs (all known before the SQL model runs): the four complexity probabilities, the top-3 table similarities and their gap, schema size, schema features from the complexity classifier, the token count at each width, and question length.
- Models: Qwen2.5-Instruct 0.5B, 1.5B and 3B at FP16, through transformers, with one prompt and greedy decoding for all sizes. Qwen2.5-1.5B-Instruct is the project's shared base model. A 7B model is not included, because it does not fit at FP16 on the mid-range hardware used. Agent 3's fine-tuned model replaces the base model in a later re-run.
- No real personal or proprietary data is used (see Appendix 1, Ethics Documentation).

**3. Baseline / Benchmark**
Every method is compared with the best fixed width. The baselines are:
- Fixed widths W1, W2, W3 and W4 (the existing retrieval modes plus the full schema).
- Complexity rule: W1 if the classifier gives P(simple) ≥ 0.5, else W2.
- Adaptive elbow: a training-free, per-question cut (simplified from Adaptive-Elbow, arXiv 2611.20979).
- Learned selector with complexity features only (the Adaptive-RAG design). If the full selector does not beat it, the schema and retrieval features add nothing.
- Retry with a wider width: after SQL that fails to run, the next wider width (an ablation, close to AutoLink; not a claim).
- Oracle: the narrowest correct width for each question (upper limit).

**4. Evaluation Metrics**

*Table — Evaluation Metrics for Ekanayake's Component*

| Metric | Why Relevant | Target / Comparison |
|---|---|---|
| Execution accuracy (strict match of result rows against the gold SQL) | Measures end-task success at each width and for each selection method. | Selector > best fixed width and complexity rule (H3); reported per model size and complexity bucket (H1, H2) |
| Token count per question | Measures context-window use, the primary constraint on mid-range hardware. | Reported for every width and method; lower at equal accuracy is better |
| Agent 1 retrieval time per question (with the selector) | The selector builds all four widths, so it adds retrieval work. | Median and 95th percentile under 500 ms |
| Schema-linking precision/recall | Measures whether the needed tables/columns are present at each width (engine quality). | Reported per width |
| Generated answers near the token limit | Checks that a long SQL answer is not cut by the generation limit. | Counted per width and model; reported as a limitation if above a few percent |

**5. Validation Strategy**
All comparisons are paired: each question is answered by every width and every method. Differences in accuracy are reported with a 95% paired bootstrap confidence interval (10,000 resamples of questions) and an exact McNemar test. The threshold for H3 is p < 0.0125, fixed in advance; the elbow, complexity-only and retry rows are secondary. The H1 and H4 tests were written down before the runs of the other model sizes. The selector is tested only on databases that it did not train on. Results are reported per complexity bucket, not only as one overall number. A negative result is a valid result and will be reported as such.

**6. Development Approach**
An iterative prototyping approach is used. The retrieval engine and its four modes were built and tuned first. The width sweep and the selector were then built and tested with synthetic rows and stub models, then checked on a 20-question run, before the full runs. Each sweep is resumable, so a long run can stop and continue without loss.

# 4. HIGH-LEVEL SYSTEM ARCHITECTURE

## Overview of Proposed Solution and Its Components

This component is Agent 1 in the project's multi-agent framework — the Retrieval Agent, the first stage of the overall pipeline. It receives a natural-language query and the target database's live schema. It builds the schema context at four widths, selects one width for the question, and passes that context, the width and the complexity label to Agent 3, the fine-tuning and generation component developed by another project member. It does not itself generate SQL or execute queries.

## System Diagram

> **Diagram note**
> Per the proposal template's requirement, the system diagram must be black-and-white and must not be produced using AI tools. The component structure below is provided as a text-based specification only; the actual figure must be hand-drawn or created using a diagramming tool (e.g. draw.io, Visio) by the student before submission.

*Figure — Ekanayake's Component Structure (to be redrawn as a black-and-white diagram)*

| Element | Description |
|---|---|
| Input | Natural-language query; live database connection for schema reflection |
| Schema Reflection Module | Extracts table structures and foreign-key relationships via database system-catalog queries |
| Vector Index (ChromaDB) | Stores table-level DDL embeddings for semantic anchor search |
| Retrieval Mode Switch | Selects among semantic-only, structural-only, hybrid, hybrid+pruned configurations |
| Column Pruning Stage | Ranks and filters columns within each selected table based on query relevance (builds width W2) |
| Width Builder | Builds the four nested contexts: W1 anchor table only, W2 hybrid+pruned, W3 hybrid, W4 full schema |
| Width Selector | Chooses one width for the question from features known before generation; trained on the SQL model's own execution results |
| Output | Schema context at the selected width, the width and the complexity label, passed to Agent 3 (the fine-tuned SQL-generation component) |


## Internal Sub-Agent Structure — Agent 1 (Retrieval)

Agent 1 is itself internally composed of three cooperating sub-agents, mirroring the project's overall multi-agent design philosophy at the component level rather than being a single monolithic module. The Anchor-Selection Sub-Agent decides where retrieval begins, using either semantic similarity (ChromaDB embedding search) or structural keyword matching, depending on the active retrieval mode. The Traversal Sub-Agent decides which additional tables to pull in, walking the foreign-key graph outward from the anchor table when the active mode calls for it. The Pruning Sub-Agent decides, for hybrid-pruned mode specifically, which individual columns within each selected table are retained, using lemma overlap with a word-vector similarity fallback. Together these sub-agents build the nested widths. The Width Selector then makes one more bounded decision: which width to send for this question. Each step makes one decision and passes its output to the next, composing into the single schema context that Agent 1 as a whole hands to Agent 3.

## Orchestration and Observability Harness

The four agents are coordinated by a lightweight orchestration and observability harness, rather than a general-purpose agentic framework. The pipeline's control flow is deterministic — a fixed sequence of agent calls with a single bounded retry branch — not a system in which agents autonomously choose their next action, so a full agentic framework was judged to add dependency and complexity disproportionate to what the system actually does. The harness is implemented as a FastAPI-based routing layer with three responsibilities: sequencing each agent call and passing its output to the next agent exactly as specified by the interface contracts between them; structured logging of every agent-to-agent handoff, including inputs, outputs, and timing, so the pipeline's behaviour is inspectable rather than opaque; and executing the bounded retry branch as an explicit conditional, with each retry attempt logged individually. This harness is shared engineering infrastructure, built collaboratively across the team, and is not attributed as any individual member's research novelty. As Agent 1, this component's role in the harness is limited to being invoked first, on each incoming query, with its output logged before being passed to Agent 3. After a failed attempt, the harness can ask Agent 1 for the next wider width for the retry.

## Overall Integration

This component's output (the schema context at the selected width, the width and the complexity label) is consumed directly by Agent 3 (fine-tuning and generation) as part of its prompt construction. Agent 3's output SQL is then executed by Agent 4 (quantized execution), and the base model underlying Agent 3's generation is produced by Agent 2 (model construction). Integration between agents is via the shared orchestration and observability harness described above. This component has no dependency on the other three agents' internal implementation. The width study runs with the project's shared base model; the selector is re-trained and re-tested with Agent 3's fine-tuned model when that model is available, because the labels depend on the model in use.

## Individual Responsibility Boundary

| Activity / Deliverable | My Responsibility | Shared Responsibility | Other Member |
|---|---|---|---|
| Schema reflection & FK-graph construction | ✓ |  |  |
| Four retrieval-mode implementation | ✓ |  |  |
| Column-level pruning algorithm (width W2) | ✓ |  |  |
| Width study: sweeps, width selector, distraction curves | ✓ |  |  |
| Query-complexity classifier |  | ✓ |  |
| Fine-tuning architecture (LoRA/HydraLoRA) |  |  | K.G.Y.V. Thathsarani |
| Quantization strategy (adaptive mixed precision) |  |  | K.M.I.N. Karunanayake |
| Base model construction (distillation) |  |  | W.A.T. Wathsala |
| System orchestration and observability harness |  | ✓ |  |


# 5. USER REQUIREMENTS

## Requirements Evidence

Requirements for this component were informed by consultation with the project supervisor during the topic assessment review, and by review of enterprise BI and schema-linking literature describing the needs of data analysts and database administrators querying complex relational schemas. Formal stakeholder interviews are planned as part of the requirements-refinement phase following proposal approval.

## Functional Requirements

- The system shall automatically reflect a connected database's table structures and foreign-key relationships without hardcoded schema definitions.
- The system shall retrieve a semantically relevant anchor table for a given natural-language query.
- The system shall traverse foreign-key relationships to identify structurally related tables up to a configurable depth.
- The system shall support switching between semantic-only, structural-only, hybrid, and hybrid-with-pruning retrieval modes.
- The system shall prune irrelevant columns from each selected table's schema based on query relevance.
- The system shall build four nested schema contexts (W1–W4) for a question.
- The system shall select one width for each question before SQL generation, using only features known before generation.
- The system shall give the next wider width when the harness asks for a retry after a failed attempt.
- The system shall classify each query by complexity (simple, single-join, multi-join, aggregation) prior to retrieval.
- The system shall output the schema context, the selected width and the complexity label in a format consumable by the downstream SQL-generation component.

## Non-Functional Requirements

- Performance: schema retrieval, pruning and width selection for a single query shall complete within 500ms on the target mid-range hardware, to preserve interactive responsiveness.
- Accuracy: execution accuracy shall be measured and reported per width, per model size and per complexity bucket, against the best fixed width.
- Scalability: the retrieval engine shall support schemas of at least 20 tables without requiring re-architecture.
- Reliability: the engine shall gracefully handle schemas with incomplete or missing foreign-key declarations without failing retrieval entirely.

# 6. COMMERCIALIZATION PLAN

## Target Market and Customer Persona

This component contributes to a product targeting enterprise BI teams and data-warehousing operations in regulated verticals (Corporate BI, FinTech) who require natural-language querying without transmitting schema data externally.

## Value Proposition

Efficient, accurate schema retrieval directly determines whether the overall product can run responsively on modest on-premise hardware — a prerequisite for the product's core privacy-preserving value proposition. A width chosen for each question keeps prompts short where a short prompt is enough, and wide where the question needs more tables.

## Revenue Model

As part of the integrated product, this component supports an on-premise licensing model; its context-efficiency contribution is what makes deployment on customer-owned, modest hardware commercially viable rather than requiring expensive GPU infrastructure.

## Cost Estimation

Development costs are limited to cloud storage for vector embeddings and benchmark schema preparation; no proprietary data licensing is required since Chinook, Northwind, Spider, and TPC-H are open benchmark resources.

## Pricing Strategy

Not independently priced; contributes to the overall product's tiered on-premise licensing model described in the team-level proposal.

## Competitive Advantage

The width selector is trained for the model that the customer actually runs, from that model's own execution results. When the model changes (for example, a new fine-tuned version), the selector can be re-trained with the same procedure. This fits a product that ships one small local model per installation on mid-range hardware.

## Intellectual Property Considerations

The width-selector training procedure (labels from the deployed model's own execution results), the column-level relevance-ranking algorithm and the four-mode retrieval engine implementation are potential intellectual property arising from this component.

# 7. BUDGET AND JUSTIFICATION

This component's development requires modest cloud resources for vector-database hosting during testing, plus a share of shared project costs for dataset preparation and consultation.

*Table — Budget Justification*

| Item | Description | Estimated Cost (LKR) |
|---|---|---|
| Cloud Storage | Hosting ChromaDB vector indices and schema benchmark datasets (Chinook, Spider, TPC-H) during development and testing. | 8,000 |
| Software Licenses / Tooling | Any paid tooling for embedding generation or vector-database management beyond open-source defaults. | 3,000 |
| Testing Devices and Network Costs | Cross-device testing of retrieval latency and network costs for benchmark dataset downloads. | 3,000 |
| Technical Consultation (share) | Proportional share of project-level consultation budget for schema-linking and retrieval-architecture questions. | 5,000 |

**Total Estimated Budget: LKR 19,000**

The largest cost driver is cloud storage for the vector database and benchmark schemas, since the retrieval engine's core evaluation depends on having Chinook, Spider, and TPC-H schemas all indexed and queryable throughout development.

# 8. WORK BREAKDOWN STRUCTURE (WBS)

*Table — Task Breakdown, Timeline, and Workload Distribution*

| Task | Description | Timeline |
|---|---|---|
| Requirement Analysis | Identify retrieval and pruning requirements from literature and supervisor consultation. | Month 1 |
| Schema Reflection Engine | Implement automatic FK-graph and table-structure extraction. | Month 1 |
| Complexity Classifier | Build the shared query-complexity classification module. | Month 1 |
| Retrieval Modes Implementation | Implement semantic-only, structural-only, hybrid, and hybrid+pruned modes. | Month 2–3 |
| Column Pruning Algorithm | Design and implement the column-level relevance-ranking mechanism. | Month 2–3 |
| Evaluation Harness | Build the token-count, precision/recall, and execution-accuracy measurement pipeline. | Month 3–4 |
| Width Study Design | Define the four widths, the selector, the baselines and the hypotheses; repeat the literature check. | Month 3 |
| Width Sweeps | Run every question at every width for each model size (test and training sets). | Month 3–4 |
| Selector Training and Comparison | Train the selector; compare it with all baselines; test H1–H4. | Month 4–5 |
| Re-run with Fine-Tuned Model | Repeat the width study and end-to-end evaluation with Agent 3's fine-tuned model. | Month 5–8 |
| Analysis & Reporting | Analyse results by model size and complexity bucket; prepare findings for integration and final report. | Month 4–5, then Month 9–12 |

This component's core experimental work is scheduled in Months 1–5. It uses the project's shared base model, so it does not wait for other members' outputs. The re-run with Agent 3's fine-tuned model depends on that model's delivery. Later months are reserved for system integration and final reporting alongside the rest of the team.

# 9. GANTT CHART

*Figure — Ekanayake's Component Timeline (12 Months)*

| Activity | M1 | M2 | M3 | M4 | M5 | M6 | M7 | M8 | M9 | M10 | M11 | M12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Requirement analysis & literature review |  |  |  |  |  |  |  |  |  |  |  |  |
| Schema reflection engine |  |  |  |  |  |  |  |  |  |  |  |  |
| Complexity classifier |  |  |  |  |  |  |  |  |  |  |  |  |
| Retrieval modes implementation |  |  |  |  |  |  |  |  |  |  |  |  |
| Column pruning algorithm |  |  |  |  |  |  |  |  |  |  |  |  |
| Evaluation harness build |  |  |  |  |  |  |  |  |  |  |  |  |
| Width study design |  |  |  |  |  |  |  |  |  |  |  |  |
| Width sweeps by model size |  |  |  |  |  |  |  |  |  |  |  |  |
| Selector training and comparison |  |  |  |  |  |  |  |  |  |  |  |  |
| Re-run with fine-tuned model |  |  |  |  |  |  |  |  |  |  |  |  |
| Analysis of results by model size and complexity bucket |  |  |  |  |  |  |  |  |  |  |  |  |
| System integration support |  |  |  |  |  |  |  |  |  |  |  |  |
| End-to-end feasibility testing |  |  |  |  |  |  |  |  |  |  |  |  |
| Documentation & research paper |  |  |  |  |  |  |  |  |  |  |  |  |
| Final presentation |  |  |  |  |  |  |  |  |  |  |  |  |


# 10. REFERENCES LIST

- AID-SQL: Adaptive In-Context Learning of Text-to-SQL with Difficulty-Aware Instruction and Retrieval-Augmented Generation, 2025.
- To RAG or Not to RAG, That Is the Question: Effective Text-to-SQL Generation Under Ambiguity, 2026.
- Efficient Inference Scheduling With Edge and Cloud Collaboration for LLMs Under Resource Constraints, 2026.
- Spider: A Large-Scale Human-Labeled Dataset for Complex and Cross-Domain Semantic Parsing and Text-to-SQL Task.
- TPC-H Decision Support Benchmark, Transaction Processing Performance Council.
- Minimizing Response Latency in LLM-Based Agent Systems: A Comprehensive Survey, 2026.
- QCMA-SQL, Findings of the Association for Computational Linguistics: NAACL 2025. [to verify: full title, authors]
- AttnLink, arXiv:2608.00693, 2026. [to verify: full title, authors]
- S. Jeong et al., Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity, NAACL 2024, arXiv:2403.14403. [to verify]
- BudgetSchemaBench, arXiv:2610.00092, 2026. [to verify: full title, authors]
- LitE-SQL, arXiv:2510.09014, 2025. [to verify: full title, authors]
- Adaptive-Elbow, arXiv:2611.20979, 2026. [to verify: full title, authors]
- DecoSearch, arXiv:2606.17821, 2026. [to verify: full title, authors]
- EllieSQL, COLM 2025, arXiv:2503.22402. [to verify: full title, authors]
- RSL-SQL: Robust Schema Linking in Text-to-SQL Generation, 2024. [to verify: authors, venue]
- AutoLink, arXiv:2511.17190, 2025. [to verify: full title, authors]
- CHESS: Contextual Harnessing for Efficient SQL Synthesis, 2024. [to verify: authors, venue]
- MATS, arXiv:2512.18622, 2025. [to verify: full title, authors]

> **A note on citations**
> References were compiled from the approved topic assessment form and general knowledge of the cited works' subject matter. Exact bibliographic details (authors, venue, volume, page numbers) should be independently verified before submission, as this document was prepared without live citation-lookup access. References marked "[to verify]" were added in the November 2026 revision from the literature check in reports/agent1_width/README.md; their descriptions come partly from paper summaries, so check each statement against the paper before citing it.


# 11. APPENDICES

## Appendix 1 — Supporting Evidence and Diagrams

This appendix should include the hand-drawn or diagramming-tool-created black-and-white system diagram referenced in Section 4, along with any supporting screenshots, UI sketches, or preliminary experiment outputs relevant to this component.

### Literature Comparison

| Paper | Method | Amount of Schema / Context | Key Finding | Gap vs. This Component |
|---|---|---|---|---|
| AID-SQL (2025) | Difficulty-aware in-context retrieval for Text-to-SQL | Table/example-level, adapted by difficulty | Adaptive retrieval by query difficulty beats static retrieval | Adapts examples, not the amount of schema |
| To RAG or Not to RAG (2026) | Compares RAG vs. non-RAG pipelines under schema ambiguity | Table-level | Excess retrieved context introduces noise, not just helps | No split by model size or complexity |
| Efficient Inference Scheduling (2026) | Edge/cloud inference scheduling survey | N/A (infra-focused) | Context length is a first-order driver of latency/memory on constrained hardware | General-purpose; doesn't address schema width |
| QCMA-SQL (NAACL 2025 Findings) | Learned per-question schema selector | Per question, learned | Schema selection can be learned per question | Labels from gold-SQL relevance, not the generator's own results; API models |
| AttnLink (arXiv 2608.00693) | Per-question top-p cut | Per question, rule | Best balance "is generator-dependent" | Rule, not learned per generator |
| Adaptive-RAG (NAACL 2024) | Complexity router learned from model outcomes | Retrieval strategy per question | Routing by complexity helps | Not schema width; complexity features only |
| BudgetSchemaBench (arXiv 2610.00092) | Accuracy at fixed schema budgets | Fixed budgets | Accuracy depends on budget | API models; no size or difficulty split |
| LitE-SQL (arXiv 2510.09014) | Vector schema linking, fixed top-k | Fixed k | Smaller models less robust to irrelevant columns | No per-question choice |

### Problem Analysis — Worked Example

To make the "context overload" claim concrete rather than asserted: Chinook's Customer table has 13 columns (CustomerId, FirstName, LastName, Company, Address, City, State, Country, PostalCode, Phone, Fax, Email, SupportRepId). A representative query such as "which customers spent the most?" only needs CustomerId, FirstName, LastName, and the joined Invoice.Total — roughly 3 of 13 columns, meaning around 75% of the injected table-level context for that query is irrelevant to the SLM's actual reasoning. But the same question also needs the Invoice table: a context with only the Customer table (the narrowest width) cannot answer it. The width study generalises this example: the question is not only which columns to drop, but how much schema each question should get for a given model. This is presented as an illustrative estimate; measured results are in reports/agent1_width/README.md.

### Preliminary Dataset Sample

| NL Question | Ground-Truth SQL | Complexity |
|---|---|---|
| What is the total number of tracks in the catalogue? | `SELECT COUNT(*) FROM Track;` | Simple |
| List all track names in the Rock genre. | `SELECT t.Name FROM Track t JOIN Genre g ON t.GenreId = g.GenreId WHERE g.Name = 'Rock';` | Single-join |
| Which employees support customers from Canada? | `SELECT e.FirstName, e.LastName FROM Employee e JOIN Customer c ON e.EmployeeId = c.SupportRepId WHERE c.Country = 'Canada';` | Multi-join |
| Which customers have spent more than $40 in total? | `SELECT c.CustomerId, c.FirstName, c.LastName, SUM(i.Total) AS TotalSpent FROM Customer c JOIN Invoice i ON c.CustomerId = i.CustomerId GROUP BY c.CustomerId HAVING SUM(i.Total) > 40;` | Aggregation |

These four rows are valid against the actual Chinook schema and cover all four complexity buckets; expand with the full labelled evaluation set once built.

### Ethics Documentation

This component uses only open, publicly available benchmark datasets — Chinook, Northwind, Spider, and TPC-H — none of which contain real personally identifiable or proprietary enterprise data. Where additional natural-language-question/SQL pairs are required to fill underrepresented complexity buckets, these are generated synthetically via script rather than sourced from real users or real enterprise systems, consistent with the project's broader approach of avoiding dependency on proprietary data. No stakeholder interviews or user data collection conducted for this component will involve vulnerable populations or sensitive personal data; any future interviews conducted during the requirements-refinement phase will follow standard informed-consent practice as required by the department.

### Additional Experimental Plans

Beyond the core width study, the following are identified as follow-on experiments outside this proposal's primary scope: a 7B model at reduced precision, which does not fit at FP16 on the mid-range hardware used; a two-generation, post-hoc choice between a pruned and a full schema (RSL-SQL style), which costs a second generation per question; the full adaptive elbow with smoothing windows; sensitivity of the results to the generation token limit; and generalization testing on further relational schemas, to check whether the selector's behaviour holds on schema shapes not seen during development.

## Appendix 2 — Proposal Evidence and Decision Log

This appendix records the key research decisions made during proposal development, including the evidence considered, alternatives evaluated, and discussions with the supervisor.

| Date | Claim / Problem | Evidence Collected | Alternatives Considered | Decision Made | Supervisor Discussion |
|---|---|---|---|---|---|
| 2026-06 | Original schema-retrieval novelty judged too similar to fine-tuning pillar by review panel | Panel review comments on integrated novelty | Keep table-level 3-way comparison / add column-level pruning arm | Adopted column-level pruning as the fourth, differentiating comparison arm | Discussed with supervisor; pending formal sign-off |
| 2026-06 | Full multi-table schemas risk exceeding the SLM's context window and consuming disproportionate memory on mid-range hardware, since table-level retrieval injects entire DDLs regardless of column relevance | Literature on edge-inference resource constraints (context length as a first-order driver of latency/memory); reviewed local Text-to-SQL tools that inject full DDL per retrieved table | Static full-schema prompting / table-level RAG only (existing literature) / dynamic retrieval with column-level pruning layered on top | Adopted a hybrid retrieval engine — ChromaDB semantic anchor search plus PRAGMA-based foreign-key graph traversal — with column-level pruning as the differentiating fourth configuration | Discussed context-window and hardware constraints; supervisor approved the graph-based, column-pruned retrieval direction |
| 2026-07 | Needed a concrete, defensible signal for deciding which individual columns to keep within an already-selected table | Preliminary comparison of embedding similarity vs. rule-based lemma matching for column-relevance scoring; RAG-ambiguity literature showing excess retrieved context introduces noise, not just helps | Pure spaCy embedding similarity for every column / lemma overlap only / hybrid fallback | Adopted lemma overlap first, falling back to spaCy cosine similarity only when no lemma overlap exists — balances accuracy against added embedding-computation cost on constrained hardware | Discussed feasibility given the shared mid-range hardware constraint |
| 2026-07 | Needed to decide how to measure whether column-pruning actually helps, rather than assuming it does | Review of RAG/schema-linking evaluation practice; AID-SQL's finding that retrieval-strategy effectiveness varies by query difficulty | Report a single aggregate SQL-accuracy figure / stratify all metrics by query complexity | Adopted stratified evaluation (token count, schema-linking precision/recall, execution accuracy) across the shared complexity taxonomy, with table-level hybrid retrieval as the internal baseline | To be confirmed during supervision |
| 2026-11 | Column-level pruning saved tokens but gave no significant accuracy gain with stand-in models (no loss, no gain); wide context lowered accuracy on simple questions | Phase 7–8 execution results (paired McNemar tests); literature check of 22 Nov 2026 (AttnLink, QCMA-SQL, Adaptive-Elbow, DecoSearch, DSR-SQL, Adaptive-RAG, EllieSQL, BudgetSchemaBench, LitE-SQL) | Keep pruning as the claim / claim complexity routing / claim a per-question width learned from the small model's own execution results | Main claim changed to adaptive schema context width; the four retrieval modes become fixed-width baselines; only the combination is claimed as new, "to our knowledge". Details: `reports/agent1_width/README.md` | Approved November 2026 |
| 2026-11 | Which model sizes the distraction curves can cover on the available hardware | Memory of the mid-range hardware used: 0.5B and 3B fit at FP16; 7B would need 4-bit precision, which would mix precision with size | Include 7B at reduced precision / leave 7B out | 0.5B, 1.5B and 3B at FP16 only; H1 and H4 tests written down before the runs of the other sizes (reports/agent1_width/README.md, "Pre-registered rules for model sizes") | User decision, 23 November 2026; to be reported to the supervisor |

*Table 7: Proposal Evidence and Decision Log*


## Appendix 3 — AI Use Disclosure

Generative AI tools were used during proposal preparation to support drafting, organisation of ideas, and clarification of research problems.

| AI Tool | Purpose of Use | What Was Generated / Assisted | How Output Was Verified | Final Student Contribution |
|---|---|---|---|---|
| Claude (Anthropic) | Drafting assistance and clarification of research problems and proposal structure | Helped clarify the research problem, research gap, and section structure; assisted with drafting section text, tables (literature comparison, problem analysis, evaluation metrics, decision log), and appendix content; assisted with the November 2026 revision to the adaptive-width claim and with the literature check behind it. No AI-generated images or diagrams were used in the submitted work — all system diagrams were independently created by the student, by hand or in a diagramming tool, per the template's requirement | Reviewed against the project's own individual and combined proposal documents, the approved topic-assessment scope, the width-study report (reports/agent1_width/README.md), and the proposal template's requirements | Final interpretation, research decisions, methodology, technical choices, verification of citations and technical claims, all diagrams, and all submitted content |

The use of AI does not transfer responsibility for the submitted work. The student remains responsible for accuracy, originality, validity of references, research decisions, methodology, technical choices, interpretation of evidence, and the ability to defend every part of the proposal.
