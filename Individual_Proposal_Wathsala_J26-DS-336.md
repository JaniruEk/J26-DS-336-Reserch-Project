J26-DS-336
Distributed Multi-Agent SLM Framework for
Privacy-Preserving Enterprise Data Intelligence
Knowledge-Distilled Foundation Models for Resource-Constrained SQL Reasoning
Individual Project Proposal Report
W.A.T. Wathsala – IT23282704
B.Sc. (Hons) Degree in Information Technology
Specialized in Data Science
Department of Information Technology
Sri Lanka Institute of Information Technology, Sri Lanka
September 2026

# DECLARATION

I declare that this is my own work, and this proposal does not knowingly incorporate any material previously submitted for a degree or diploma at any other university or higher education institution, nor does it contain any material that has been previously published or written by another person apart from where proper acknowledgment is given in the text.

| Name | Student ID | Signature |
|---|---|---|
| W.A.T. Wathsala | IT23282704 |  |

The above candidate is conducting research for their undergraduate dissertation under my supervision.

| Name | Date | Signature |
|---|---|---|
| Prof. Nathali Silva |  |  |
| Mr. Theshan Senanayake |  |  |


# ABSTRACT

Off-the-shelf Small Language Models in the parameter range that fits an 8GB-VRAM hardware budget (approximately 0.5B–1.5B parameters) are generic, general-purpose models never optimised for multi-step reasoning, and fine-tuning alone cannot reliably instil reasoning capacity a base model does not already possess some trace of. Knowledge distillation — compressing a larger, stronger teacher model's behaviour into a small student model — offers an underexplored alternative path for constructing the foundation model underlying a locally-deployed Text-to-SQL system. This component investigates whether a small model built via knowledge distillation retains better multi-join and aggregation reasoning after identical fine-tuning, compared to a natively small model of the same parameter count, under the same hardware and training budget. Evidence from deep-learning and edge-inference literature establishes that model capacity constrains achievable reasoning ability, but does not directly compare distilled-versus-native small models under a controlled, identical fine-tuning regime for SQL generation specifically. The identified gap is addressed through response-based distillation: a larger teacher model (approximately 7B parameters) generates a dataset of prompt-response pairs, used to train a small student model via standard supervised fine-tuning; the distilled student is then compared against a natively small model of equal size, first on general reasoning retention, and subsequently after both are fine-tuned identically using the project's shared fine-tuning configuration. The research follows a Design Science methodology with an iterative development approach, given the exploratory nature of distillation-dataset design at this project's scope. Within the complete system, this component is the earliest-required output in the pipeline: its distilled and native base models are the required input for the fine-tuning component, and by extension for the quantization component, making this component's timely delivery a critical dependency for the rest of the team.
Keywords: Knowledge Distillation, Small Language Models, Text-to-SQL, Model Compression, Teacher-Student Training

# ACKNOWLEDGEMENT

I would like to thank my research supervisor, Prof. Nathali Silva, and co-supervisor, Mr. Theshan Senanayake, for their guidance and constructive feedback throughout the development of this proposal, particularly during the topic assessment review that shaped this component's research direction.
I am also grateful to the Sri Lanka Institute of Information Technology (SLIIT) and the Department of Information Technology for the academic resources and learning environment provided. I further acknowledge my project teammates — working on the other three components of this system — whose collaboration helped clarify how this individual component connects to the complete solution.
Finally, I thank my family and friends for their continued encouragement throughout this academic undertaking.

# TABLE OF CONTENT

