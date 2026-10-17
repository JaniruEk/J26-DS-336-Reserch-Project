J26-DS-336
Distributed Multi-Agent SLM Framework for
Privacy-Preserving Enterprise Data Intelligence
Complexity-Specialised Fine-Tuning Architecture Selection for Deployable SQL-Generation SLMs: Standard LoRA vs. HydraLoRA
Individual Project Proposal Report
K.G.Y.V. Thathsarani – IT23404250
B.Sc. (Hons) Degree in Information Technology
Specialized in Data Science
Department of Information Technology
Sri Lanka Institute of Information Technology, Sri Lanka
September 2026

# DECLARATION

I declare that this is my own work, and this proposal does not knowingly incorporate any material previously submitted for a degree or diploma at any other university or higher education institution, nor does it contain any material that has been previously published or written by another person apart from where proper acknowledgment is given in the text.

| Name | Student ID | Signature |
|---|---|---|
| K.G.Y.V. Thathsarani | IT23404250 |  |

The above candidate is conducting research for their undergraduate dissertation under my supervision.

| Name | Date | Signature |
|---|---|---|
| Prof. Nathali Silva |  |  |
| Mr. Theshan Senanayake |  |  |


# ABSTRACT

Text-to-SQL is not a homogeneous task: query complexity ranges from simple single-table lookups to multi-table joins combined with aggregation functions, and this project's own problem statement identifies exactly that range — multi-join and aggregation reasoning — as the specific failure mode where locally-hosted small language models suffer severe logic degradation. Standard Low-Rank Adaptation (LoRA) fine-tunes a single, shared adapter across this entire range of difficulty, forcing one adapter to represent tasks that plausibly require different reasoning, a compromise the literature does not evaluate directly. This component investigates whether an asymmetric multi-head LoRA architecture — HydraLoRA, sharing a common down-projection matrix but learning separate up-projection heads specialised by query-complexity bucket — improves multi-join and aggregation reasoning over standard LoRA without a proportional increase in trainable parameters, using hard-coded, classifier-based routing to each head rather than HydraLoRA's original unsupervised auto-clustering, a deliberate scope simplification appropriate to the project timeline. Evidence from parameter-efficient fine-tuning literature shows LoRA-based approaches can correct Text-to-SQL errors effectively, but existing work uses a single, undifferentiated adapter and does not evaluate architecture-level specialisation by within-domain task heterogeneity; HydraLoRA itself has been evaluated on distinct multi-task instruction-tuning benchmarks, not on within-domain complexity variation such as SQL query difficulty. The identified gap is addressed through a controlled, quantitative comparison training both architectures under identical conditions — same base model, dataset, epochs, and hardware budget — evaluated on exact-match accuracy, JOIN/aggregation-specific accuracy, and trainable parameter count, stratified by the project's shared query-complexity taxonomy. To avoid idle dependency on the base-model component, this comparison is run immediately on a plain off-the-shelf placeholder base model, and re-validated once the project's actual winning base model is available. This component does not stop at selecting a winner: it also reports the runner-up architecture as a first-class output, since a downstream component (quantization strategy selection) uses it to test whether a quantization-strategy ranking established on the winning architecture holds when applied to a different fine-tuning architecture — a cross-check made possible precisely because this component reports both results rather than discarding the comparison once a winner is named. The research follows a Design Science methodology using an iterative, benchmark-driven development approach. Within the complete system, this component consumes the pruned schema context produced by the retrieval component and the base model produced by the model-construction component, and produces the fine-tuned SQL-generation model — both the winning architecture and the runner-up — that the quantization-and-execution component compresses and deploys.
Keywords: Text-to-SQL, Parameter-Efficient Fine-Tuning, LoRA, HydraLoRA, Query-Complexity Specialisation, Small Language Models

# ACKNOWLEDGEMENT

I would like to thank my research supervisor, Prof. Nathali Silva, and co-supervisor, Mr. Theshan Senanayake, for their guidance and constructive feedback throughout the development of this proposal, including through two rounds of scope revision — first when this comparison was briefly consolidated with quantization strategy under a teammate's ownership to test whether the two decisions interact, and again when the team reconsidered a proposed OLAP/MDX research pillar and settled on retaining this fine-tuning-architecture comparison as my own component instead, with the cross-stage interaction question preserved through a smaller, artifact-based cross-check owned downstream.
I am also grateful to the Sri Lanka Institute of Information Technology (SLIIT) and the Department of Information Technology for the academic resources and learning environment provided. I further acknowledge my project teammates — working on the other three components of this system — whose collaboration helped clarify how this individual component connects to the complete solution, in particular my teammate who quantizes and deploys the architecture this component selects.
Finally, I thank my family and friends for their continued encouragement throughout this academic undertaking.

