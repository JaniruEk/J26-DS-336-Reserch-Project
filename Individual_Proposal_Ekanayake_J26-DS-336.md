Sri Lanka Institute of Information
Technology
J26-DS-336
Distributed Multi-Agent SLM Framework for
Privacy-Preserving Enterprise Data Intelligence
Dynamic Schema Retrieval and Column-Level Pruning for Resource-Constrained Text-to-SQL
Individual Project Proposal Report
J.K.B. Ekanayake – IT23199262
B.Sc. (Hons) Degree in Information Technology
Specialized in Data Science
Department of Information Technology
Sri Lanka Institute of Information Technology, Sri Lanka
September 2026

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

Enterprises need natural-language access to internal databases, but sending schemas into cloud-hosted generative-AI systems is restricted at most regulated enterprises by internal AI-governance policy, reinforced by data-protection regulation, while local Small Language Models (SLMs) hallucinate on complex multi-table schemas. A major contributor to this hallucination is context overload: existing schema-retrieval methods operate at table-level granularity, injecting entire table definitions into the SLM's limited context window regardless of how many columns are actually relevant. This component investigates whether pruning schema context at column level, layered on structural and semantic table retrieval, improves both context efficiency and downstream SQL accuracy under a fixed token budget. Evidence from recent Text-to-SQL retrieval literature shows accuracy gains from table-level schema linking, but little work examines pruning within a selected table. The identified gap is addressed through a controlled four-way comparison — semantic-only, structural-only, hybrid, and hybrid-with-column-pruning retrieval — implemented on a foreign-key-reflecting, ChromaDB-backed retrieval engine, in which anchor selection, structural traversal, and column pruning are treated as three cooperating internal sub-agents. The research follows a Design Science methodology, using the Chinook database and Spider/TPC-H schemas as enterprise-database proxies, with an iterative prototyping development approach. Evaluation measures token count, schema-linking precision/recall, and downstream SQL execution accuracy, stratified by query complexity (simple, single-join, multi-join, aggregation). Results will be validated by comparing table-level-only baselines drawn from existing literature. Within the complete four-component system, this module supplies the pruned schema context consumed by the fine-tuning and generation component, directly determining how much of the SLM's limited context budget is available for reasoning rather than redundant schema text.

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

Road-scale enterprise data querying increasingly relies on natural-language interfaces, but sending sensitive schema and transaction data into cloud-hosted, third-party generative-AI systems is restricted at most regulated enterprises — not because third-party data sharing itself is prohibited (established vendor relationships operate under audited contracts routinely), but because a generative-AI vendor is a newer, less-precedented category that internal AI-governance and vendor-risk policy, reinforced by regulations such as GDPR and CCPA, treats far more cautiously than a long-established third-party relationship. Locally hosted Small Language Models avoid this exposure, but are known to hallucinate heavily when reasoning over complex, multi-table schemas — a limitation with direct financial and legal consequences for regulated enterprises in Corporate Business Intelligence, FinTech, and Data Warehousing verticals.

One significant, under-addressed contributor to this hallucination is context overload: when an SLM is given a full multi-table schema with dozens of columns per table, much of that context is irrelevant to any single query, consuming the model's limited attention and context window while providing no benefit. This is particularly acute on mid-range consumer-grade hardware, where context length directly trades off against inference speed and memory headroom.

This component addresses the schema-retrieval and context-construction problem specifically: given a natural-language query and a full enterprise schema, how should the system decide exactly which tables and which columns to expose to the downstream SQL-generation model. The proposed solution combines foreign-key graph traversal, semantic vector retrieval, and a novel column-level pruning stage, evaluated under the project's shared mid-range hardware constraint.

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
| Limitations | Operates at table/example level; does not address column-level context pruning within a selected table. |

Motivates this component's decision to stratify evaluation by query complexity rather than reporting a single aggregate accuracy figure.

**[2] To RAG or Not to RAG, That Is the Question: Effective Text-to-SQL Generation Under Ambiguity (2026)**

