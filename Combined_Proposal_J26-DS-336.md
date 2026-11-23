J26-DS-336
Distributed Multi-Agent SLM Framework for
Privacy-Preserving Enterprise Data Intelligence
Project Proposal Report
J.K.B. Ekanayake – IT23199262
K.G.Y.V. Thathsarani – IT23404250
K.M.I.N. Karunanayake – IT23179912
W.A.T. Wathsala – IT23282704
B.Sc. (Hons) Degree in Information Technology
Specialized in Data Science
Department of Information Technology
Sri Lanka Institute of Information Technology, Sri Lanka
September 2026

# DECLARATION

We declare that this is our own work, and this proposal does not knowingly incorporate any material previously submitted for a degree or diploma at any other university or higher education institution, nor does it contain any material that has been previously published or written by another person apart from where proper acknowledgment is given in the text.

| Name | Student ID | Signature |
|---|---|---|
| J.K.B. Ekanayake | IT23199262 |  |
| K.G.Y.V. Thathsarani | IT23404250 |  |
| K.M.I.N. Karunanayake | IT23179912 |  |
| W.A.T. Wathsala | IT23282704 |  |

The above candidates are conducting research for their undergraduate dissertation under our supervision.

| Name | Date | Signature |
|---|---|---|
| Prof. Nathali Silva |  |  |
| Mr. Theshan Senanayake |  |  |


# ABSTRACT

Enterprises need natural-language access to internal databases and data warehouses, but sending proprietary schemas and customer data into a third-party generative-AI system is restricted at most such organisations — by internal AI-governance and vendor-risk policy, reinforced by data-protection regulation such as GDPR and CCPA — while locally hosted Small Language Models (SLMs) hallucinate severely on complex multi-table joins and aggregations — the real-world problem this project addresses. The individual research problem is that no existing framework simultaneously investigates schema context width, fine-tuning architecture, compression strategy, and foundation-model construction as a coordinated set of independent, hardware-constrained comparisons feeding into one deployable system. Key evidence for this gap comes from Text-to-SQL retrieval, PEFT, edge-inference, and model-compression literature reviewed in Section 1.2, each of which addresses one dimension of the problem in isolation.

The identified gap spans four dimensions: (1) schema retrieval gives every question the same amount of schema, although the best amount can depend on the question and on the small model that uses it; (2) standard fine-tuning applies one undifferentiated adapter across heterogeneous query complexity; (3) quantization is applied without systematically comparing training-time versus post-hoc compression for reasoning preservation; and (4) foundation-model construction relies on off-the-shelf small models never optimised for multi-step reasoning.

This project's proposed research contribution is a Distributed Multi-Agent SLM Framework organised as four independently evaluated, controlled comparisons: a per-question schema-width selector, learned from the small model's own execution results, versus fixed schema widths; an asymmetric multi-head LoRA (HydraLoRA) architecture versus standard LoRA, specialised by query complexity; Quantization-Aware Training versus Post-Training Quantization; and a knowledge-distilled base model versus a natively small model, evaluated under identical fine-tuning. The fine-tuning-architecture and quantization-strategy comparisons connect through a single, lightweight cross-check — the winning quantization strategy is additionally applied to the runner-up fine-tuning architecture — testing whether the two decisions interact without requiring either component to own or depend on the other's internal implementation. The proposed product component is an on-premise, natural-language-to-SQL query engine for regulated enterprises.

The research follows a Design Science methodology with an iterative, prototype-driven development approach. Evaluation uses token efficiency, schema-linking precision/recall, exact-match and JOIN/aggregation-specific SQL accuracy, and VRAM/latency footprint, stratified by a shared query-complexity taxonomy (simple, single-join, multi-join, aggregation) across all four studies. Following independent evaluation, the best-performing configuration from each study is assembled into an end-to-end pipeline, and this integration is validated as a feasibility demonstration — not an additional novelty claim — confirming that regulation-compliant, fully local natural-language database querying is achievable on mid-range hardware without sacrificing multi-table reasoning accuracy.

**Keywords:** Text-to-SQL, Small Language Models, Retrieval-Augmented Generation, Parameter-Efficient Fine-Tuning, Knowledge Distillation, Model Quantization, Privacy-Preserving AI

# ACKNOWLEDGEMENT

We would like to thank our research supervisor, Prof. Nathali Silva, and co-supervisor, Mr. Theshan Senanayake, for their invaluable guidance and constructive feedback throughout the development of this proposal, particularly during the topic assessment review that shaped this project's four independently defensible research contributions.

We also extend our gratitude to the Sri Lanka Institute of Information Technology (SLIIT) and the Department of Information Technology for the academic resources and learning environment provided throughout this research.

Finally, we thank our families and friends for their continued encouragement throughout this academic undertaking.

# TABLE OF CONTENT

