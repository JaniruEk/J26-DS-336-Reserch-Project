J26-DS-336
Distributed Multi-Agent SLM Framework for
Privacy-Preserving Enterprise Data Intelligence
Compression Strategy Analysis for Deployable SQL-Generation SLMs: Quantization-Aware Training vs. Post-Training Quantization, with a Cross-Architecture Stability Check
Individual Project Proposal Report
K.M.I.N. Karunanayake – IT23179912
B.Sc. (Hons) Degree in Information Technology
Specialized in Data Science
Department of Information Technology
Sri Lanka Institute of Information Technology, Sri Lanka
September 2026

# DECLARATION

I declare that this is my own work, and this proposal does not knowingly incorporate any material previously submitted for a degree or diploma at any other university or higher education institution, nor does it contain any material that has been previously published or written by another person apart from where proper acknowledgment is given in the text.

| Name | Student ID | Signature |
|---|---|---|
| K.M.I.N. Karunanayake | IT23179912 |  |

The above candidate is conducting research for their undergraduate dissertation under my supervision.

| Name | Date | Signature |
|---|---|---|
| Prof. Nathali Silva |  |  |
| Mr. Theshan Senanayake |  |  |


# ABSTRACT

Deploying a fine-tuned Small Language Model for Text-to-SQL generation on consumer-grade, mid-range hardware requires compression: even a small fine-tuned model can exceed available memory at full precision, and reviewed local-deployment frameworks apply quantization using whichever method is most convenient, without systematically comparing whether the added training cost of Quantization-Aware Training (QAT) is justified over simpler, post-hoc Post-Training Quantization (PTQ) — particularly for the multi-table join and aggregation reasoning this project's problem statement identifies as the primary failure mode of compressed small models, since compression applied carelessly can introduce numerical or logical errors in aggregation functions (SUM, AVG, COUNT) that require precise accumulation across many rows. This component takes the winning fine-tuning architecture produced by the project's fine-tuning-architecture component and asks which compression strategy, QAT or PTQ, better preserves its reasoning under compression, and at what bit-level each approach's accuracy degrades sharply. A smaller, connecting check goes further than treating this as an isolated, single-model benchmark: the winning quantization strategy identified here is additionally applied to the runner-up fine-tuning architecture from the upstream component, to test whether the quantization ranking established on one architecture holds regardless of which fine-tuning method produced the input model, or whether the two decisions interact in a way that changes the deployment recommendation — a question neither the quantization literature nor the fine-tuning literature addresses in isolation, and one this project can answer precisely because the two components are independently owned but exchange artefacts rather than being combined under one owner. Evidence from edge-inference-scheduling literature establishes that model size and precision are first-order determinants of latency and memory footprint on constrained hardware, but does not address which compression method best preserves task-specific reasoning capability, nor whether that preservation depends on the fine-tuning architecture it is applied to; evidence from LLM-agent latency-reduction surveys confirms quantization method choice materially affects the accuracy/latency trade-off but reports inconsistent trade-offs across studies without examining whether upstream fine-tuning method is a hidden confound. This component also owns the live execution stage of the deployed pipeline: on a query failure, an error-diagnosis sub-agent inspects the specific error and routes control back to the fine-tuning component's generation sub-agent for a bounded number of retries. To avoid idle dependency on the fine-tuning component, quantization tooling is built immediately and an early QAT-vs-PTQ comparison runs on a self-fine-tuned placeholder model, with the full comparison re-run once the project's actual winning fine-tuned architecture is available. The research follows a Design Science methodology using an iterative, benchmark-driven development approach. Within the complete system, this component consumes the fine-tuned model (winner and runner-up) produced by the fine-tuning-architecture component and produces the final, deployment-ready quantized model that executes SQL against the local database at inference time.
Keywords: Text-to-SQL, Model Quantization, Quantization-Aware Training, Post-Training Quantization, Edge Deployment, Small Language Models

# ACKNOWLEDGEMENT