| Aspect | Detail |
|---|---|
| Method | Comparative analysis of RAG-based versus non-RAG Text-to-SQL pipelines under schema ambiguity. |
| Dataset / Context | Ambiguous-query subsets of standard Text-to-SQL benchmarks. |
| Key Findings | Retrieval augmentation helps disambiguate schema references, but excess retrieved context can itself introduce noise. |
| Strengths | Highlights that retrieval quantity, not just presence, affects generation accuracy. |
| Limitations | Does not isolate table-level versus column-level retrieval granularity as a variable. |

Directly supports the hypothesis underlying this component: that reducing retrieved context to only relevant columns, not just relevant tables, should reduce noise and improve accuracy.

**[3] Efficient Inference Scheduling With Edge and Cloud Collaboration for LLMs Under Resource Constraints (2026)**

| Aspect | Detail |
|---|---|
| Method | Survey and benchmarking of inference scheduling strategies balancing edge and cloud resources for LLM deployment. |
| Dataset / Context | Simulated and real edge-hardware inference workloads. |
| Key Findings | Context length is a first-order determinant of inference latency and memory footprint on constrained hardware. |
| Strengths | Provides quantitative grounding for why context-window efficiency matters on edge-class GPUs. |
| Limitations | General-purpose inference scheduling; does not address domain-specific context construction (e.g. schema pruning). |

Provides the technical justification for treating token count as a primary evaluation metric in this component.

### Existing Products and Systems

Cloud-hosted Text-to-SQL copilots achieve high accuracy but require transmitting schema and query data into a third-party generative-AI vendor — a data flow most regulated enterprises' internal AI-governance policy does not currently permit for live, sensitive data. Locally-run open-source Text-to-SQL tools typically perform table-level schema linking via either keyword matching or embedding similarity, then inject the full DDL of every retrieved table into the prompt. None of the locally-run tools reviewed perform column-level pruning within a selected table; this is the specific limitation this component addresses.

## 1.3 Research Gap

> **Research Gap Statement**
> Existing schema-retrieval approaches for local, SLM-scale Text-to-SQL systems operate at table-level granularity, injecting complete table schemas into a constrained context window regardless of column relevance; it is not yet established whether column-level pruning, evaluated under a fixed token budget and across varying query complexity, improves retrieval efficiency and downstream SQL accuracy over table-level-only retrieval strategies.


# 2. OBJECTIVE

## 2.1 Main Objective

> **Main Objective**
> To design, implement, and evaluate a column-level schema-pruning mechanism, layered on structural and semantic table retrieval, that improves context efficiency and downstream SQL execution accuracy under a fixed token budget on mid-range hardware.


## 2.2 Specific Objectives

- To implement a dynamic schema-reflection engine that automatically extracts table structures and foreign-key relationships from a live relational database without hardcoded schema definitions.
- To implement four retrieval configurations — semantic-only, structural-only, hybrid, and hybrid with column-level pruning — as switchable modes of a single retrieval engine.
- To design a column-level relevance-ranking mechanism that determines which columns within a selected table are retained in the generation context.
- To build a query-complexity classification module (simple, single-join, multi-join, aggregation) shared across the project's evaluation pipeline.
- To evaluate all four retrieval configurations on token count, schema-linking precision/recall, and downstream SQL execution accuracy, stratified by query complexity.
- To identify the retrieval configuration that best balances context efficiency and accuracy for deployment on the project's target hardware.

# 3. METHODOLOGY

**1. Research Methodology**
The research question — whether retrieval granularity affects context efficiency and downstream accuracy — is best answered through controlled, quantitative experimentation rather than qualitative or observational methods, since the outcome variables (token count, precision/recall, execution accuracy) are directly measurable and the four retrieval configurations can be isolated as a single controlled variable. A Design Science approach is appropriate because the research produces an evaluated artefact (the retrieval engine) alongside empirical findings.

> **Selected Methodology**
> Design Science Research, incorporating a controlled quantitative experiment comparing four retrieval configurations.