# TABLE OF CONTENT

(Auto-generated in the final submitted document via Word's Table of Contents feature, referencing the Heading styles used throughout this report.)

# LIST OF TABLES

Table 1. Evaluation Metrics for Thathsarani's Component
Table 2. Budget Justification
Table 3. Task Breakdown, Timeline, and Workload Distribution
Table 4. Individual Responsibility Boundary

# LIST OF FIGURES

Figure 1. Thathsarani's Component Structure
Figure 2. Gantt Chart — 12-Month Timeline

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
| SQL | Structured Query Language |
| FK | Foreign Key |
| DDL | Data Definition Language |
| GDPR | General Data Protection Regulation |
| CCPA | California Consumer Privacy Act |
| SDG | Sustainable Development Goal |
| CEAI | Computing, Engineering and AI (research cluster) |


# LIST OF APPENDICES

Appendix 1 – Supporting Evidence and Diagrams
Appendix 2 – Proposal Evidence and Decision Log
Appendix 3 – AI Use Disclosure

# 1. INTRODUCTION


## 1.1 Background and Context

Enterprises require natural-language database querying without transmitting proprietary schema or transaction data to cloud LLMs, motivating locally hosted Small Language Models fine-tuned specifically for Text-to-SQL generation. Text-to-SQL, however, is not a homogeneous task: query complexity ranges from simple single-table lookups to multi-table joins combined with aggregation functions, and these require materially different reasoning. This project's own problem statement identifies multi-join and aggregation reasoning as the specific failure mode where off-the-shelf small models suffer "severe logic degradation," yet the standard fine-tuning approach — a single, shared LoRA adapter — must compromise across this entire range of difficulty rather than specialising for it.
This component investigates an architecture-level solution rather than simply tuning hyperparameters of a single adapter: specialising adapter capacity by query complexity, using an asymmetric multi-head LoRA design (HydraLoRA) with a shared down-projection matrix and per-complexity up-projection heads. The output of this comparison — a winning fine-tuning architecture — is not the end of this component's contribution to the wider project: the runner-up architecture is reported and preserved as well, specifically so that the project's quantization-strategy component can test whether its own findings are stable across fine-tuning architectures, rather than being an artifact of whichever architecture happened to win this comparison.
This work aligns with SDG 9 (Industry, Innovation and Infrastructure) and the CEAI research cluster's focus on efficient, resource-constrained AI systems for enterprise use.

## 1.2 Literature Review

The following peer-reviewed and benchmark sources were critically evaluated for their relevance to this component:
[1] Exploring Large Language Models for Text-to-SQL Error Correction with LoRA Fine-Tuning

| Aspect | Detail |
|---|---|
| Method | LoRA-based fine-tuning applied to correct erroneous SQL generated by a base LLM. |
| Dataset / Context | Text-to-SQL benchmark with injected and naturally-occurring generation errors. |
| Key Findings | LoRA fine-tuning meaningfully reduces syntax and simple logic errors in generated SQL. |
| Strengths | Demonstrates LoRA's practical effectiveness for SQL-specific adaptation at low parameter cost. |
| Limitations | Uses a single, undifferentiated LoRA adapter; does not investigate whether adapter specialisation by query type improves results further. |

Establishes standard LoRA as a valid, literature-supported baseline for this component's comparison.
[2] Leveraging Large Language Model for Enhanced Text-to-SQL Parsing (2026)

| Aspect | Detail |
|---|---|
| Method | Fine-tuning and prompt-engineering techniques to improve SQL parsing accuracy on complex schemas. |
| Dataset / Context | Cross-domain Text-to-SQL benchmarks including multi-table join scenarios. |
| Key Findings | Accuracy degrades disproportionately on multi-table joins and aggregation queries compared to simple lookups. |
| Strengths | Provides direct evidence that query complexity, not just schema size, drives accuracy degradation. |
| Limitations | Does not propose an architecture-level fix targeting this specific degradation pattern. |

Directly motivates this component's hypothesis that complexity-aware adapter specialisation, rather than a single generic adapter, should specifically target the multi-join/aggregation accuracy gap.
[3] HydraLoRA: An Asymmetric LoRA Architecture for Efficient Fine-Tuning, 2024

| Aspect | Detail |
|---|---|
| Method | Asymmetric multi-head LoRA: a shared down-projection matrix (A) with multiple task-specialised up-projection heads (B), combined via a learned router. |
| Dataset / Context | Heterogeneous multi-task instruction-tuning benchmarks. |
| Key Findings | Multi-head specialisation improves performance on heterogeneous tasks over single-adapter LoRA without a proportional parameter increase, since only the smaller B matrices are duplicated. |
| Strengths | Provides the core architectural mechanism this component adapts; demonstrates the parameter-efficiency claim empirically in a different domain. |
| Limitations | Applied to distinct multi-domain tasks, not to within-domain complexity variation such as SQL query difficulty; uses unsupervised auto-clustering to route inputs to heads. |

This component adapts HydraLoRA's shared-A/multi-head-B architecture specifically to SQL query-complexity buckets, using hard-coded routing via a shared complexity classifier instead of unsupervised auto-clustering, as a deliberate scope decision appropriate to the project's timeline.
Existing Products and Systems
Reviewed open-source Text-to-SQL fine-tuning pipelines uniformly apply a single LoRA (or QLoRA) adapter across the full training set, regardless of query complexity. None of the locally-run tools reviewed implement task-heterogeneity-aware adapter architectures specifically for SQL query complexity; this is the specific limitation this component addresses.

## 1.3 Research Gap

| Research Gap Statement Standard LoRA fine-tuning applies one shared low-rank adapter across the full heterogeneity of Text-to-SQL query complexity. It is not established whether an asymmetric multi-head LoRA architecture, specialised by query-complexity bucket, improves multi-join and aggregation reasoning accuracy over standard LoRA without a proportional increase in trainable parameters — nor, since the choice of fine-tuning architecture feeds directly into a downstream compression decision made by another component, whether that downstream decision's own findings hold regardless of which fine-tuning architecture produced the model being compressed. |
|---|


# 2. OBJECTIVE


## 2.1 Main Objective

| Main Objective To design, implement, and evaluate an asymmetric multi-head LoRA (HydraLoRA) fine-tuning architecture, specialised by SQL query complexity via hard-coded classifier-based routing, against standard single-adapter LoRA, and to report both the winning and runner-up architectures as first-class outputs for downstream compression and deployment. |
|---|


## 2.2 Specific Objectives

- To construct a Text-to-SQL fine-tuning dataset with each example labelled by query complexity, using the project's shared complexity classifier.
- To implement a standard single-adapter LoRA fine-tuning pipeline using the PEFT library as the control condition.
- To implement a custom HydraLoRA module with a shared down-projection matrix and complexity-specialised up-projection heads.
- To implement hard-coded, classifier-based routing of training and inference examples to the appropriate HydraLoRA head.
- To train both architectures under identical conditions — same base model, dataset, epochs, and hardware budget — running an initial comparison on a placeholder base model, then re-validating on the project's actual base model once available.
- To evaluate both architectures on exact-match accuracy, JOIN/aggregation-specific accuracy, and trainable parameter count, stratified by complexity bucket, and identify both the winning and runner-up architecture.
- To package and hand off both the winning and runner-up fine-tuned architectures to the project's quantization-and-execution component, including the shared evaluation artefacts needed for that component's cross-check.

# 3. METHODOLOGY

1. Research Methodology
The research question — whether architecture-level specialisation improves fine-tuning outcomes for a specific task-heterogeneity pattern — requires controlled, quantitative comparison with all confounding variables (base model, dataset, training budget) held constant. A Design Science approach is appropriate because the research produces an evaluated artefact (the HydraLoRA implementation) alongside empirical comparative findings.

| Selected Methodology Design Science Research, incorporating a controlled quantitative experiment comparing standard LoRA and HydraLoRA architectures under identical training conditions. |
|---|

2. Data / Participants / Experimental Inputs
A synthetic Text-to-SQL training and evaluation dataset, generated via Python-based scripts and labelled by the shared query-complexity taxonomy, is required in sufficient quantity per complexity bucket — particularly multi-join and aggregation examples, where HydraLoRA's advantage is hypothesised to be largest. Bucket sizes will be checked early in development, with deliberate over-sampling of harder categories if under-represented.
3. Baseline / Benchmark
Standard single-adapter LoRA, fine-tuned on the identical dataset and base model, serves as the primary baseline, representing the approach used in the reviewed LoRA-based Text-to-SQL literature.
4. Evaluation Metrics
Table 1 — Evaluation Metrics for Thathsarani's Component

| Metric | Why Relevant | Target / Comparison |
|---|---|---|
| Exact-match SQL accuracy | Standard Text-to-SQL evaluation metric; enables direct comparability with literature baselines. | HydraLoRA ≥ standard LoRA overall |
| JOIN/aggregation-specific accuracy | Isolates the specific failure mode this project's problem statement identifies. | HydraLoRA outperforms standard LoRA on multi-join/aggregation buckets specifically |
| Trainable parameter count | Validates the claim that specialisation does not proportionally increase cost. | HydraLoRA parameter overhead small relative to per-head duplication of a full adapter |

5. Validation Strategy
Results are validated by comparing accuracy differences per complexity bucket between the two architectures, rather than relying on a single aggregate accuracy figure, consistent with accepted evaluation practice for heterogeneous-task PEFT architectures as demonstrated in the HydraLoRA literature reviewed above. Parameter-count validation confirms the efficiency claim independently of the accuracy result. Both the winning and runner-up architecture's checkpoints and evaluation logs are retained and versioned, not just the winner, since the runner-up is a required input to the quantization component's cross-check.
6. Development Approach
An iterative prototyping approach is used: the custom HydraLoRA module (routing, shared-A/multi-head-B implementation) is built incrementally and validated against a small subset before committing to full-scale training runs, given that PEFT libraries do not natively support multi-head B-matrix architectures and custom implementation carries higher risk of subtle bugs.

# 4. HIGH-LEVEL SYSTEM ARCHITECTURE


## Overview of Proposed Solution and Its Components

This component is Agent 3 in the project's multi-agent framework — the Fine-Tuned Generation agent. It receives the pruned schema context from Agent 1 (Ekanayake) and the base model from Agent 2 (Wathsala), and produces the fine-tuned SQL-generation model — both winning and runner-up architectures — that Agent 4 (Karunanayake) compresses and deploys. At inference time, this component also performs the live generation step: given the pruned schema context and the routed complexity-specialised head, it produces the candidate SQL statement that Agent 4 then executes.

## System Diagram

| Diagram note Per the proposal template's requirement, the system diagram must be black-and-white and must not be produced using AI tools. The component structure below is provided as a text-based specification only; the actual figure must be hand-drawn or created using a diagramming tool (e.g. draw.io, Visio) by the student before submission. |
|---|

Figure 1 — Thathsarani's Component Structure (to be redrawn as a black-and-white diagram)

| Element | Description |
|---|---|
| Input | Pruned schema context (from Agent 1); base model checkpoint (from Agent 2); complexity-labelled training data |
| Standard LoRA Module | Single shared adapter (A, B matrices) fine-tuned on the full dataset — control condition |
| HydraLoRA Module | Shared A matrix; multiple complexity-specialised B-matrix heads; routing via the shared complexity classifier |
| Head-Selection Sub-Agent | Live, per-query: routes to the correct complexity-specialised head (or the single shared adapter, in standard-LoRA mode) |
| Generation Sub-Agent | Live, per-query: produces the candidate SQL statement from the pruned schema context, the query, and the selected head |
| Output | Winning and runner-up fine-tuned architectures (offline, to Agent 4); candidate SQL (live, per query, to Agent 4 for execution) |


## Internal Sub-Agent Structure — Agent 3 (Fine-Tuned Generation)

Agent 3 decomposes into two live sub-agents, reflecting the two distinct decisions it makes at inference time, plus the offline architecture-comparison pipeline described above. The Head-Selection Sub-Agent consumes the complexity label produced by Agent 1's shared classifier and, when the winning architecture is HydraLoRA, routes to the correct complexity-specialised adapter head (or the single shared adapter, if standard LoRA won). The Generation Sub-Agent then produces the actual SQL statement, conditioned on the pruned schema context, the user query, and the selected head, using whichever quantized weights Agent 4 has prepared for the winning architecture. Separating these two decisions keeps the routing logic — what this component's own research question is actually about — independently inspectable from the generation step itself.

## Orchestration and Observability Harness

The four agents are coordinated by a lightweight orchestration and observability harness, rather than a general-purpose agentic framework. The pipeline's control flow is deterministic — a fixed sequence of agent calls with a single bounded retry branch — not a system in which agents autonomously choose their next action, so a full agentic framework was judged to add dependency and complexity disproportionate to what the system actually does. The harness is implemented as a FastAPI-based routing layer with three responsibilities: sequencing each agent call and passing its output to the next agent exactly as specified by the interface contracts between them; structured logging of every agent-to-agent handoff, including inputs, outputs, and timing; and executing the bounded retry branch — which loops from Agent 4's Error-Diagnosis Sub-Agent back to this component's own Generation Sub-Agent — as an explicit conditional, with each retry attempt logged individually. This harness is shared engineering infrastructure, built collaboratively across the team, and is not attributed as any individual member's research novelty.

## Overall Integration

This component depends on two upstream agents: Agent 1 (for schema context and the shared complexity classifier) and Agent 2 (for the base model). Rather than waiting idle for Agent 2's real base model, the architecture comparison runs immediately on a plain off-the-shelf placeholder base model, producing valid standalone findings without idle dependency. Once Agent 2's actual winning base model is delivered, the comparison is re-run as a shorter validation pass. This component's output — both the winning and runner-up fine-tuned architectures — is handed to Agent 4 (Karunanayake), who quantizes the winner for deployment and additionally applies her winning quantization strategy to the runner-up, as a cross-check on whether the quantization ranking she establishes is stable across fine-tuning architectures.

## Individual Responsibility Boundary

| Activity / Deliverable | My Responsibility | Shared Responsibility | Other Member |
|---|---|---|---|
| Standard LoRA baseline implementation | ✓ |  |  |
| Custom HydraLoRA module implementation | ✓ |  |  |
| Complexity-based routing logic | ✓ |  |  |
| Head-Selection and Generation sub-agents (live inference) | ✓ |  |  |
| Winning and runner-up architecture hand-off artefacts | ✓ |  |  |
| Query-complexity classifier |  |  | J.K.B. Ekanayake |
| Base model / distillation |  |  | W.A.T. Wathsala |
| Quantization strategy selection and cross-check |  |  | K.M.I.N. Karunanayake |
| Execution and error-diagnosis sub-agents |  |  | K.M.I.N. Karunanayake |
| Shared fine-tuning configuration agreement |  | ✓ |  |
| Shared evaluation dataset |  | ✓ |  |
| System orchestration and observability harness |  | ✓ |  |

# 5. USER REQUIREMENTS


## Requirements Evidence

Requirements were informed by consultation with the project supervisor during the topic assessment review and subsequent restructuring discussions, and review of parameter-efficient fine-tuning literature describing accuracy degradation patterns on complex queries. Formal requirements refinement with BI-analyst and IT infrastructure stakeholders is planned post-approval.

## Functional Requirements

- The system shall fine-tune a base SLM using standard single-adapter LoRA as a control condition.
- The system shall fine-tune the same base SLM using a custom HydraLoRA architecture with complexity-specialised heads.
- The system shall route each training and inference example to the correct HydraLoRA head using the shared complexity classifier.
- The system shall separately report exact-match accuracy, JOIN/aggregation accuracy, and trainable parameter count for both architectures, stratified by complexity bucket.
- The system shall identify and package both the winning and runner-up architecture as versioned artefacts for downstream consumption.
- The system shall perform live, per-query head selection and SQL generation at inference time, using whichever architecture and quantized weights the project's deployed configuration selects.

## Non-Functional Requirements

- Performance: fine-tuning of any tested configuration shall complete within the project's available compute/time budget on mid-range hardware.
- Accuracy: JOIN/aggregation accuracy shall be reported with statistical comparison between architectures, not a single aggregate number.
- Reliability: routing logic shall handle any complexity label without failure, including edge cases at bucket boundaries.
- Reproducibility: the shared fine-tuning configuration shall be version-controlled so results are reproducible across both architectures and both base models (distilled and native).

# 6. COMMERCIALIZATION PLAN


## Target Market and Customer Persona

This component contributes to a product targeting enterprise BI teams, data-warehousing operations, and organisations requiring on-premise deployment on modest, consumer-grade hardware rather than expensive dedicated GPU infrastructure.

## Value Proposition

Improved multi-join and aggregation accuracy directly addresses the specific failure mode enterprises cite as the reason locally-run SLM tools are currently impractical for real analytical workloads, without a proportional increase in model size or training cost.

## Revenue Model

Contributes to the overall product's on-premise licensing model; a validated HydraLoRA configuration could be positioned as a premium deployment tier if the results support it.

## Cost Estimation

Development costs are dominated by compute for training two fine-tuning architectures under controlled, identical conditions; no proprietary data licensing required given synthetic dataset generation.

## Pricing Strategy

Not independently priced; contributes to the overall product's tiered licensing and deployment-configuration options.

## Competitive Advantage

A complexity-specialised fine-tuning architecture, validated against a rigorous standard-LoRA baseline and reporting both a winner and a runner-up for downstream interaction testing, is not provided by reviewed existing local-deployment frameworks, which apply a single undifferentiated adapter regardless of query heterogeneity.

## Intellectual Property Considerations

The custom HydraLoRA module implementation, the complexity-routing logic, and the resulting complexity-stratified accuracy benchmarks are potential intellectual property arising from this component.

# 7. BUDGET AND JUSTIFICATION

This component's development requires compute resources for training two fine-tuning architectures under strictly identical conditions, plus a share of shared project costs.
Table 2 — Budget Justification

| Item | Description | Estimated Cost (LKR) |
|---|---|---|
| Cloud GPU / Compute Credits | Training compute for standard LoRA and HydraLoRA architectures, run initially on a placeholder model and re-validated on the project's actual base model. | 15,000 |
| Cloud Storage | Storage for training datasets, checkpoints, and evaluation logs for both architectures — including the runner-up, retained for downstream cross-check use. | 5,000 |
| Software Licenses / Tooling | Any tooling beyond open-source PEFT defaults required for custom HydraLoRA module development. | 3,000 |
| Technical Consultation (share) | Proportional share of project-level consultation budget for PEFT-architecture questions. | 5,000 |

Total Estimated Budget: LKR 28,000
The largest cost driver is compute for training two fine-tuning architectures under strictly identical conditions, run once on a placeholder base model and again on the project's actual winning base model, since any deviation in training budget between the compared architectures would invalidate the comparison this component's novelty depends on.

# 8. WORK BREAKDOWN STRUCTURE (WBS)

Table 3 — Task Breakdown, Timeline, and Workload Distribution

| Task | Description | Timeline |
|---|---|---|
| Requirement Analysis | Identify PEFT requirements from literature and supervisor consultation. | Month 1–2 |
| Complexity-Labelled Dataset | Build fine-tuning dataset labelled by the shared complexity taxonomy. | Month 2–3 |
| Standard LoRA Baseline | Implement and train the control-condition adapter on a placeholder base model. | Month 3–4 |
| HydraLoRA Module | Implement the custom shared-A/multi-head-B architecture and routing logic. | Month 4–6 |
| Initial Comparison (placeholder model) | Run the full LoRA-vs-HydraLoRA comparison immediately, in parallel with Agent 2's development. | Month 4–6 |
| Coordinated Re-Validation | Re-run the fine-tuning comparison on Wathsala's actual winning base model. | Month 6–7 |
| Evaluation | Measure exact-match, JOIN/aggregation accuracy, and parameter count across both architectures, stratified by complexity. | Month 7 |
| Hand-off Packaging | Package winning and runner-up architectures and evaluation artefacts for Agent 4's quantization and cross-check work. | Month 7–8 |
| Live Sub-Agent Integration | Implement Head-Selection and Generation sub-agents for the deployed pipeline. | Month 8–9 |
| Analysis & Reporting | Analyse results; prepare findings for integration and final report. | Month 8, then Month 9–12 |

# 9. GANTT CHART

Figure 2 — Thathsarani's Component Timeline (12 Months)

| Activity | M1 | M2 | M3 | M4 | M5 | M6 | M7 | M8 | M9 | M10 | M11 | M12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Requirement analysis & literature review |  |  |  |  |  |  |  |  |  |  |  |  |
| Complexity-labelled dataset construction |  |  |  |  |  |  |  |  |  |  |  |  |
| Standard LoRA baseline (placeholder model) |  |  |  |  |  |  |  |  |  |  |  |  |
| HydraLoRA module implementation |  |  |  |  |  |  |  |  |  |  |  |  |
| Initial comparison (placeholder model) |  |  |  |  |  |  |  |  |  |  |  |  |
| Coordinated re-validation (real base model) |  |  |  |  |  |  |  |  |  |  |  |  |
| Evaluation & hand-off packaging |  |  |  |  |  |  |  |  |  |  |  |  |
| Live sub-agent integration |  |  |  |  |  |  |  |  |  |  |  |  |
| System integration support |  |  |  |  |  |  |  |  |  |  |  |  |
| End-to-end feasibility testing |  |  |  |  |  |  |  |  |  |  |  |  |
| Documentation & research paper |  |  |  |  |  |  |  |  |  |  |  |  |
| Final presentation |  |  |  |  |  |  |  |  |  |  |  |  |


# 10. REFERENCES LIST

- Exploring Large Language Models for Text-to-SQL Error Correction with LoRA Fine-Tuning.
- Leveraging Large Language Model for Enhanced Text-to-SQL Parsing, 2026.
- C. Tian et al., "HydraLoRA: An Asymmetric LoRA Architecture for Efficient Fine-Tuning," 2024.

| A note on citations References were compiled from the approved topic assessment form and general knowledge of the cited works' subject matter. Exact bibliographic details (authors, venue, volume, page numbers) should be independently verified before submission, as this document was prepared without live citation-lookup access. |
|---|


# 11. APPENDICES


## Appendix 1 — Supporting Evidence and Diagrams

This appendix should include the hand-drawn or diagramming-tool-created black-and-white system diagram referenced in Section 4, along with any supporting screenshots, UI sketches, or preliminary experiment outputs relevant to this component.

## Appendix 2 — Proposal Evidence and Decision Log

To be maintained and completed throughout proposal development.

| Date | Claim / Problem | Evidence Collected | Alternatives Considered | Decision Made | Supervisor Discussion |
|---|---|---|---|---|---|
| 2026-07 | Original fine-tuning novelty (standard LoRA vs. HydraLoRA) temporarily judged to overlap with a proposed joint fine-tuning-and-quantization pillar, and ownership of it was transferred to a teammate to enable a single-owner study of whether the two decisions interact | Team discussion on consolidating fine-tuning and quantization ownership under one member; reviewed what a genuine joint-interaction study would require | Retain original fine-tuning comparison independently / transfer it to enable a joint study (adopted at the time) / take on a new OLAP-cube MDX generation pillar as a replacement (explored, then reconsidered) | Fine-tuning-architecture ownership was transferred to a teammate; an OLAP/MDX pillar was explored as a replacement for this component but not adopted | Discussed with supervisor; pending formal sign-off |
| 2026-09 | On further review, the OLAP/MDX pillar was judged to add a fifth, only loosely-integrated line of work to the project without a correspondingly strong payoff, and the team reconsidered whether a single-owner joint study was the only way to test interaction between fine-tuning architecture and quantization strategy | Reviewed whether the interaction question could be tested without one person owning both variables | Keep the merged single-owner component and drop the OLAP/MDX idea entirely (rejected — loses the benefit of independent, parallel ownership) / revert to two independent components, but preserve the interaction question via a smaller artifact-based cross-check (adopted) | Reverted fine-tuning-architecture ownership to this component; quantization strategy selection returns to being an independently-owned component (K.M.I.N. Karunanayake), which additionally runs a cross-check using this component's runner-up architecture as an artifact hand-off, preserving the interaction-testing value without requiring single-owner control over both variables. The OLAP/MDX pillar was dropped. | Discussed with supervisor; pending formal sign-off |


## Appendix 3 — AI Use Disclosure

Students should disclose any use of generative AI tools during proposal preparation. The row below is pre-filled to reflect drafting assistance received for this document; the verification and final-contribution columns must be completed honestly by the student before submission.

| AI Tool | Purpose of Use | What Was Generated / Assisted | How Output Was Verified | Final Student Contribution |
|---|---|---|---|---|
| Claude (Anthropic) | Drafting assistance and clarification of research problems and proposal structure, including reconciling this component's scope across two rounds of team restructuring (temporary consolidation, a considered OLAP/MDX pillar, and the final reversion to an independently-owned fine-tuning-architecture component with a downstream cross-check) | Helped clarify the research problem, research gap, and section structure; assisted with drafting section text, tables, and appendix content reflecting the current scope | Reviewed against the project's own individual and combined proposal documents, the approved topic-assessment scope, and the proposal template's requirements | Final interpretation, research decisions, methodology, technical choices, verification of citations and technical claims, all diagrams, and all submitted content |

The use of AI does not transfer responsibility for the submitted work. The student remains responsible for accuracy, originality, validity of references, research decisions, methodology, technical choices, interpretation of evidence, and the ability to defend every part of the proposal.