I would like to thank my research supervisor, Prof. Nathali Silva, and co-supervisor, Mr. Theshan Senanayake, for their guidance and constructive feedback throughout the development of this proposal, including through the period when this component was briefly consolidated with fine-tuning-architecture selection under my ownership to test whether the two decisions interact directly, and the subsequent decision to revert to two independently-owned components while preserving that interaction question through a smaller, artifact-based cross-check.
I am also grateful to the Sri Lanka Institute of Information Technology (SLIIT) and the Department of Information Technology for the academic resources and learning environment provided. I further acknowledge my project teammates — working on the other three components of this system — whose collaboration helped clarify how this individual component connects to the complete solution, in particular my teammate whose winning and runner-up fine-tuned architectures this component's core comparison and cross-check depend on.
Finally, I thank my family and friends for their continued encouragement throughout this academic undertaking.

# TABLE OF CONTENT

(Auto-generated in the final submitted document via Word's Table of Contents feature, referencing the Heading styles used throughout this report.)

# LIST OF TABLES

Table 1. Evaluation Metrics for Karunanayake's Component
Table 2. Budget Justification
Table 3. Task Breakdown, Timeline, and Workload Distribution
Table 4. Individual Responsibility Boundary

# LIST OF FIGURES

Figure 1. Karunanayake's Component Structure
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
| SQL | Structured Query Language |
| FK | Foreign Key |
| DDL | Data Definition Language |
| GDPR | General Data Protection Regulation |
| CCPA | California Consumer Privacy Act |
| SDG | Sustainable Development Goal |
| GGUF | GPT-Generated Unified Format (quantized model format) |
| AWQ | Activation-aware Weight Quantization |
| CEAI | Computing, Engineering and AI (research cluster) |


# LIST OF APPENDICES

Appendix 1 – Supporting Evidence and Diagrams
Appendix 2 – Proposal Evidence and Decision Log
Appendix 3 – AI Use Disclosure

# 1. INTRODUCTION


## 1.1 Background and Context

Enterprises require natural-language database querying without transmitting proprietary schema or transaction data to cloud LLMs, motivating locally hosted Small Language Models fine-tuned for Text-to-SQL generation and subsequently compressed to run responsively on mid-range consumer hardware. Once a fine-tuning architecture is chosen and trained, deploying it typically requires further compression, since even a small fine-tuned model can exceed available memory at full precision — and compression, applied carelessly, can compound this project's identified failure mode: a model that reasons correctly at full precision may make numerical or logical errors once compressed, particularly in aggregation functions that require precise accumulation across many rows.
This component investigates which compression strategy — Quantization-Aware Training or Post-Training Quantization — better preserves a fine-tuned model's reasoning under compression, and at what bit-level each degrades sharply. Critically, this component also checks whether that answer would have been different had a different fine-tuning architecture been used, since a compression strategy that behaves well for one fine-tuning architecture is not guaranteed to behave the same way for another — a possibility existing literature does not address, because existing work treats fine-tuning method and quantization method as independent choices evaluated separately. This cross-check is made possible without requiring single-owner control over both variables: the project's fine-tuning-architecture component reports both a winning and a runner-up architecture as artefacts, and this component consumes both.
This work aligns with SDG 9 (Industry, Innovation and Infrastructure) and the CEAI research cluster's focus on efficient, resource-constrained AI systems for enterprise use.

## 1.2 Literature Review

The following peer-reviewed and benchmark sources were critically evaluated for their relevance to this component:
[1] Efficient Inference Scheduling With Edge and Cloud Collaboration for LLMs Under Resource Constraints, 2026

| Aspect | Detail |
|---|---|
| Method | Survey and benchmarking of inference scheduling and resource allocation strategies for LLM deployment across edge and cloud. |
| Dataset / Context | Simulated and real edge-hardware inference workloads across varying model sizes. |
| Key Findings | Model size and precision are primary determinants of achievable latency and memory footprint on constrained hardware; compression is treated as a necessary but under-specified step. |
| Strengths | Provides quantitative grounding for the hardware constraints motivating this component. |
| Limitations | Does not compare specific compression methodologies (QAT vs. PTQ), their effect on task-specific reasoning accuracy, or whether that effect depends on the fine-tuning architecture being compressed. |

Establishes the hardware-constraint motivation for this component and confirms compression is a necessary, not optional, deployment step.
[2] Minimizing Response Latency in LLM-Based Agent Systems: A Comprehensive Survey, 2026

| Aspect | Detail |
|---|---|
| Method | Survey of latency-reduction techniques across LLM-based multi-agent systems, including model compression. |
| Dataset / Context | Cross-system benchmarking of latency-reduction techniques. |
| Key Findings | Quantization is among the most effective latency-reduction techniques, but the survey notes inconsistent accuracy trade-offs reported across studies depending on quantization method and task. |
| Strengths | Highlights that quantization method choice materially affects the accuracy/latency trade-off, not just the fact of quantization. |
| Limitations | Does not isolate SQL-specific reasoning, particularly numerical aggregation accuracy, and does not examine whether the reported inconsistency across studies is partly explained by differing upstream fine-tuning methods. |

Motivates this component's decision to isolate syntax accuracy from logical (aggregation-specific) accuracy, and motivates the cross-check as a possible explanation for the inconsistent trade-offs this survey reports.
[3] Agentic AI Security: Threats, Defenses, Evaluation, and Open Challenges, 2026

| Aspect | Detail |
|---|---|
| Method | Survey of security and reliability threats specific to agentic AI systems, including generation errors under resource constraints. |
| Dataset / Context | Cross-system review of agentic AI failure modes. |
| Key Findings | Compressed models deployed in agentic pipelines can silently produce plausible-but-incorrect outputs, a particular risk for SQL execution against live enterprise data. |
| Strengths | Provides justification for rigorous, task-specific compression evaluation before deployment, rather than relying on generic quantization benchmarks. |
| Limitations | General agentic-security framing; does not provide SQL-specific or bit-level compression guidance. |

Reinforces the importance of this component's syntax-versus-logic accuracy isolation, since a syntactically valid but logically wrong SQL query executed against live enterprise data carries real operational risk — and reinforces why the execution/error-diagnosis sub-agent this component owns matters beyond the offline benchmarking itself.
Existing Products and Systems
Reviewed local-deployment frameworks for small language models (e.g. llama.cpp-based tools) support quantization to various bit-widths and formats but do not provide task-specific guidance on which method is appropriate for a given downstream task, and none reviewed test whether their quantization recommendation is stable across different fine-tuning architectures applied to the same base model. This is the specific limitation this component addresses.

## 1.3 Research Gap

| Research Gap Statement Existing locally-deployed SLM frameworks apply quantization without systematically comparing Quantization-Aware Training against Post-Training Quantization for task-specific reasoning preservation. It is not established which method better preserves multi-join and aggregation SQL reasoning under compression, nor at what bit-level each method's accuracy degrades sharply — and neither body of literature addresses whether the answer depends on which fine-tuning architecture produced the model being compressed, a question this component answers directly by testing its winning quantization strategy against both the fine-tuning-architecture component's winning and runner-up outputs. |
|---|


# 2. OBJECTIVE


## 2.1 Main Objective

| Main Objective To implement and evaluate Quantization-Aware Training against Post-Training Quantization on the project's winning fine-tuned SQL-generation architecture, identify the bit-level inflection point at which each degrades, and test whether the resulting quantization-strategy ranking is stable when applied instead to the runner-up fine-tuning architecture. |
|---|


## 2.2 Specific Objectives

- To implement a Post-Training Quantization pipeline applied post-hoc to the winning fine-tuned model received from the fine-tuning-architecture component, across multiple bit-rates and formats (GGUF, AWQ).
- To implement a Quantization-Aware Training pipeline applied during fine-tuning of the same winning architecture, at the same bit-rates.
- To design a custom error-rate metrics suite that separately scores syntax validity and logical (JOIN/aggregation) correctness.
- To measure VRAM footprint and inference latency for every quantization configuration tested.
- To run an initial QAT-vs-PTQ comparison on a self-fine-tuned placeholder model, in parallel with the upstream component's early work, then re-validate on the project's actual winning fine-tuned model once available.
- To identify the bit-level inflection point at which each quantization strategy's accuracy degrades sharply, and identify the winning quantization strategy.
- To apply the winning quantization strategy to the runner-up fine-tuning architecture supplied by the upstream component, using the same bit-rates and evaluation protocol, and report whether the quantization-strategy ranking is stable across fine-tuning architectures or reverses.
- To implement the live execution and error-diagnosis sub-agents that run the deployed, quantized model against the local database and drive the pipeline's bounded retry loop.

# 3. METHODOLOGY

1. Research Methodology
The research question — which compression method better preserves task-specific reasoning, and whether that answer depends on the fine-tuning architecture compressed — requires controlled, quantitative benchmarking across multiple compression configurations applied to more than one underlying fine-tuned model, holding all other variables constant. A Design Science approach is appropriate because the research produces both an evaluated compression pipeline and empirical comparative findings usable for deployment decisions.

| Selected Methodology Design Science Research, incorporating a controlled quantitative benchmark comparing QAT and PTQ across multiple bit-rates and formats on the winning fine-tuned model, plus a smaller cross-check applying the winning strategy to the runner-up architecture. |
|---|

2. Data / Participants / Experimental Inputs
The winning (and, for the cross-check, runner-up) fine-tuned model produced by the project's fine-tuning-architecture component is the required experimental input; this component's core benchmarking cannot begin until that model is available, though quantization tooling (llama.cpp setup, error-rate metrics suite) is built and tested against a self-fine-tuned placeholder model in parallel. The same complexity-labelled evaluation set used across the project is reused for consistency.
3. Baseline / Benchmark
The unquantized, full-precision winning fine-tuned model serves as the accuracy ceiling baseline; PTQ at each bit-rate serves as the simpler-method baseline against which QAT's additional training cost is justified or not.
4. Evaluation Metrics
Table 1 — Evaluation Metrics for Karunanayake's Component

| Metric | Why Relevant | Target / Comparison |
|---|---|---|
| Syntax accuracy | Isolates whether the model still produces well-formed SQL after compression, independent of logical correctness. | No significant drop vs. full-precision baseline at 8-bit; measured degradation curve at 4-bit |
| Logical (JOIN/aggregation) accuracy | Isolates numerical and multi-table reasoning correctness, the project's core failure mode of concern. | QAT or PTQ, whichever preserves accuracy longer across bit-rates |
| VRAM footprint / inference latency | Confirms the compression method's practical deployability on the shared hardware budget. | Both methods must fit within the shared hardware budget |
| Cross-check ranking stability | Confirms whether the winning quantization strategy still wins when applied to the runner-up fine-tuning architecture. | Ranking holds (simpler deployment story), or reverses (a genuine interaction finding worth reporting either way) |

5. Validation Strategy
Results are validated by plotting accuracy against bit-rate for both QAT and PTQ, per complexity bucket, to identify the specific inflection point at which each method degrades — a more rigorous validation than a single point-accuracy comparison, and consistent with accepted evaluation practice in the quantization literature reviewed above. The cross-check is validated by repeating the same bit-rate-vs-accuracy plot for the runner-up architecture and comparing the two curves directly; a reversal is treated as a legitimate, reportable finding on its own, not as a failed result.
6. Development Approach
An iterative, benchmark-driven approach is used: quantization tooling and the error-rate metrics suite are built and validated on a placeholder model first, so that once the winning fine-tuned model is available from the upstream component, full-scale benchmarking — and subsequently the cross-check — can proceed without further tooling delays.

# 4. HIGH-LEVEL SYSTEM ARCHITECTURE


## Overview of Proposed Solution and Its Components

This component is Agent 4 in the project's multi-agent framework — the Quantized Execution agent. It receives the winning (and runner-up) fine-tuned model from Agent 3 (Thathsarani), and produces the final, deployment-ready quantized model that executes SQL against the local database at inference time, including the system's self-healing retry behaviour.

## System Diagram

| Diagram note Per the proposal template's requirement, the system diagram must be black-and-white and must not be produced using AI tools. The component structure below is provided as a text-based specification only; the actual figure must be hand-drawn or created using a diagramming tool (e.g. draw.io, Visio) by the student before submission. |
|---|

Figure 1 — Karunanayake's Component Structure (to be redrawn as a black-and-white diagram)

| Element | Description |
|---|---|
| Input | Winning fine-tuned model, and separately the runner-up model, from Agent 3 |
| PTQ Pipeline | Post-hoc quantization of the winning model across bit-rates (8-bit, 4-bit) and formats (GGUF, AWQ) |
| QAT Pipeline | Quantization-aware fine-tuning of the winning model at the same bit-rates |
| Cross-Check | Winning quantization strategy re-applied to the runner-up fine-tuned model from Agent 3 |
| Error-Rate Metrics Suite | Separately scores syntax validity and logical (JOIN/aggregation) correctness |
| Execution Sub-Agent | Runs the generated SQL, using the deployed quantized model, against the local database |
| Error-Diagnosis Sub-Agent | On execution failure, constructs an error-informed hint and routes control back to Agent 3's Generation Sub-Agent for a retry |
| Output | Deployment-ready quantized model, used for live SQL execution against the local database |


## Internal Sub-Agent Structure — Agent 4 (Quantized Execution)

Agent 4 decomposes into two live sub-agents, corresponding to the system's self-healing retry behaviour, plus the offline quantization-comparison pipeline described above. The Execution Sub-Agent runs the generated SQL, using the quantized model, against the local database and reports success or failure. On failure, the Error-Diagnosis Sub-Agent inspects the specific error (syntax error, invalid reference, etc.), constructs an error-informed hint, and routes control back to Agent 3's Generation Sub-Agent for a retry, up to a bounded number of attempts before surfacing the failure to the user. This decomposition makes the retry loop an explicit, inspectable control-flow branch spanning the two agents, rather than an implicit behaviour buried inside a single call.

## Orchestration and Observability Harness

The four agents are coordinated by a lightweight orchestration and observability harness, rather than a general-purpose agentic framework. The pipeline's control flow is deterministic — a fixed sequence of agent calls with a single bounded retry branch — not a system in which agents autonomously choose their next action, so a full agentic framework was judged to add dependency and complexity disproportionate to what the system actually does. The harness is implemented as a FastAPI-based routing layer with three responsibilities: sequencing each agent call and passing its output to the next agent exactly as specified by the interface contracts between them; structured logging of every agent-to-agent handoff, including inputs, outputs, and timing; and executing the bounded retry branch between this component's Error-Diagnosis Sub-Agent and Agent 3's Generation Sub-Agent as an explicit conditional, with each retry attempt logged individually. This harness is shared engineering infrastructure, built collaboratively across the team, and is not attributed as any individual member's research novelty.

## Overall Integration

This component depends on Agent 3 (for the winning and runner-up fine-tuned models). Rather than waiting idle, quantization tooling is built immediately and an initial QAT-vs-PTQ comparison runs on a self-fine-tuned placeholder model, producing valid standalone findings without idle dependency. Once Agent 3 delivers its real winning (and, later, runner-up) architecture — itself potentially re-validated against Agent 2's real base model — this component's comparison and cross-check are re-run against the real artefacts as a shorter validation pass. The final output, the deployment-ready quantized model, is the last artefact in the pipeline before live SQL execution.

## Individual Responsibility Boundary

| Activity / Deliverable | My Responsibility | Shared Responsibility | Other Member |
|---|---|---|---|
| PTQ pipeline implementation | ✓ |  |  |
| QAT pipeline implementation | ✓ |  |  |
| Error-rate metrics suite (syntax vs. logic) | ✓ |  |  |
| VRAM/latency benchmarking | ✓ |  |  |
| Cross-check against runner-up fine-tuning architecture | ✓ |  |  |
| Execution and Error-Diagnosis sub-agents (live inference) | ✓ |  |  |
| Fine-tuned model to be quantized (winner and runner-up) |  |  | K.G.Y.V. Thathsarani |
| Query-complexity classifier |  |  | J.K.B. Ekanayake |
| Base model / distillation |  |  | W.A.T. Wathsala |
| Shared evaluation dataset |  | ✓ |  |
| System orchestration and observability harness |  | ✓ |  |

# 5. USER REQUIREMENTS


## Requirements Evidence

Requirements were informed by consultation with the project supervisor during the topic assessment review and subsequent restructuring discussions, and review of edge-inference and quantization literature describing accuracy degradation patterns under compression. Formal requirements refinement with BI-analyst and IT infrastructure stakeholders is planned post-approval.

## Functional Requirements

- The system shall apply Post-Training Quantization and Quantization-Aware Training to the winning fine-tuning architecture, at 8-bit and 4-bit precision, in GGUF and AWQ formats.
- The system shall separately measure and report syntax validity and logical correctness for every quantization configuration.
- The system shall measure VRAM footprint and inference latency for every quantization configuration tested.
- The system shall additionally apply the winning quantization strategy to the runner-up fine-tuning architecture, to test ranking stability.
- The system shall execute generated SQL against the local database using the deployed quantized model.
- The system shall detect execution errors and route an error-informed hint back to the fine-tuning component's generation sub-agent for a bounded number of retries.
- The system shall expose the final winning fine-tuned-and-quantized model for deployment in the end-to-end pipeline.

## Non-Functional Requirements

- Performance: quantization of any tested configuration shall complete within the project's available compute/time budget on mid-range hardware.
- Accuracy: JOIN/aggregation accuracy shall be reported with statistical comparison between quantization strategies, not a single aggregate number.
- Reliability: the quantization pipeline shall handle model-loading and conversion failures gracefully; the retry loop shall terminate within a bounded number of attempts.
- Reproducibility: quantization configurations shall be version-controlled so results are reproducible across both the winning and runner-up fine-tuned models.

# 6. COMMERCIALIZATION PLAN


## Target Market and Customer Persona

This component contributes to a product targeting enterprise BI teams, data-warehousing operations, and organisations requiring on-premise deployment on modest, consumer-grade hardware rather than expensive dedicated GPU infrastructure.

## Value Proposition

A compression strategy validated not just on one fine-tuned model but checked for stability across two different fine-tuning architectures gives customers a deployment recommendation with a known, tested robustness margin, rather than a default that was only ever validated on whichever architecture happened to be used during development.

## Revenue Model

Contributes to the overall product's on-premise licensing model; a higher-accuracy validated quantization configuration could be positioned as a premium deployment tier if the results support it.

## Cost Estimation

Development costs are dominated by compute for two quantization strategies across multiple bit-rates and formats, plus the cross-check run against the runner-up architecture; no proprietary data licensing required given synthetic dataset generation.

## Pricing Strategy

Not independently priced; contributes to the overall product's tiered licensing and deployment-configuration options.

## Competitive Advantage

A rigorous QAT-vs-PTQ study that additionally checks whether its own conclusion is stable across fine-tuning architectures is not provided by reviewed existing local-deployment frameworks, which recommend a single quantization default without testing it against more than one upstream model.

## Intellectual Property Considerations

The PTQ and QAT pipeline implementations, the error-rate metrics suite isolating syntax from logical accuracy, the resulting bit-level degradation benchmarks, and the cross-architecture stability check methodology are potential intellectual property arising from this component.

# 7. BUDGET AND JUSTIFICATION

This component's development requires compute resources for running two quantization pipelines across multiple bit-rates and formats, plus the additional cross-check run against the runner-up architecture, plus a share of shared project costs.
Table 2 — Budget Justification

| Item | Description | Estimated Cost (LKR) |
|---|---|---|
| Cloud GPU / Compute Credits | QAT training runs at multiple bit-rates; PTQ conversion benchmarking; the cross-check run on the runner-up architecture. | 12,000 |
| Cloud Storage | Storage for multiple quantized model artefacts across bit-rates and formats, for both the winning and runner-up architecture. | 6,000 |
| Software Licenses / Tooling | Any tooling beyond open-source llama.cpp/GGUF/AWQ defaults required for benchmarking. | 3,000 |
| Testing Devices | Cross-device latency and VRAM-footprint testing on target hardware profiles. | 4,000 |
| Technical Consultation (share) | Proportional share of project-level consultation budget for quantization-specific questions. | 5,000 |

Total Estimated Budget: LKR 30,000
The largest cost driver is compute for running two quantization strategies against the winning fine-tuned model, plus the additional cross-check run against the runner-up architecture — since any deviation in quantization budget between compared configurations would invalidate the comparisons this component's novelty depends on.

# 8. WORK BREAKDOWN STRUCTURE (WBS)

Table 3 — Task Breakdown, Timeline, and Workload Distribution

| Task | Description | Timeline |
|---|---|---|
| Requirement Analysis | Identify quantization requirements from literature and supervisor consultation. | Month 3–4 |
| Quantization Tooling Setup | Build PTQ/QAT pipelines and error-rate metrics suite, in parallel with Agent 3's fine-tuning work. | Month 4–6 |
| Placeholder Quantization (early) | Run an initial QAT-vs-PTQ comparison on a self-fine-tuned placeholder model, without waiting on Agent 3's completion. | Month 5–6 |
| Core Comparison (winning architecture) | Run QAT-vs-PTQ on Agent 3's winning fine-tuned model, across bit-rates and formats. | Month 7–8 |
| Cross-Check (runner-up architecture) | Apply the winning quantization strategy to Agent 3's runner-up architecture. | Month 8 |
| Execution / Error-Diagnosis Sub-Agents | Implement the live execution and retry-loop sub-agents for the deployed pipeline. | Month 8–9 |
| Evaluation | Measure syntax/logic accuracy, VRAM, and latency across all configurations, including the cross-check. | Month 8 |
| Analysis & Reporting | Analyse results, including the cross-check comparison; prepare findings for integration and final report. | Month 8, then Month 9–12 |

Quantization tooling is built in parallel with Agent 3's fine-tuning work rather than waiting for it to complete, and the core comparison runs first on a placeholder model before re-validating against the real winning architecture, avoiding idle time between the two components' schedules.

# 9. GANTT CHART

Figure 2 — Karunanayake's Component Timeline (12 Months)

| Activity | M1 | M2 | M3 | M4 | M5 | M6 | M7 | M8 | M9 | M10 | M11 | M12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Requirement analysis & literature review |  |  |  |  |  |  |  |  |  |  |  |  |
| Quantization tooling setup |  |  |  |  |  |  |  |  |  |  |  |  |
| Placeholder quantization (early) |  |  |  |  |  |  |  |  |  |  |  |  |
| Core comparison (winning architecture) |  |  |  |  |  |  |  |  |  |  |  |  |
| Cross-check (runner-up architecture) |  |  |  |  |  |  |  |  |  |  |  |  |
| Execution / error-diagnosis sub-agents |  |  |  |  |  |  |  |  |  |  |  |  |
| Evaluation & analysis |  |  |  |  |  |  |  |  |  |  |  |  |
| System integration support |  |  |  |  |  |  |  |  |  |  |  |  |
| End-to-end feasibility testing |  |  |  |  |  |  |  |  |  |  |  |  |
| Documentation & research paper |  |  |  |  |  |  |  |  |  |  |  |  |
| Final presentation |  |  |  |  |  |  |  |  |  |  |  |  |


# 10. REFERENCES LIST

- Efficient Inference Scheduling With Edge and Cloud Collaboration for LLMs Under Resource Constraints, 2026.
- Minimizing Response Latency in LLM-Based Agent Systems: A Comprehensive Survey, 2026.
- Agentic AI Security: Threats, Defenses, Evaluation, and Open Challenges, 2026.

| A note on citations References were compiled from the approved topic assessment form and general knowledge of the cited works' subject matter. Exact bibliographic details (authors, venue, volume, page numbers) should be independently verified before submission, as this document was prepared without live citation-lookup access. |
|---|


# 11. APPENDICES


## Appendix 1 — Supporting Evidence and Diagrams

This appendix should include the hand-drawn or diagramming-tool-created black-and-white system diagram referenced in Section 4, along with any supporting screenshots, UI sketches, or preliminary experiment outputs relevant to this component.

## Appendix 2 — Proposal Evidence and Decision Log

To be maintained and completed throughout proposal development.

| Date | Claim / Problem | Evidence Collected | Alternatives Considered | Decision Made | Supervisor Discussion |
|---|---|---|---|---|---|
| 2026-06 | Original quantization pillar judged to lack independent research value by review panel | Panel review comments on component breakdown lacking research value | Simple bit-rate sweep only / adopt QAT-vs-PTQ comparative study | Adopted QAT-vs-PTQ as a controlled comparative study, not just a bit-rate sweep | Discussed with supervisor; pending formal sign-off |
| 2026-09 (first revision) | Team proposed a joint fine-tuning-and-quantization optimization approach, consolidating fine-tuning-architecture ownership (previously a teammate's component) under this component, to test whether the two decisions interact | Reviewed the project's independence principle against what a genuine interaction study would require | Full joint grid search across both variables (rejected — likely oversized for an individual project) / consolidate under one owner, run sequentially with a cross-check (adopted at the time) | Temporarily consolidated fine-tuning-architecture selection and quantization strategy under this component | Discussed with supervisor; pending formal sign-off |
| 2026-09 (second revision) | On further review, the consolidated component was judged to overload one person's scope, and the team reconsidered whether single ownership was the only way to preserve the interaction question | Reviewed whether the cross-architecture interaction question could be tested via an artifact hand-off instead of single ownership | Keep the consolidated component (rejected — overloaded scope for one individual project) / split back into two independently-owned components and lose the interaction question (rejected — forfeits a genuine, cheaply-obtainable finding) / split back into two components, with this component running a cross-check using the upstream component's runner-up architecture as an artifact (adopted) | Reverted to an independently-owned quantization-strategy component, receiving the winning and runner-up fine-tuned architectures from the fine-tuning-architecture component (K.G.Y.V. Thathsarani) as artefacts, and running the cross-check using the runner-up architecture without requiring control over how it was produced | Discussed with supervisor; pending formal sign-off |


## Appendix 3 — AI Use Disclosure

Students should disclose any use of generative AI tools during proposal preparation. The row below is pre-filled to reflect drafting assistance received for this document; the verification and final-contribution columns must be completed honestly by the student before submission.

| AI Tool | Purpose of Use | What Was Generated / Assisted | How Output Was Verified | Final Student Contribution |
|---|---|---|---|---|
| Claude (Anthropic) | Drafting assistance and clarification of research problems and proposal structure, including reconciling this component's scope across two rounds of team restructuring (temporary consolidation with fine-tuning-architecture selection, and the final reversion to an independently-owned quantization component with an artifact-based cross-check) | Helped clarify the research problem, research gap, and section structure; assisted with drafting section text, tables, and appendix content reflecting the current scope | Reviewed against the project's own individual and combined proposal documents, the approved topic-assessment scope, and the proposal template's requirements | Final interpretation, research decisions, methodology, technical choices, verification of citations and technical claims, all diagrams, and all submitted content |

The use of AI does not transfer responsibility for the submitted work. The student remains responsible for accuracy, originality, validity of references, research decisions, methodology, technical choices, interpretation of evidence, and the ability to defend every part of the proposal.