**2. Data / Participants / Experimental Inputs**
The Chinook relational database serves as the primary enterprise-database proxy, supplemented by the Spider dataset and TPC-H decision-support benchmark for schema complexity beyond Chinook's scope. A labelled evaluation set of natural-language-question and ground-truth-SQL pairs is required, tagged by query complexity; where an existing labelled set does not provide sufficient examples per complexity bucket, additional synthetic pairs will be generated using Python-based scripts, consistent with the project's synthetic-data approach for avoiding proprietary data dependency.

**3. Baseline / Benchmark**
The table-level hybrid retrieval approach (semantic anchor selection plus foreign-key graph traversal, without column pruning) serves as the primary internal baseline, representing the retrieval strategy typical of existing schema-linking literature. Semantic-only and structural-only configurations serve as secondary baselines to isolate the contribution of each retrieval signal independently.

**4. Evaluation Metrics**

*Table — Evaluation Metrics for Ekanayake's Component*

| Metric | Why Relevant | Target / Comparison |
|---|---|---|
| Token count per query | Directly measures context-window efficiency, the primary constraint on mid-range hardware. | Minimise, relative to table-level baseline |
| Schema-linking precision/recall | Measures whether the correct tables/columns were retrieved against ground truth. | Maximise, ≥ hybrid baseline |
| Downstream SQL execution accuracy | Measures end-task success — whether the generated SQL, given this context, executes correctly. | Outperform table-level-only baseline, especially on multi-join/aggregation buckets |

**5. Validation Strategy**
Results are validated through stratified evaluation across the shared query-complexity taxonomy, allowing the analysis to determine not only whether column-pruning helps on average but specifically where it helps or hurts. Statistical comparison (e.g. paired accuracy differences per query) between configurations will be used rather than relying on a single aggregate accuracy number, consistent with accepted evaluation practice in the retrieval-augmented generation literature reviewed above.

**6. Development Approach**
An iterative prototyping approach is appropriate given the exploratory nature of the research: each retrieval configuration is implemented, tested against a small validation subset, and refined before full-scale evaluation, allowing early detection of implementation issues (e.g. FK-graph traversal errors) without committing to a fixed design upfront.

# 4. HIGH-LEVEL SYSTEM ARCHITECTURE

## Overview of Proposed Solution and Its Components

This component is Agent 1 in the project's multi-agent framework — the Dynamic Retrieval and Pruning Agent, the first stage of the overall pipeline. It receives a natural-language query and the target database's live schema, and produces a minimal, pruned schema context that is passed to Agent 3, the fine-tuning and generation component developed by another project member. It does not itself generate SQL or execute queries.

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
| Column Pruning Stage | Ranks and filters columns within each selected table based on query relevance |
| Output | Pruned schema context, passed to Agent 3 (the fine-tuned SQL-generation component) |


## Internal Sub-Agent Structure — Agent 1 (Retrieval)

Agent 1 is itself internally composed of three cooperating sub-agents, mirroring the project's overall multi-agent design philosophy at the component level rather than being a single monolithic module. The Anchor-Selection Sub-Agent decides where retrieval begins, using either semantic similarity (ChromaDB embedding search) or structural keyword matching, depending on the active retrieval mode. The Traversal Sub-Agent decides which additional tables to pull in, walking the foreign-key graph outward from the anchor table when the active mode calls for it. The Pruning Sub-Agent decides, for hybrid-pruned mode specifically, which individual columns within each selected table are retained, using lemma overlap with a word-vector similarity fallback. Each sub-agent makes one bounded decision and passes its output to the next, composing into the single pruned schema context that Agent 1 as a whole hands to Agent 3.

## Orchestration and Observability Harness

The four agents are coordinated by a lightweight orchestration and observability harness, rather than a general-purpose agentic framework. The pipeline's control flow is deterministic — a fixed sequence of agent calls with a single bounded retry branch — not a system in which agents autonomously choose their next action, so a full agentic framework was judged to add dependency and complexity disproportionate to what the system actually does. The harness is implemented as a FastAPI-based routing layer with three responsibilities: sequencing each agent call and passing its output to the next agent exactly as specified by the interface contracts between them; structured logging of every agent-to-agent handoff, including inputs, outputs, and timing, so the pipeline's behaviour is inspectable rather than opaque; and executing the bounded retry branch as an explicit conditional, with each retry attempt logged individually. This harness is shared engineering infrastructure, built collaboratively across the team, and is not attributed as any individual member's research novelty. As Agent 1, this component's role in the harness is limited to being invoked first, on each incoming query, with its output logged before being passed to Agent 3.