(Auto-generated in the final submitted document via Word's Table of Contents feature, referencing the Heading styles used throughout this report.)

# LIST OF TABLES

- Table 1. Evaluation Metrics per Pillar (4 tables)
- Table 2. Component Ownership Matrix
- Table 3. Functional Requirements
- Table 4. Budget Justification (per member and combined)
- Table 5. Work Distribution per Member
- Table 6. List of Abbreviations

# LIST OF FIGURES

- Figure 1. High-Level System Architecture
- Figure 2. Work Breakdown Structure
- Figure 3. Gantt Chart — 12-Month Combined Timeline

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
| GGUF | GPT-Generated Unified Format (quantized model format) |
| AWQ | Activation-aware Weight Quantization |
| VRAM | Video Random Access Memory |
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

Modern organisations increasingly need data-intelligence tools capable of executing natural-language queries against sophisticated internal data systems, including data warehouses, OLTP databases, and multidimensional data cubes. The intended users — enterprise data analysts, BI managers, and database administrators — require immediate insight into their data, but sending database schemas and transaction logs into a cloud-hosted generative-AI system is restricted at most such organisations. This is not a claim that third-party data sharing is prohibited outright — regulated enterprises routinely share data with established third parties (core-banking vendors, payment processors, cloud hosting) under audited contracts. Rather, a generative-AI vendor is a newer, less-precedented category — open questions around prompt logging, retention, and training-data use — that internal AI-governance and vendor-risk policy, reinforced by data-protection regulation such as GDPR and CCPA, currently keeps most such organisations from sending live, sensitive data to. At the same time, hosting large foundation models locally is infeasible for most organisations due to high hardware requirements.

Attempting to solve this with localized Small Language Models introduces a distinct technical challenge: off-the-shelf SLMs suffer substantial hallucination when reasoning over complicated, multi-table joins and large database schemas. Organisations are consequently placed in a difficult position — investing heavily in local AI infrastructure, or accepting an AI-governance risk most such organisations are not willing to take with live, sensitive data. This is directly relevant to the Corporate Business Intelligence, FinTech, and Data Warehousing verticals, and aligns with SDG 9 (Industry, Innovation and Infrastructure) and the CEAI research cluster's focus on resource-constrained, applied AI systems.

This project addresses the problem through a Distributed Multi-Agent SLM Framework, in which four independently investigated components — schema retrieval, fine-tuning architecture, compression strategy, and foundation-model construction — are each evaluated as a standalone, controlled research question, before being combined into one working system that performs natural-language-to-SQL translation entirely on-premise or on an enterprise edge server, on hardware no more powerful than a single mid-range GPU.

## 1.2 Literature Review

The following peer-reviewed and benchmark sources were critically evaluated for their relevance to this project's four components:

### Ekanayake's Component — Adaptive Schema Context Width for Small Local Text-to-SQL Models

> **Revision note:** Revised 23 November 2026: research claim changed from column-level pruning to adaptive schema context width (approved 21 November 2026). Results: reports/agent1_width/README.md.

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
| Strengths | Provides quantitative grounding for why context-window efficiency matters on edge-class GPUs. |
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

**[7] BudgetSchemaBench (arXiv 2610.00092) and LitE-SQL (arXiv 2510.09014)**

| Aspect | Detail |
|---|---|
| Method | BudgetSchemaBench: Text-to-SQL accuracy at fixed schema budgets. LitE-SQL: vector-based schema linking at a fixed top-k, with execution-guided SQL correction. |
| Dataset / Context | Text-to-SQL benchmarks; API-scale models (BudgetSchemaBench); models from 1.5B to 7B parameters (LitE-SQL). |
| Key Findings | Accuracy depends on the schema budget; LitE-SQL reports that smaller models are less robust to irrelevant columns. |
| Strengths | Direct prior studies of accuracy against schema amount, and evidence for the distraction effect in small models. |
| Limitations | Fixed budgets or a fixed k for all questions; BudgetSchemaBench has no small open models and no split by model size or query difficulty. |

Shows that accuracy-against-schema-amount studies are not new. This component adds a per-question choice and the split by small model size and query complexity.

**Further related work.** CHESS, Adaptive-Elbow (arXiv 2611.20979, a training-free per-question cut) and DecoSearch (arXiv 2606.17821, selection by an LLM) also vary the amount of schema per question. EllieSQL (arXiv 2503.22402) routes each question to "the most efficient capable" pipeline, the same idea as this component's label (the cheapest option that succeeds), applied to pipelines. RSL-SQL chooses between a pruned and a full schema after two generations. AutoLink (arXiv 2511.17190) widens the schema on verification errors before generation. The bibliographic details of these November 2026 additions are to be verified before submission.

### Thathsarani's Component — Complexity-Specialised Parameter-Efficient Fine-Tuning for SQL Reasoning (Standard LoRA vs. HydraLoRA)

**[1] Exploring Large Language Models for Text-to-SQL Error Correction with LoRA Fine-Tuning**

| Aspect | Detail |
|---|---|
| Method | LoRA-based fine-tuning applied to correct erroneous SQL generated by a base LLM. |
| Dataset / Context | Text-to-SQL benchmark with injected and naturally-occurring generation errors. |
| Key Findings | LoRA fine-tuning meaningfully reduces syntax and simple logic errors in generated SQL. |
| Strengths | Demonstrates LoRA's practical effectiveness for SQL-specific adaptation at low parameter cost. |
| Limitations | Uses a single, undifferentiated LoRA adapter; does not investigate whether adapter specialisation by query type improves results further. |

Establishes standard LoRA as a valid, literature-supported baseline for this component's comparison.

**[2] Leveraging Large Language Model for Enhanced Text-to-SQL Parsing (2026)**

| Aspect | Detail |
|---|---|
| Method | Fine-tuning and prompt-engineering techniques to improve SQL parsing accuracy on complex schemas. |
| Dataset / Context | Cross-domain Text-to-SQL benchmarks including multi-table join scenarios. |
| Key Findings | Accuracy degrades disproportionately on multi-table joins and aggregation queries compared to simple lookups. |
| Strengths | Provides direct evidence that query complexity, not just schema size, drives accuracy degradation. |
| Limitations | Does not propose an architecture-level fix targeting this specific degradation pattern. |

Directly motivates this component's hypothesis that complexity-aware adapter specialisation, rather than a single generic adapter, should specifically target the multi-join/aggregation accuracy gap.

**[3] HydraLoRA: An Asymmetric LoRA Architecture for Efficient Fine-Tuning, 2024**

| Aspect | Detail |
|---|---|
| Method | Asymmetric multi-head LoRA: a shared down-projection matrix (A) with multiple task-specialised up-projection heads (B), combined via a learned router. |
| Dataset / Context | Heterogeneous multi-task instruction-tuning benchmarks. |
| Key Findings | Multi-head specialisation improves performance on heterogeneous tasks over single-adapter LoRA without a proportional parameter increase, since only the smaller B matrices are duplicated. |
| Strengths | Provides the core architectural mechanism this component adapts; demonstrates the parameter-efficiency claim empirically in a different domain. |
| Limitations | Applied to distinct multi-domain tasks, not to within-domain complexity variation such as SQL query difficulty; uses unsupervised auto-clustering to route inputs to heads, which is not evaluated for a single, well-definable task-complexity taxonomy. |

This component adapts HydraLoRA's shared-A/multi-head-B architecture specifically to SQL query-complexity buckets, using hard-coded routing via a shared complexity classifier instead of unsupervised auto-clustering, as a deliberate scope decision.

### Karunanayake's Component — Compression Strategy Analysis for Deployable SQL-Generation SLMs (Quantization-Aware Training vs. Post-Training Quantization)

**[1] Efficient Inference Scheduling With Edge and Cloud Collaboration for LLMs Under Resource Constraints, 2026**

| Aspect | Detail |
|---|---|
| Method | Survey and benchmarking of inference scheduling and resource allocation strategies for LLM deployment across edge and cloud. |
| Dataset / Context | Simulated and real edge-hardware inference workloads across varying model sizes. |
| Key Findings | Model size and precision are primary determinants of achievable latency and memory footprint on constrained hardware; compression is treated as a necessary but under-specified step. |
| Strengths | Provides quantitative grounding for the hardware constraints motivating this component. |
| Limitations | Does not compare specific compression methodologies (QAT vs. PTQ) or their effect on task-specific reasoning accuracy. |

Establishes the hardware-constraint motivation for this component and confirms compression is a necessary, not optional, deployment step.

**[2] Minimizing Response Latency in LLM-Based Agent Systems: A Comprehensive Survey, 2026**

| Aspect | Detail |
|---|---|
| Method | Survey of latency-reduction techniques across LLM-based multi-agent systems, including model compression. |
| Dataset / Context | Cross-system benchmarking of latency-reduction techniques. |
| Key Findings | Quantization is among the most effective latency-reduction techniques, but the survey notes inconsistent accuracy trade-offs reported across studies depending on quantization method and task. |
| Strengths | Highlights that quantization method choice materially affects the accuracy/latency trade-off, not just the fact of quantization. |
| Limitations | Does not isolate SQL-specific reasoning, particularly numerical aggregation accuracy, as an evaluation dimension. |

Motivates this component's decision to isolate syntax accuracy from logical (aggregation-specific) accuracy, rather than reporting a single blended accuracy figure.

**[3] Agentic AI Security: Threats, Defenses, Evaluation, and Open Challenges, 2026**

| Aspect | Detail |
|---|---|
| Method | Survey of security and reliability threats specific to agentic AI systems, including generation errors under resource constraints. |
| Dataset / Context | Cross-system review of agentic AI failure modes. |
| Key Findings | Compressed models deployed in agentic pipelines can silently produce plausible-but-incorrect outputs, a particular risk for SQL execution against live enterprise data. |
| Strengths | Provides justification for rigorous, task-specific compression evaluation before deployment, rather than relying on generic quantization benchmarks. |
| Limitations | General agentic-security framing; does not provide SQL-specific or bit-level compression guidance. |

Reinforces the importance of this component's syntax-versus-logic accuracy isolation, since a syntactically valid but logically wrong SQL query executed against live enterprise data carries real operational risk.

### Wathsala's Component — Knowledge-Distilled Foundation Models for Resource-Constrained SQL Reasoning

**[1] I. Goodfellow, Y. Bengio, and A. Courville, Deep Learning, MIT Press, 2016**

| Aspect | Detail |
|---|---|
| Method | Foundational text covering model capacity, generalisation, and representation learning in deep neural networks. |
| Dataset / Context | N/A — foundational textbook, not an empirical study. |
| Key Findings | Model capacity fundamentally bounds the complexity of functions a network can represent and learn; smaller models have measurably reduced representational capacity. |
| Strengths | Provides the theoretical grounding for why a natively small model may structurally lack reasoning capacity that fine-tuning cannot recover. |
| Limitations | General deep-learning theory, not specific to language models or knowledge distillation. |

Provides the theoretical justification for this component's hypothesis: capacity constraints in native small models are a structural limitation that distillation, not fine-tuning, is positioned to address.

**[2] LLMs and IoT: A Comprehensive Survey on Large Language Models and the Internet of Things, 2026**

| Aspect | Detail |
|---|---|
| Method | Survey of techniques for deploying LLMs on resource-constrained edge and IoT hardware, including model compression and distillation. |
| Dataset / Context | Cross-study review of edge-deployment LLM techniques. |
| Key Findings | Distillation is identified as a practical technique for constructing capable small models for edge deployment, though the survey notes that most reported distillation work targets general capability rather than domain-specific reasoning tasks such as SQL generation. |
| Strengths | Confirms distillation's practical viability for edge-class hardware, directly relevant to this project's mid-range hardware target. |
| Limitations | Does not provide a controlled, task-specific (SQL) comparison between distilled and native small models under identical downstream fine-tuning. |

Confirms distillation as a technically appropriate and practically feasible approach for this component's hardware target, while identifying the specific gap (task-specific, controlled comparison) this component addresses.

**[3] Agentic AI Security: Threats, Defenses, Evaluation, and Open Challenges, 2026**

| Aspect | Detail |
|---|---|
| Method | Survey of reliability and security considerations for agentic AI systems, including foundation-model quality as an upstream risk factor. |
| Dataset / Context | Cross-system review of agentic AI failure modes. |
| Key Findings | Weaknesses in a foundation model's underlying reasoning propagate through the entire downstream agentic pipeline, including any fine-tuning applied afterward. |
| Strengths | Supports treating foundation-model construction as a first-class research question rather than an incidental implementation choice. |
| Limitations | General agentic-security framing; does not address distillation methodology specifically. |

Reinforces why this component's controlled distilled-versus-native comparison matters for the overall system's reliability, not just its accuracy metrics.

### Existing Products and Systems

**Ekanayake:** Cloud-hosted Text-to-SQL copilots (e.g. general-purpose LLM-based BI assistants) achieve high accuracy but require transmitting schema and query data into a third-party generative-AI vendor — a data flow most regulated enterprises' internal AI-governance policy does not currently permit for live, sensitive data, regardless of the vendor's contractual terms. Locally-run open-source Text-to-SQL tools typically perform table-level schema linking via either keyword matching or embedding similarity, then inject the full DDL of every retrieved table into the prompt, with one fixed setting for all questions. Research systems already vary the amount of schema per question (CHESS, QCMA-SQL, AttnLink, Adaptive-Elbow, DecoSearch), and MATS (arXiv 2512.18622) already combines several small language models in one Text-to-SQL pipeline. They set the amount of schema with a fixed rule, gold-schema labels, model confidence or a large model. To our knowledge, as of November 2026, none of the reviewed systems learns the width from the execution results of the small local model that will use it, and chooses it once, before generation; this narrow combination is the limitation this component addresses.

**Thathsarani:** Reviewed open-source Text-to-SQL fine-tuning pipelines uniformly apply a single LoRA (or QLoRA) adapter across the full training set. None of the locally-run tools reviewed implement task-heterogeneity-aware adapter architectures specifically for SQL query complexity; this is the specific limitation this component addresses.

**Karunanayake:** Reviewed local-deployment frameworks for small language models (e.g. llama.cpp-based tools) support quantization to various bit-widths and formats (GGUF, AWQ) but do not provide task-specific guidance on which method (QAT or PTQ) is appropriate for a given downstream task, nor do they isolate syntax from logical accuracy in their reported benchmarks. This is the specific limitation this component addresses.

**Wathsala:** Reviewed open-source small-model deployment tools typically select an off-the-shelf small model (e.g. a published 0.5B–1.5B parameter model) without evaluating whether a distilled alternative of the same size would provide a stronger reasoning foundation for the target task. This is the specific limitation this component addresses.

## 1.3 Research Gap

Four specific, complementary gaps motivate this project's four research components, sharing one root cause: the fixed mid-range hardware budget that rules out simply using bigger, cloud-hosted models.

> **Ekanayake — Research Gap Statement**
> Per-question schema selection exists, and accuracy against schema amount has been measured for API-scale models and for fixed budgets on 1.5B–7B models. It is not yet established, for small local Text-to-SQL models, (a) how the best schema width changes with model size and query complexity, and (b) whether a selector that chooses one of several nested widths for each question before generation, trained on labels from the deployed model's own execution results, gives higher execution accuracy than the best fixed width and a simple complexity rule. Research question: for a given small local SQL model, how much schema (width) should each question get?

> **Thathsarani — Research Gap Statement**
> Standard LoRA fine-tuning applies one shared low-rank adapter across the full heterogeneity of Text-to-SQL query complexity; it is not established whether an asymmetric multi-head LoRA architecture, specialised by query-complexity bucket, improves multi-join and aggregation reasoning accuracy over standard LoRA without a proportional increase in trainable parameters.

> **Karunanayake — Research Gap Statement**
> Existing locally-deployed SLM frameworks apply quantization without systematically comparing Quantization-Aware Training against Post-Training Quantization for task-specific reasoning preservation; it is not established which method better preserves multi-join and aggregation SQL reasoning under compression, nor at what bit-level each method's accuracy degrades sharply.

> **Wathsala — Research Gap Statement**
> It is not established whether a small language model constructed via knowledge distillation from a larger teacher retains stronger multi-join and aggregation SQL reasoning after identical fine-tuning, compared to a natively small model of equal parameter count, under the same hardware and training budget.


# 2. OBJECTIVE

## 2.1 Main Objective

> **Main Objective**
> To design, implement, and evaluate a fully localized, privacy-preserving distributed framework that utilises a coordinated network of specialised, quantized Small Language Models (SLMs) to execute accurate natural-language queries against complex enterprise relational databases on mid-tier local hardware, without risking regulatory data leaks.

## 2.2 Specific Objectives

Each member's specific objectives are designed as an independent, controlled comparison, sharing a common query-complexity taxonomy (simple / single-join / multi-join / aggregation) and the same mid-range hardware budget.

### J.K.B. Ekanayake — Adaptive Schema Context Width for Small Local Text-to-SQL Models

- To implement a dynamic schema-reflection engine that automatically extracts table structures and foreign-key relationships from a live relational database without hardcoded schema definitions.
- To implement four retrieval configurations — semantic-only, structural-only, hybrid, and hybrid with column-level pruning — as switchable modes of a single retrieval engine, and to use them, with the full schema, as four nested widths: W1 (anchor table only), W2 (anchor and related tables, columns pruned), W3 (the same tables, all columns) and W4 (full schema).
- To implement the column-level relevance-ranking mechanism that builds width W2.
- To build a query-complexity classification module (simple, single-join, multi-join, aggregation) shared across the project's evaluation pipeline.
- To measure execution accuracy and token count at each width W1–W4 for Qwen2.5-Instruct 0.5B, 1.5B and 3B (FP16) on the full non-nested Spider development set, Chinook and Northwind, stratified by query complexity (the distraction curves; tests H1 and H2), before PP2.
- To train a width selector on 1,200 Spider training questions, each labelled with the narrowest width whose SQL returns the correct rows, and to compare it with the fixed widths, the complexity rule, the adaptive elbow, the complexity-only selector, retry with a wider width and the oracle, using paired bootstrap CIs and exact McNemar tests (tests H3), before PP2.
- To test whether a selector trained for one model size is the best selector for another model size (tests H4), before PP2.
- To keep Agent 1's retrieval time, including the selector, under 500 ms per question, and to repeat the width study with Agent 3's fine-tuned model before the final submission.

### K.G.Y.V. Thathsarani — Complexity-Specialised Parameter-Efficient Fine-Tuning for SQL Reasoning (Standard LoRA vs. HydraLoRA)

- To construct a Text-to-SQL fine-tuning dataset with each example labelled by query complexity, using the project's shared complexity classifier.
- To implement a standard single-adapter LoRA fine-tuning pipeline using the PEFT library as the control condition.
- To implement a custom HydraLoRA module with a shared down-projection matrix and complexity-specialised up-projection heads.
- To implement hard-coded, classifier-based routing of training and inference examples to the appropriate HydraLoRA head.
- To train both architectures under identical conditions — same base model, dataset, epochs, and hardware budget.
- To evaluate both architectures on exact-match accuracy, JOIN/aggregation-specific accuracy, and trainable parameter count, stratified by complexity bucket.
- To report both the winning and runner-up architecture as versioned artefacts, so the quantization-strategy component can test whether its own findings hold regardless of which fine-tuning architecture produced the model being compressed.

### K.M.I.N. Karunanayake — Compression Strategy Analysis for Deployable SQL-Generation SLMs (Quantization-Aware Training vs. Post-Training Quantization)

- To implement a Post-Training Quantization pipeline applied post-hoc to the project's fine-tuned model across multiple bit-rates and formats (GGUF, AWQ).
- To implement a Quantization-Aware Training pipeline applied during the fine-tuning process at the same bit-rates.
- To design a custom error-rate metrics suite that separately scores syntax validity and logical (JOIN/aggregation) correctness.
- To measure VRAM footprint and inference latency for every quantization configuration tested.
- To evaluate both quantization strategies stratified by the shared query-complexity taxonomy.
- To identify the bit-level inflection point at which each quantization strategy's accuracy degrades sharply, and identify the winning quantization strategy.
- To apply the winning quantization strategy to the runner-up fine-tuning architecture supplied by the fine-tuning component, and report whether the resulting ranking is stable across fine-tuning architectures or reverses.

### W.A.T. Wathsala — Knowledge-Distilled Foundation Models for Resource-Constrained SQL Reasoning

- To select a teacher model (approximately 7B parameters, strong at SQL/code reasoning) and a student model architecture matched in size to the project's native-model baseline.
- To generate a response-based distillation dataset of prompt-response pairs from the teacher model, covering general reasoning and SQL-adjacent schema comprehension.
- To train the student model on the teacher-generated dataset via standard supervised fine-tuning.
- To evaluate the distilled student against a natively small model of equal size on general reasoning retention, prior to any SQL-specific fine-tuning.
- To coordinate a shared fine-tuning configuration with the fine-tuning component's owner, ensuring both distilled and native models are fine-tuned identically.
- To evaluate both fine-tuned models on exact-match SQL accuracy and JOIN/aggregation accuracy, stratified by query complexity.

# 3. METHODOLOGY

This study follows a Design Science research methodology across all four components, with emphasis on the design, implementation, and controlled empirical evaluation of a distributed multi-agent SLM system. Each member's specific methodology is detailed below, followed by the shared experimental infrastructure and integration approach.

### Shared Experimental Infrastructure

- Hardware constraint: all experiments are conducted and evaluated against a single mid-range GPU budget, representing realistic mid-tier enterprise edge hardware.
- Database proxies: the Chinook relational database serves as the primary enterprise-database proxy; the Spider dataset and TPC-H decision-support benchmark provide additional, more complex schema structures.
- Query-complexity taxonomy: every natural-language/SQL pair used in evaluation is classified as simple, single-join, multi-join, or aggregation-heavy, shared across all four components so results can be compared directly.

## J.K.B. Ekanayake's Methodology — Adaptive Schema Context Width for Small Local Text-to-SQL Models

**1. Research Methodology**
The research question — for a given small local SQL model, how much schema (width) each question should get — is best answered through controlled, quantitative experimentation, since the outcome variables (execution accuracy, token count) are directly measurable and width can be isolated as the single controlled variable: for every question, the same model generates SQL once at each of four nested widths (W1 anchor table only; W2 anchor and related tables, columns pruned; W3 the same tables, all columns; W4 full schema), with the same prompt and greedy decoding. A Design Science approach is appropriate because the research produces evaluated artefacts (the retrieval engine and the width selector) alongside empirical findings (the distraction curves). The hypotheses are:
- **H1.** The best fixed width becomes narrower when the model becomes smaller. Primary test (pre-registered before the runs of other model sizes): with D(model) = accuracy(W4) − accuracy(W2), the difference D(3B) − D(0.5B) is greater than 0, and its 95% paired bootstrap CI excludes 0.
- **H2.** The best width is different for each complexity label.
- **H3.** The learned selector beats every fixed width and the complexity rule (threshold p < 0.0125).
- **H4.** A selector trained for one model is not the best selector for a different model (exact McNemar; supported if p < 0.025 for at least one of the two other sizes).

If H3 is not supported, H1 and H2 (the distraction curves) are the main finding.

> **Selected Methodology**
> Design Science Research, incorporating a controlled quantitative experiment that compares four nested schema widths and several width-selection methods for small local SQL models of different sizes.

**2. Data / Participants / Experimental Inputs**
The test set is all non-nested questions of the Spider development set, plus the Chinook and Northwind question sets; questions whose gold SQL returns no rows are skipped. The selector trains on 1,200 Spider training questions from databases that are not in the test set; every split is by database. For each question and model, the label is the narrowest width whose SQL returns the gold rows; a question with no correct width is not used for training. The selector's inputs are known before the SQL model runs: the four complexity probabilities, the top-3 table similarities and their gap, schema size, schema features, the token count at each width, and question length. The models are Qwen2.5-Instruct 0.5B, 1.5B and 3B at FP16, with one prompt and greedy decoding; Qwen2.5-1.5B-Instruct is the project's shared base model. A 7B model is not included, because it does not fit at FP16 on the mid-range hardware used. Agent 3's fine-tuned model replaces the base model in a later re-run.

**3. Baseline / Benchmark**
Every method is compared with the best fixed width. The baselines are the fixed widths W1–W4 (the existing semantic-only, hybrid+pruning and hybrid retrieval modes, plus the full schema); a complexity rule (W1 if P(simple) ≥ 0.5, else W2); an adaptive elbow, a training-free per-question cut (simplified from Adaptive-Elbow); the learned selector with complexity features only (the Adaptive-RAG design); retry with the next wider width after SQL that fails to run (an ablation, close to AutoLink, not a claim); and the oracle, the narrowest correct width for each question (upper limit).

**4. Evaluation Metrics**

*Table — Evaluation Metrics for Ekanayake's Component*

| Metric | Why Relevant | Target / Comparison |
|---|---|---|
| Execution accuracy (strict match of result rows against the gold SQL) | Measures end-task success at each width and for each selection method. | Selector > best fixed width and complexity rule (H3); reported per model size and complexity bucket (H1, H2) |
| Token count per question | Measures context-window use, the primary constraint on mid-range hardware. | Reported for every width and method; lower at equal accuracy is better |
| Agent 1 retrieval time per question (with the selector) | The selector builds all four widths, so it adds retrieval work. | Median and 95th percentile under 500 ms |
| Schema-linking precision/recall | Measures whether the needed tables/columns are present at each width (engine quality). | Reported per width |

**5. Validation Strategy**
All comparisons are paired: each question is answered by every width and every method. Differences in accuracy are reported with a 95% paired bootstrap confidence interval (10,000 resamples of questions) and an exact McNemar test. The threshold for H3 is p < 0.0125, fixed in advance; the elbow, complexity-only and retry rows are secondary. The H1 and H4 tests were written down before the runs of the other model sizes. The selector is tested only on databases that it did not train on. Results are reported per complexity bucket, not only as one overall number. A negative result is a valid result and will be reported as such.

**6. Development Approach**
An iterative prototyping approach is used. The retrieval engine and its four modes were built and tuned first. The width sweep and the selector were then built and tested with synthetic rows and stub models, then checked on a 20-question run, before the full runs. Each sweep is resumable, so a long run can stop and continue without loss.

## K.G.Y.V. Thathsarani's Methodology — Complexity-Specialised Parameter-Efficient Fine-Tuning for SQL Reasoning (Standard LoRA vs. HydraLoRA)

**1. Research Methodology**
The research question — whether architecture-level specialisation improves fine-tuning outcomes for a specific task-heterogeneity pattern — requires controlled, quantitative comparison with all confounding variables (base model, dataset, training budget) held constant. A Design Science approach is appropriate because the research produces an evaluated artefact (the HydraLoRA implementation) alongside empirical comparative findings.

> **Selected Methodology**
> Design Science Research, incorporating a controlled quantitative experiment comparing standard LoRA and HydraLoRA architectures under identical training conditions.

**2. Data / Participants / Experimental Inputs**
A synthetic Text-to-SQL training and evaluation dataset, generated via Python-based scripts and labelled by the shared query-complexity taxonomy, is required in sufficient quantity per complexity bucket — particularly multi-join and aggregation examples, where HydraLoRA's advantage is hypothesised to be largest. Bucket sizes will be checked early in development, with deliberate over-sampling of harder categories if under-represented.

**3. Baseline / Benchmark**
Standard single-adapter LoRA, fine-tuned on the identical dataset and base model, serves as the primary baseline, representing the approach used in the reviewed LoRA-based Text-to-SQL literature.

**4. Evaluation Metrics**

*Table — Evaluation Metrics for Thathsarani's Component*

| Metric | Why Relevant | Target / Comparison |
|---|---|---|
| Exact-match SQL accuracy | Standard Text-to-SQL evaluation metric; enables direct comparability with literature baselines. | HydraLoRA ≥ standard LoRA overall |
| JOIN/aggregation-specific accuracy | Isolates the specific failure mode this project's problem statement identifies. | HydraLoRA outperforms standard LoRA on multi-join/aggregation buckets specifically |
| Trainable parameter count | Validates the claim that specialisation does not proportionally increase cost. | HydraLoRA parameter overhead small relative to per-head duplication of a full adapter |

**5. Validation Strategy**
Results are validated by comparing accuracy differences per complexity bucket between the two architectures, rather than relying on a single aggregate accuracy figure, consistent with accepted evaluation practice for heterogeneous-task PEFT architectures as demonstrated in the HydraLoRA literature reviewed above. Parameter-count validation confirms the efficiency claim independently of the accuracy result.

**6. Development Approach**
An iterative prototyping approach is used: the custom HydraLoRA module (routing, shared-A/multi-head-B implementation) is built incrementally and validated against a small subset before committing to full-scale training runs, given that PEFT libraries do not natively support multi-head B-matrix architectures and custom implementation carries higher risk of subtle bugs.

## K.M.I.N. Karunanayake's Methodology — Compression Strategy Analysis for Deployable SQL-Generation SLMs (Quantization-Aware Training vs. Post-Training Quantization)

**1. Research Methodology**
The research question — which compression method better preserves task-specific reasoning — requires controlled, quantitative benchmarking across multiple compression configurations applied to the same underlying fine-tuned model, holding all other variables constant. A Design Science approach is appropriate because the research produces both an evaluated compression pipeline and empirical comparative findings usable for deployment decisions.

> **Selected Methodology**
> Design Science Research, incorporating a controlled quantitative benchmark comparing QAT and PTQ across multiple bit-rates and formats on the same fine-tuned model.

**2. Data / Participants / Experimental Inputs**
The fine-tuned model produced by the project's fine-tuning component (Pillar 2) is the required experimental input; this component cannot begin its core benchmarking until that model is available, though quantization tooling (llama.cpp setup, error-rate metrics suite) can be built and tested against placeholder models in parallel. The same labelled evaluation set used across the project (complexity-stratified natural-language/SQL pairs) is reused for consistency.

**3. Baseline / Benchmark**
The unquantized, full-precision fine-tuned model serves as the accuracy ceiling baseline; PTQ at each bit-rate serves as the simpler-method baseline against which QAT's additional training cost is justified or not.

**4. Evaluation Metrics**

*Table — Evaluation Metrics for Karunanayake's Component*

| Metric | Why Relevant | Target / Comparison |
|---|---|---|
| Syntax accuracy | Isolates whether the model still produces well-formed SQL after compression, independent of logical correctness. | No significant drop vs. full-precision baseline at 8-bit; measured degradation curve at 4-bit |
| Logical (JOIN/aggregation) accuracy | Isolates numerical and multi-table reasoning correctness, the project's core failure mode of concern. | QAT or PTQ, whichever preserves accuracy longer across bit-rates |
| VRAM footprint / inference latency | Confirms the compression method's practical deployability on the mid-range hardware target. | Both methods must fit within the shared hardware budget |

**5. Validation Strategy**
Results are validated by plotting accuracy against bit-rate for both QAT and PTQ, per complexity bucket, to identify the specific inflection point at which each method degrades — a more rigorous validation than a single point-accuracy comparison, and consistent with accepted evaluation practice in the quantization literature reviewed above (which notes inconsistent accuracy trade-offs depending on method).

**6. Development Approach**
An iterative, benchmark-driven approach is used: quantization tooling and the error-rate metrics suite are built and validated on a placeholder model first, so that once the fine-tuned model is available from the upstream component, full-scale benchmarking can proceed immediately without further tooling delays.

## W.A.T. Wathsala's Methodology — Knowledge-Distilled Foundation Models for Resource-Constrained SQL Reasoning

**1. Research Methodology**
The research question — whether distillation produces a stronger foundation model than a native small model — requires controlled comparison with fine-tuning held constant as a variable, isolating model-construction method as the sole difference. A Design Science approach is appropriate because the research produces both an evaluated distillation pipeline and empirical comparative findings.

> **Selected Methodology**
> Design Science Research, incorporating a controlled quantitative comparison between a distilled and a natively small model, evaluated both before and after identical fine-tuning.

**2. Data / Participants / Experimental Inputs**
A distillation dataset of approximately 1,500–3,000 prompt-response pairs is required, generated by running the teacher model over a mix of general reasoning/instruction prompts and SQL-adjacent schema-comprehension prompts — explicitly scoped as a proof-of-concept scale given the project timeline, not a production-scale distillation corpus. This dataset is generated once and does not depend on other components' outputs, allowing this component to begin immediately.

**3. Baseline / Benchmark**
A natively small model of equal parameter count to the distilled student, undergoing the same subsequent fine-tuning process, serves as the baseline — isolating model-construction method as the only variable under comparison.

**4. Evaluation Metrics**

*Table — Evaluation Metrics for Wathsala's Component*

| Metric | Why Relevant | Target / Comparison |
|---|---|---|
| General reasoning score (pre-fine-tuning) | Isolates distillation's effect independently of any SQL-specific fine-tuning, providing a clean early result. | Distilled student ≥ native baseline |
| Exact-match SQL accuracy (post-fine-tuning) | Standard Text-to-SQL evaluation metric; enables comparison with fine-tuning-component baselines. | Distilled-model pipeline ≥ native-model pipeline |
| JOIN/aggregation accuracy (post-fine-tuning) | Isolates the specific reasoning failure mode this project's problem statement identifies. | Distilled-model pipeline outperforms native-model pipeline, particularly on multi-join/aggregation buckets |

**5. Validation Strategy**
Results are validated in two stages: first, an independent pre-fine-tuning comparison establishes whether distillation alone provides a measurable advantage; second, post-fine-tuning comparison (using the identical configuration coordinated with the fine-tuning component) confirms whether that advantage persists after task-specific adaptation. This two-stage validation is more rigorous than a single post-fine-tuning comparison alone, since it separates the contribution of distillation from the contribution of fine-tuning.

**6. Development Approach**
An iterative development approach is used given the exploratory nature of distillation-dataset design: the teacher-prompting strategy and dataset composition are refined based on early student-training results before committing to the full-scale dataset generation and training run.

# 4. HIGH-LEVEL SYSTEM ARCHITECTURE

## Overview of Proposed Solution and Its Components

The proposed system is a privacy-preserving, natural-language-to-SQL query engine composed of four specialised agents, one per member, coordinated by a shared orchestration layer. Consistent with the project's multi-agent framing, each component is treated as an independent agent with a defined input, a defined output, and no direct dependency on another agent's internal implementation — only on the handoff contract between them: Agent 1 (Retrieval, Ekanayake), Agent 2 (Foundation Model, Wathsala), Agent 3 (Fine-Tuned Generation, Thathsarani), and Agent 4 (Quantized Execution, Karunanayake). A user's natural-language question flows through schema retrieval, base-model-backed generation, and quantized execution entirely within enterprise-owned infrastructure.

## System Diagram

> **Diagram note**
> Per the proposal template's requirement, the system diagram must be black-and-white and must not be produced using AI tools. The component structure below is provided as a text-based specification only; the actual figure must be hand-drawn or created using a diagramming tool (e.g. draw.io, Visio) by the team before submission.

*Figure 1 — Combined Component Structure (to be redrawn as a black-and-white diagram)*

| Element | Description |
|---|---|
| [Ekanayake] Input | Natural-language query; live database connection for schema reflection |
| [Ekanayake] Schema Reflection Module | Extracts table structures and foreign-key relationships via database system-catalog queries |
| [Ekanayake] Vector Index (ChromaDB) | Stores table-level DDL embeddings for semantic anchor search |
| [Ekanayake] Retrieval Mode Switch | Selects among semantic-only, structural-only, hybrid, hybrid+pruned configurations |
| [Ekanayake] Column Pruning Stage | Ranks and filters columns within each selected table based on query relevance (builds width W2) |
| [Ekanayake] Width Builder | Builds the four nested contexts: W1 anchor table only, W2 hybrid+pruned, W3 hybrid, W4 full schema |
| [Ekanayake] Width Selector | Chooses one width for the question from features known before generation; trained on the SQL model's own execution results |
| [Ekanayake] Output | Schema context at the selected width, the width and the complexity label, passed to the fine-tuned SQL-generation component |
| [Thathsarani] Input | Pruned schema context (from retrieval component); base model checkpoint (from model-construction component); complexity-labelled training data |
| [Thathsarani] Standard LoRA Module | Single shared adapter (A, B matrices) fine-tuned on the full dataset — control condition |
| [Thathsarani] HydraLoRA Module | Shared A matrix; multiple complexity-specialised B-matrix heads |
| [Thathsarani] Routing Logic | Hard-coded routing using the shared query-complexity classifier |
| [Thathsarani] Output | Winning AND runner-up fine-tuned SQL-generation models, passed to the quantization component — the runner-up specifically to support that component's cross-check |
| [Karunanayake] Input | Winning fine-tuned SQL-generation model, and separately the runner-up, from the fine-tuning component |
| [Karunanayake] PTQ Pipeline | Post-hoc quantization across bit-rates (8-bit, 4-bit) and formats (GGUF, AWQ) using llama.cpp |
| [Karunanayake] QAT Pipeline | Quantization-aware fine-tuning at the same bit-rates |
| [Karunanayake] Cross-Check | Winning quantization strategy re-applied to the runner-up fine-tuned model, testing whether the ranking is stable across fine-tuning architectures |
| [Karunanayake] Error-Rate Metrics Suite | Separately scores syntax validity and logical (JOIN/aggregation) correctness |
| [Karunanayake] Output | Deployment-ready quantized model, used for live SQL execution against the local database |
| [Wathsala] Teacher Model | Approximately 7B-parameter model used for inference only, to generate the distillation dataset |
| [Wathsala] Distillation Dataset Generation | Prompt-response pairs collected from the teacher across general reasoning and SQL-adjacent prompts |
| [Wathsala] Student Model Training | Small model (matched in size to the native baseline) trained on teacher-generated responses |
| [Wathsala] Native Baseline Model | An off-the-shelf small model of equal parameter count, used as the comparison baseline |
| [Wathsala] Output | Both the distilled and native base models, handed off to the fine-tuning component |

## Internal Sub-Agent Structure — Agent 1 (Retrieval)

Agent 1 is itself internally composed of three cooperating sub-agents, mirroring the project's overall multi-agent design philosophy at the component level rather than being a single monolithic module. Anchor Selection decides where retrieval begins, using either semantic similarity (ChromaDB embedding search) or structural keyword matching, depending on the active retrieval mode. Traversal decides which additional tables to pull in, walking the foreign-key graph outward from the anchor table when the active mode calls for it. Pruning decides, for hybrid-pruned mode specifically, which individual columns within each selected table are retained. Together these sub-agents build the nested widths. The Width Selector then makes one more bounded decision: which width to send for this question. Each step makes one decision and passes its output to the next, composing into the single schema context that Agent 1 as a whole hands to Agent 3.

## Internal Sub-Agent Structure — Agent 3 (Fine-Tuned Generation)

Agent 3 decomposes into two sub-agents, reflecting the two distinct decisions it makes at inference time. The Head-Selection Sub-Agent consumes the complexity label produced by Agent 1's shared classifier and, when running in HydraLoRA mode, routes to the correct complexity-specialised adapter head (or the single shared adapter, when running in standard-LoRA mode). The Generation Sub-Agent then produces the actual SQL statement, conditioned on the pruned schema context, the user query, and the selected head. Separating these two decisions keeps the routing logic — which is what Agent 3's own research question is actually about — independently inspectable from the generation step itself, rather than treating fine-tuned generation as a single opaque call. Beyond live inference, Agent 3's