(Auto-generated in the final submitted document via Word's Table of Contents feature, referencing the Heading styles used throughout this report.)

# LIST OF TABLES

Table 1. Evaluation Metrics for Wathsala's Component
Table 2. Budget Justification
Table 3. Task Breakdown, Timeline, and Workload Distribution
Table 4. Individual Responsibility Boundary

# LIST OF FIGURES

Figure 1. Wathsala's Component Structure
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
| QAT | Quantization-Aware Training |
| PTQ | Post-Training Quantization |
| VRAM | Video Random Access Memory |
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

Enterprises require natural-language database querying entirely on local infrastructure, ruling out large cloud-hosted foundation models and necessitating Small Language Models within an 8GB-VRAM hardware budget. However, off-the-shelf small models are generic, general-purpose models, and this project's problem statement identifies 'severe hallucinations on complicated, multi-table joins and large database schema' as the resulting failure mode.
Fine-tuning a small model for a narrow task such as Text-to-SQL can improve surface-level task performance, but cannot reliably instil reasoning capacity that was never present in the base model to begin with. This raises the question of whether the base model itself — before any task-specific fine-tuning — can be constructed differently to provide a stronger reasoning foundation within the same parameter budget.
Knowledge distillation, in which a larger, more capable teacher model's behaviour is compressed into a small student model, is a well-established technique in general machine learning literature, but its specific value for constructing SQL-reasoning-capable foundation models at this parameter scale, prior to task-specific fine-tuning, is underexplored. This component investigates that question directly, isolating distillation as the sole variable by fine-tuning both a distilled and a native small model identically.
This work aligns with SDG 9 (Industry, Innovation and Infrastructure) and the CEAI research cluster's focus on resource-constrained, locally deployable AI systems.

## 1.2 Literature Review

The following peer-reviewed and benchmark sources were critically evaluated for their relevance to this component:
[1] I. Goodfellow, Y. Bengio, and A. Courville, Deep Learning, MIT Press, 2016

| Aspect | Detail |
|---|---|
| Method | Foundational text covering model capacity, generalisation, and representation learning in deep neural networks. |
| Dataset / Context | N/A — foundational textbook, not an empirical study. |
| Key Findings | Model capacity fundamentally bounds the complexity of functions a network can represent and learn; smaller models have measurably reduced representational capacity. |
| Strengths | Provides the theoretical grounding for why a natively small model may structurally lack reasoning capacity that fine-tuning cannot recover. |
| Limitations | General deep-learning theory, not specific to language models or knowledge distillation. |

Provides the theoretical justification for this component's hypothesis: capacity constraints in native small models are a structural limitation that distillation, not fine-tuning, is positioned to address.
[2] LLMs and IoT: A Comprehensive Survey on Large Language Models and the Internet of Things, 2026

| Aspect | Detail |
|---|---|
| Method | Survey of techniques for deploying LLMs on resource-constrained edge and IoT hardware, including model compression and distillation. |
| Dataset / Context | Cross-study review of edge-deployment LLM techniques. |
| Key Findings | Distillation is identified as a practical technique for constructing capable small models for edge deployment, though the survey notes that most reported distillation work targets general capability rather than domain-specific reasoning tasks such as SQL generation. |
| Strengths | Confirms distillation's practical viability for edge-class hardware, directly relevant to this project's 8GB-VRAM constraint. |
| Limitations | Does not provide a controlled, task-specific (SQL) comparison between distilled and native small models under identical downstream fine-tuning. |

Confirms distillation as a technically appropriate and practically feasible approach for this component's hardware target, while identifying the specific gap (task-specific, controlled comparison) this component addresses.
[3] Agentic AI Security: Threats, Defenses, Evaluation, and Open Challenges, 2026

| Aspect | Detail |
|---|---|
| Method | Survey of reliability and security considerations for agentic AI systems, including foundation-model quality as an upstream risk factor. |
| Dataset / Context | Cross-system review of agentic AI failure modes. |
| Key Findings | Weaknesses in a foundation model's underlying reasoning propagate through the entire downstream agentic pipeline, including any fine-tuning applied afterward. |
| Strengths | Supports treating foundation-model construction as a first-class research question rather than an incidental implementation choice. |
| Limitations | General agentic-security framing; does not address distillation methodology specifically. |

Reinforces why this component's controlled distilled-versus-native comparison matters for the overall system's reliability, not just its accuracy metrics.
Existing Products and Systems
Reviewed open-source small-model deployment tools typically select an off-the-shelf small model (e.g. a published 0.5B–1.5B parameter model) without evaluating whether a distilled alternative of the same size would provide a stronger reasoning foundation for the target task. This is the specific limitation this component addresses.

## 1.3 Research Gap

| Research Gap Statement It is not established whether a small language model constructed via knowledge distillation from a larger teacher retains stronger multi-join and aggregation SQL reasoning after identical fine-tuning, compared to a natively small model of equal parameter count, under the same hardware and training budget. |
|---|


# 2. OBJECTIVE


## 2.1 Main Objective

| Main Objective To construct a small language model via knowledge distillation from a larger teacher model and evaluate it against a natively small model of equal size, under an identical fine-tuning method, isolating distillation as the sole variable affecting downstream SQL-reasoning accuracy. |
|---|


## 2.2 Specific Objectives

- To select a teacher model (approximately 7B parameters, strong at SQL/code reasoning) and a student model architecture matched in size to the project's native-model baseline.
- To generate a response-based distillation dataset of prompt-response pairs from the teacher model, covering general reasoning and SQL-adjacent schema comprehension.
- To train the student model on the teacher-generated dataset via standard supervised fine-tuning.
- To evaluate the distilled student against a natively small model of equal size on general reasoning retention, prior to any SQL-specific fine-tuning.
- To coordinate a shared fine-tuning configuration with the fine-tuning component's owner, ensuring both distilled and native models are fine-tuned identically.
- To evaluate both fine-tuned models on exact-match SQL accuracy and JOIN/aggregation accuracy, stratified by query complexity.

# 3. METHODOLOGY

1. Research Methodology
The research question — whether distillation produces a stronger foundation model than a native small model — requires controlled comparison with fine-tuning held constant as a variable, isolating model-construction method as the sole difference. A Design Science approach is appropriate because the research produces both an evaluated distillation pipeline and empirical comparative findings.

| Selected Methodology Design Science Research, incorporating a controlled quantitative comparison between a distilled and a natively small model, evaluated both before and after identical fine-tuning. |
|---|

2. Data / Participants / Experimental Inputs
A distillation dataset of approximately 1,500–3,000 prompt-response pairs is required, generated by running the teacher model over a mix of general reasoning/instruction prompts and SQL-adjacent schema-comprehension prompts — explicitly scoped as a proof-of-concept scale given the project timeline, not a production-scale distillation corpus. This dataset is generated once and does not depend on other components' outputs, allowing this component to begin immediately.
3. Baseline / Benchmark
A natively small model of equal parameter count to the distilled student, undergoing the same subsequent fine-tuning process, serves as the baseline — isolating model-construction method as the only variable under comparison.
4. Evaluation Metrics
Table — Evaluation Metrics for Wathsala's Component

| Metric | Why Relevant | Target / Comparison |
|---|---|---|
| General reasoning score (pre-fine-tuning) | Isolates distillation's effect independently of any SQL-specific fine-tuning, providing a clean early result. | Distilled student ≥ native baseline |
| Exact-match SQL accuracy (post-fine-tuning) | Standard Text-to-SQL evaluation metric; enables comparison with fine-tuning-component baselines. | Distilled-model pipeline ≥ native-model pipeline |
| JOIN/aggregation accuracy (post-fine-tuning) | Isolates the specific reasoning failure mode this project's problem statement identifies. | Distilled-model pipeline outperforms native-model pipeline, particularly on multi-join/aggregation buckets |

5. Validation Strategy
Results are validated in two stages: first, an independent pre-fine-tuning comparison establishes whether distillation alone provides a measurable advantage; second, post-fine-tuning comparison (using the identical configuration coordinated with the fine-tuning component) confirms whether that advantage persists after task-specific adaptation. This two-stage validation is more rigorous than a single post-fine-tuning comparison alone, since it separates the contribution of distillation from the contribution of fine-tuning.
6. Development Approach
An iterative development approach is used given the exploratory nature of distillation-dataset design: the teacher-prompting strategy and dataset composition are refined based on early student-training results before committing to the full-scale dataset generation and training run.

# 4. HIGH-LEVEL SYSTEM ARCHITECTURE


## Overview of Proposed Solution and Its Components

This component is Agent 2 in the project's multi-agent framework — the Foundation Model Agent, the second stage conceptually but the first stage in build order, since it produces the distilled and native base models that Agent 3 subsequently adapts for SQL generation. Unlike Agents 1, 3, and 4, this agent does not make a per-query runtime decision — its output (the base model) is built once, offline, before any query is ever answered, so it is not decomposed into internal sub-agents the way the runtime-decision-making agents are.

## System Diagram


| Diagram note Per the proposal template's requirement, the system diagram must be black-and-white and must not be produced using AI tools. The component structure below is provided as a text-based specification only; the actual figure must be hand-drawn or created using a diagramming tool (e.g. draw.io, Visio) by the student before submission. |
|---|

Figure — Wathsala's Component Structure (to be redrawn as a black-and-white diagram)

| Element | Description |
|---|---|
| Teacher Model | Approximately 7B-parameter model used for inference only, to generate the distillation dataset |
| Distillation Dataset Generation | Prompt-response pairs collected from the teacher across general reasoning and SQL-adjacent prompts |
| Student Model Training | Small model (matched in size to the native baseline) trained on teacher-generated responses |
| Native Baseline Model | An off-the-shelf small model of equal parameter count, used as the comparison baseline |
| Output | Both the distilled and native base models, handed off to Agent 3 (the fine-tuning component) |


## Orchestration and Observability Harness

The four agents are coordinated by a lightweight orchestration and observability harness, rather than a general-purpose agentic framework. The pipeline's control flow is deterministic — a fixed sequence of agent calls with a single bounded retry branch — not a system in which agents autonomously choose their next action, so a full agentic framework was judged to add dependency and complexity disproportionate to what the system actually does. The harness is implemented as a FastAPI-based routing layer with three responsibilities: sequencing each agent call and passing its output to the next agent exactly as specified by the interface contracts between them; structured logging of every agent-to-agent handoff, including inputs, outputs, and timing, so the pipeline's behaviour is inspectable rather than opaque; and executing the bounded retry branch as an explicit conditional, with each retry attempt logged individually. This harness is shared engineering infrastructure, built collaboratively across the team, and is not attributed as any individual member's research novelty. As Agent 2, this component is not invoked per query by the harness at all — its output (the trained base model) is loaded once by Agent 3 during that agent's own setup, rather than being called live within the per-query pipeline the harness orchestrates.

## Overall Integration

This component has no upstream dependency and begins work immediately, in parallel with Agent 1. Its output — both the distilled and native base models — is required before Agent 3's core training work can begin, making this component a critical-path dependency for the rest of the team. A shared fine-tuning configuration is agreed with Agent 3's owner in advance so that both base models are subsequently fine-tuned under identical conditions.

## Individual Responsibility Boundary

| Activity / Deliverable | My Responsibility | Shared Responsibility | Other Member |
|---|---|---|---|
| Teacher/student model selection | ✓ |  |  |
| Distillation dataset generation | ✓ |  |  |
| Student model training | ✓ |  |  |
| Pre-fine-tuning baseline comparison | ✓ |  |  |
| Shared fine-tuning configuration agreement |  | ✓ |  |
| Fine-tuning execution (LoRA/HydraLoRA) |  |  | K.G.Y.V. Thathsarani |
| Quantization of resulting models |  |  | K.M.I.N. Karunanayake |
| System orchestration and observability harness |  | ✓ |  |


# 5. USER REQUIREMENTS


## Requirements Evidence

Requirements were informed by consultation with the project supervisor during the topic assessment review, and review of deep-learning and edge-deployment literature describing model-capacity constraints. Formal requirements refinement is planned post-approval.

## Functional Requirements

- The system shall generate a distillation dataset of prompt-response pairs from a selected teacher model.
- The system shall train a student model of specified parameter size on the teacher-generated dataset.
- The system shall provide a natively small baseline model of equal parameter count for comparison.
- The system shall evaluate both models on general reasoning tasks prior to any SQL-specific fine-tuning.
- The system shall expose both the distilled and native base models in a format consumable by the fine-tuning component.

## Non-Functional Requirements

- Performance: distillation dataset generation and student training shall complete within the project's available compute/time budget, given this component's position as a critical-path dependency.
- Scope: the distillation dataset shall be explicitly documented as proof-of-concept scale (thousands, not tens of thousands, of examples), consistent with the project's overall scope decisions.
- Reproducibility: the teacher-prompting strategy and training configuration shall be version-controlled for reproducibility.
- Fairness of comparison: the native baseline model shall be trained/fine-tuned under conditions identical to the distilled model at every subsequent stage, to preserve the validity of the comparison.

# 6. COMMERCIALIZATION PLAN


## Target Market and Customer Persona

This component contributes to a product targeting enterprises requiring capable natural-language SQL generation within an 8GB-VRAM hardware budget, without reliance on larger, more expensive local infrastructure.

## Value Proposition

A stronger foundation model, achieved through distillation rather than simply purchasing more hardware, directly supports the product's core value proposition: capable enterprise AI on modest, customer-owned hardware.

## Revenue Model

Contributes to the overall product's on-premise licensing model; the distilled base model, if it demonstrates a clear advantage, could become the default foundation model shipped with the product.

## Cost Estimation

Development costs are dominated by compute for teacher-model inference and student-model training, the most resource-intensive stage among the project's four components.

## Pricing Strategy

Not independently priced; contributes to the overall product's on-premise licensing model.

## Competitive Advantage

A rigorously validated, task-relevant distillation pipeline — rather than an arbitrarily chosen off-the-shelf small model — is not offered by reviewed existing local-deployment frameworks, offering evidence-based foundation-model selection.

## Intellectual Property Considerations

The teacher-prompting strategy, the distillation dataset composition, and the resulting distilled model checkpoint are potential intellectual property arising from this component.

# 7. BUDGET AND JUSTIFICATION

This component's development is the most resource-intensive in the project, requiring compute for teacher-model inference (exceeding local 8GB-VRAM capacity) and student-model training, plus a share of shared project costs.
Table — Budget Justification

| Item | Description | Estimated Cost (LKR) |
|---|---|---|
| Cloud GPU / Compute Credits | Rented GPU time for teacher-model inference during distillation-dataset generation, and for student-model training. | 35,000 |
| Cloud Storage | Storage for the distillation dataset, teacher and student model checkpoints. | 8,000 |
| Software Licenses / Tooling | Any tooling beyond open-source model-training defaults required for distillation. | 3,000 |
| Technical Consultation (share) | Proportional share of project-level consultation budget for distillation-methodology questions. | 5,000 |
| Contingency | Buffer for compute overruns, given this component's position as the project's most resource-intensive and schedule-critical stage. | 10,000 |

Total Estimated Budget: LKR 61,000
This component's budget is the largest among the four individual components because teacher-model inference (approximately 7B parameters) exceeds the local 8GB-VRAM hardware budget and must be run via rented compute; the contingency allocation reflects this component's critical-path position, where delays would cascade to the fine-tuning and quantization components.

# 8. WORK BREAKDOWN STRUCTURE (WBS)

Table — Task Breakdown, Timeline, and Workload Distribution

| Task | Description | Timeline |
|---|---|---|
| Requirement Analysis | Identify distillation requirements from literature and supervisor consultation. | Month 1 |
| Teacher/Student Selection | Select and validate teacher and student model candidates against hardware constraints. | Month 1 |
| Distillation Dataset Generation | Generate prompt-response pairs from the teacher model. | Month 1–2 |
| Student Model Training | Train the student on teacher-generated data. | Month 2–3 |
| Pre-Fine-Tuning Baseline Comparison | Compare distilled student against native baseline on general reasoning. | Month 3 |
| Coordination with Fine-Tuning Component | Agree shared fine-tuning configuration; hand off both base models. | Month 3–4 |
| Post-Fine-Tuning Evaluation Support | Support evaluation once fine-tuning completes, using shared complexity taxonomy. | Month 6–7 |
| Analysis & Reporting | Prepare findings for integration and final report. | Month 7, then Month 9–12 |

This component has no upstream dependency and begins immediately in Month 1, in parallel with the retrieval component. Given its position as the critical-path dependency for the fine-tuning and quantization components, it is prioritised early rather than scheduled according to its numbering in the approved topic assessment form.

# 9. GANTT CHART

Figure — Wathsala's Component Timeline (12 Months)

| Activity | M1 | M2 | M3 | M4 | M5 | M6 | M7 | M8 | M9 | M10 | M11 | M12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Requirement analysis & literature review |  |  |  |  |  |  |  |  |  |  |  |  |
| Teacher/student model selection |  |  |  |  |  |  |  |  |  |  |  |  |
| Distillation dataset generation |  |  |  |  |  |  |  |  |  |  |  |  |
| Student model training |  |  |  |  |  |  |  |  |  |  |  |  |
| Pre-fine-tuning baseline comparison |  |  |  |  |  |  |  |  |  |  |  |  |
| Coordination & hand-off to fine-tuning component |  |  |  |  |  |  |  |  |  |  |  |  |
| Post-fine-tuning evaluation support |  |  |  |  |  |  |  |  |  |  |  |  |
| System integration support |  |  |  |  |  |  |  |  |  |  |  |  |
| End-to-end feasibility testing |  |  |  |  |  |  |  |  |  |  |  |  |
| Documentation & research paper |  |  |  |  |  |  |  |  |  |  |  |  |
| Final presentation |  |  |  |  |  |  |  |  |  |  |  |  |


# 10. REFERENCES LIST

- I. Goodfellow, Y. Bengio, and A. Courville, Deep Learning. Cambridge, MA, USA: MIT Press, 2016.
- LLMs and IoT: A Comprehensive Survey on Large Language Models and the Internet of Things, 2026.
- Agentic AI Security: Threats, Defenses, Evaluation, and Open Challenges, 2026.
- Efficient Inference Scheduling With Edge and Cloud Collaboration for LLMs Under Resource Constraints, 2026.

| A note on citations References were compiled from the approved topic assessment form and general knowledge of the cited works' subject matter. Exact bibliographic details (authors, venue, volume, page numbers) should be independently verified before submission, as this document was prepared without live citation-lookup access. |
|---|


# 11. APPENDICES


## Appendix 1 — Supporting Evidence and Diagrams

This appendix should include the hand-drawn or diagramming-tool-created black-and-white system diagram referenced in Section 4, along with any supporting screenshots, UI sketches, or preliminary experiment outputs relevant to this component.

## Appendix 2 — Proposal Evidence and Decision Log

To be maintained and completed throughout proposal development. An illustrative example row is provided; replace with the actual log.

| Date | Claim / Problem | Evidence Collected | Alternatives Considered | Decision Made | Supervisor Discussion |
|---|---|---|---|---|---|
| 2026-07 | Original orchestration/MLOps pillar judged to lack independent research value by review panel | Panel review comments on component breakdown lacking research value | Retain orchestration focus / pivot to knowledge-distillation model construction | Adopted knowledge distillation vs. native model as the new comparative research focus | Discussed with supervisor; pending formal sign-off |


## Appendix 3 — AI Use Disclosure

Students should disclose any use of generative AI tools during proposal preparation. The row below is pre-filled to reflect drafting assistance received for this document; the verification and final-contribution columns must be completed honestly by the student before submission.

| AI Tool | Purpose of Use | What Was Generated / Assisted | How Output Was Verified | Final Student Contribution |
|---|---|---|---|---|
| Claude (Anthropic) | Drafting and structuring the proposal document against the provided template | Section text, tables, and content organisation based on the student's project context and prior research discussions | [To be completed by student] | [To be completed by student] |

The use of AI does not transfer responsibility for the submitted work. The student remains responsible for accuracy, originality, validity of references, research decisions, methodology, technical choices, interpretation of evidence, and the ability to defend every part of the proposal.