## Overall Integration

This component's output (pruned schema context) is consumed directly by Agent 3 (fine-tuning and generation) as part of its prompt construction. Agent 3's output SQL is then executed by Agent 4 (quantized execution), and the base model underlying Agent 3's generation is produced by Agent 2 (model construction). Integration between agents is via the shared orchestration and observability harness described above; this component has no dependency on the other three agents' internal implementation and can be developed and evaluated independently, requiring only a working SLM (any candidate model) to measure downstream execution accuracy.

## Individual Responsibility Boundary

| Activity / Deliverable | My Responsibility | Shared Responsibility | Other Member |
|---|---|---|---|
| Schema reflection & FK-graph construction | ✓ |  |  |
| Four retrieval-mode implementation | ✓ |  |  |
| Column-level pruning algorithm | ✓ |  |  |
| Query-complexity classifier |  | ✓ |  |
| Fine-tuning architecture (LoRA/HydraLoRA) |  |  | K.G.Y.V. Thathsarani |
| Quantization strategy (QAT/PTQ) |  |  | K.M.I.N. Karunanayake |
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
- The system shall classify each query by complexity (simple, single-join, multi-join, aggregation) prior to retrieval.
- The system shall output pruned schema context in a format consumable by the downstream SQL-generation component.

## Non-Functional Requirements

- Performance: schema retrieval and pruning for a single query shall complete within 500ms on the target mid-range hardware, to preserve interactive responsiveness.
- Accuracy: schema-linking precision and recall shall be measured and reported per complexity bucket, with a target of no regression versus the table-level hybrid baseline.
- Scalability: the retrieval engine shall support schemas of at least 20 tables without requiring re-architecture.
- Reliability: the engine shall gracefully handle schemas with incomplete or missing foreign-key declarations without failing retrieval entirely.

# 6. COMMERCIALIZATION PLAN

## Target Market and Customer Persona

This component contributes to a product targeting enterprise BI teams and data-warehousing operations in regulated verticals (Corporate BI, FinTech) who require natural-language querying without transmitting schema data externally.

## Value Proposition

Efficient, accurate schema retrieval directly determines whether the overall product can run responsively on modest on-premise hardware — a prerequisite for the product's core privacy-preserving value proposition.

## Revenue Model

As part of the integrated product, this component supports an on-premise licensing model; its context-efficiency contribution is what makes deployment on customer-owned, modest hardware commercially viable rather than requiring expensive GPU infrastructure.

## Cost Estimation

Development costs are limited to cloud storage for vector embeddings and benchmark schema preparation; no proprietary data licensing is required since Chinook, Spider, and TPC-H are open benchmark resources.

## Pricing Strategy

Not independently priced; contributes to the overall product's tiered on-premise licensing model described in the team-level proposal.

## Competitive Advantage

Column-level pruning under a fixed token budget is not implemented in reviewed existing local Text-to-SQL tools, offering a differentiated efficiency advantage specifically relevant to resource-constrained, on-premise deployment.

## Intellectual Property Considerations

The column-level relevance-ranking algorithm and the four-mode retrieval engine implementation are potential intellectual property arising from this component.

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
| Experimentation | Run all four configurations across the labelled evaluation set. | Month 4 |
| Analysis & Reporting | Analyse results by complexity bucket; prepare findings for integration and final report. | Month 4–5, then Month 9–12 |

This component's core experimental work is scheduled in Months 1–5, since it has no dependency on other members' outputs and its evaluation only requires a working SLM (not necessarily the project's final model) to measure downstream accuracy. Later months are reserved for system integration and final reporting alongside the rest of the team.

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
| Experimentation & data collection |  |  |  |  |  |  |  |  |  |  |  |  |
| Analysis of results by complexity bucket |  |  |  |  |  |  |  |  |  |  |  |  |
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

> **A note on citations**
> References were compiled from the approved topic assessment form and general knowledge of the cited works' subject matter. Exact bibliographic details (authors, venue, volume, page numbers) should be independently verified before submission, as this document was prepared without live citation-lookup access.


# 11. APPENDICES

## Appendix 1 — Supporting Evidence and Diagrams

This appendix should include the hand-drawn or diagramming-tool-created black-and-white system diagram referenced in Section 4, along with any supporting screenshots, UI sketches, or preliminary experiment outputs relevant to this component.

### Literature Comparison

| Paper | Method | Retrieval Granularity | Key Finding | Gap vs. This Component |
|---|---|---|---|---|
| AID-SQL (2025) | Difficulty-aware in-context retrieval for Text-to-SQL | Table/example-level | Adaptive retrieval by query difficulty beats static retrieval | Does not prune within a selected table — no column-level mechanism |
| To RAG or Not to RAG (2026) | Compares RAG vs. non-RAG pipelines under schema ambiguity | Table-level | Excess retrieved context introduces noise, not just helps | Doesn't isolate table-level vs. column-level granularity as a variable |
| Efficient Inference Scheduling (2026) | Edge/cloud inference scheduling survey | N/A (infra-focused) | Context length is a first-order driver of latency/memory on constrained hardware | General-purpose; doesn't address domain-specific context construction (schema pruning) |

### Problem Analysis — Worked Example

To make the "context overload" claim concrete rather than asserted: Chinook's Customer table has 13 columns (CustomerId, FirstName, LastName, Company, Address, City, State, Country, PostalCode, Phone, Fax, Email, SupportRepId). A representative query such as "which customers spent the most?" only needs CustomerId, FirstName, LastName, and the joined Invoice.Total — roughly 3 of 13 columns, meaning around 75% of the injected table-level context for that query is irrelevant to the SLM's actual reasoning. This is presented as an illustrative estimate; once the retrieval engine is implemented, this should be replaced with the measured per-query column-utilization rate across the evaluation set.

### Preliminary Dataset Sample

| NL Question | Ground-Truth SQL | Complexity |
|---|---|---|
| What is the total number of tracks in the catalogue? | `SELECT COUNT(*) FROM Track;` | Simple |
| List all track names in the Rock genre. | `SELECT t.Name FROM Track t JOIN Genre g ON t.GenreId = g.GenreId WHERE g.Name = 'Rock';` | Single-join |
| Which employees support customers from Canada? | `SELECT e.FirstName, e.LastName FROM Employee e JOIN Customer c ON e.EmployeeId = c.SupportRepId WHERE c.Country = 'Canada';` | Multi-join |
| Which customers have spent more than $40 in total? | `SELECT c.CustomerId, c.FirstName, c.LastName, SUM(i.Total) AS TotalSpent FROM Customer c JOIN Invoice i ON c.CustomerId = i.CustomerId GROUP BY c.CustomerId HAVING SUM(i.Total) > 40;` | Aggregation |

These four rows are valid against the actual Chinook schema and cover all four complexity buckets; expand with the full labelled evaluation set once built.

### Ethics Documentation

This component uses only open, publicly available benchmark datasets — Chinook, Spider, and TPC-H — none of which contain real personally identifiable or proprietary enterprise data. Where additional natural-language-question/SQL pairs are required to fill underrepresented complexity buckets, these are generated synthetically via script rather than sourced from real users or real enterprise systems, consistent with the project's broader approach of avoiding dependency on proprietary data. No stakeholder interviews or user data collection conducted for this component will involve vulnerable populations or sensitive personal data; any future interviews conducted during the requirements-refinement phase will follow standard informed-consent practice as required by the department.

### Additional Experimental Plans

Beyond the core four-mode comparison, the following are identified as follow-on experiments outside this proposal's primary scope: sensitivity analysis of the spaCy cosine-similarity threshold used in the Pruning Sub-Agent, to determine how performance changes as the threshold is loosened or tightened; generalization testing on relational schemas beyond Chinook, Spider, and TPC-H, to check whether the pruning mechanism's benefit holds on schema shapes not seen during development; and retrieval-latency scaling tests at table counts beyond Chinook's native scope, to stress-test the 500ms non-functional requirement as schema size grows.

## Appendix 2 — Proposal Evidence and Decision Log

This appendix records the key research decisions made during proposal development, including the evidence considered, alternatives evaluated, and discussions with the supervisor.

| Date | Claim / Problem | Evidence Collected | Alternatives Considered | Decision Made | Supervisor Discussion |
|---|---|---|---|---|---|
| 2026-06 | Original schema-retrieval novelty judged too similar to fine-tuning pillar by review panel | Panel review comments on integrated novelty | Keep table-level 3-way comparison / add column-level pruning arm | Adopted column-level pruning as the fourth, differentiating comparison arm | Discussed with supervisor; pending formal sign-off |
| 2026-06 | Full multi-table schemas risk exceeding the SLM's context window and consuming disproportionate memory on mid-range hardware, since table-level retrieval injects entire DDLs regardless of column relevance | Literature on edge-inference resource constraints (context length as a first-order driver of latency/memory); reviewed local Text-to-SQL tools that inject full DDL per retrieved table | Static full-schema prompting / table-level RAG only (existing literature) / dynamic retrieval with column-level pruning layered on top | Adopted a hybrid retrieval engine — ChromaDB semantic anchor search plus PRAGMA-based foreign-key graph traversal — with column-level pruning as the differentiating fourth configuration | Discussed context-window and hardware constraints; supervisor approved the graph-based, column-pruned retrieval direction |
| 2026-07 | Needed a concrete, defensible signal for deciding which individual columns to keep within an already-selected table | Preliminary comparison of embedding similarity vs. rule-based lemma matching for column-relevance scoring; RAG-ambiguity literature showing excess retrieved context introduces noise, not just helps | Pure spaCy embedding similarity for every column / lemma overlap only / hybrid fallback | Adopted lemma overlap first, falling back to spaCy cosine similarity only when no lemma overlap exists — balances accuracy against added embedding-computation cost on constrained hardware | Discussed feasibility given the shared mid-range hardware constraint |
| 2026-07 | Needed to decide how to measure whether column-pruning actually helps, rather than assuming it does | Review of RAG/schema-linking evaluation practice; AID-SQL's finding that retrieval-strategy effectiveness varies by query difficulty | Report a single aggregate SQL-accuracy figure / stratify all metrics by query complexity | Adopted stratified evaluation (token count, schema-linking precision/recall, execution accuracy) across the shared complexity taxonomy, with table-level hybrid retrieval as the internal baseline | To be confirmed during supervision |

*Table 7: Proposal Evidence and Decision Log*


## Appendix 3 — AI Use Disclosure

Generative AI tools were used during proposal preparation to support drafting, organisation of ideas, and clarification of research problems.

| AI Tool | Purpose of Use | What Was Generated / Assisted | How Output Was Verified | Final Student Contribution |
|---|---|---|---|---|
| Claude (Anthropic) | Drafting assistance and clarification of research problems and proposal structure | Helped clarify the research problem, research gap, and section structure; assisted with drafting section text, tables (literature comparison, problem analysis, evaluation metrics, decision log), and appendix content. No AI-generated images or diagrams were used in the submitted work — all system diagrams were independently created by the student, by hand or in a diagramming tool, per the template's requirement | Reviewed against the project's own individual and combined proposal documents, the approved topic-assessment scope, and the proposal template's requirements | Final interpretation, research decisions, methodology, technical choices, verification of citations and technical claims, all diagrams, and all submitted content |

The use of AI does not transfer responsibility for the submitted work. The student remains responsible for accuracy, originality, validity of references, research decisions, methodology, technical choices, interpretation of evidence, and the ability to defend every part of the proposal.
