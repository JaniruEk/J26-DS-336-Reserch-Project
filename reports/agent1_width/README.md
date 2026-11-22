# Agent 1: adaptive context width (approved November 2026)

New main claim: Agent 1 selects how much schema to show for each question, and learns the selection from the SQL
results of the small model. Proposal addendum: "Agent 1 Proposal Addendum: Adaptive Context Width".

## The four widths (`agent1_retrieval/width.py`)

| Width | Content | Existing mode |
|---|---|---|
| W1 | the anchor table only | `semantic` |
| W2 | anchor tables + FK tables, columns pruned | `hybrid_pruned` (RECOMMENDED) |
| W3 | anchor tables + FK tables, all columns | `hybrid` (RECOMMENDED) |
| W4 | the full schema | new |

## Steps (run on a machine with Ollama, from the repository folder)

1. Build the question sets (one time, downloads Spider):
   `python -m scripts.get_spider --width`
   -> `eval/spider_dev_full.json` (test) and `eval/spider_train_width.json` (selector training).
2. Quick check, 20 questions:
   `python -m scripts.width_sweep --pairs eval/chinook_pairs.json --model qwen2.5:1.5b-instruct --limit 20`
3. The distraction curves, one run per model size (`ollama pull` each model first):
   `python -m scripts.width_sweep --pairs eval/spider_dev_full.json eval/chinook_pairs.json --model qwen2.5:1.5b-instruct --out results/width/dev_qwen1.5b.jsonl`
   Repeat with `qwen2.5:0.5b-instruct`, `qwen2.5:3b-instruct`, `qwen2.5:7b-instruct`.
   The run can be stopped and started again. It prints accuracy per complexity bucket and width.
4. Training rows for the selector (same model as the test rows):
   `python -m scripts.width_sweep --pairs eval/spider_train_width.json --model qwen2.5:1.5b-instruct --out results/width/train_qwen1.5b.jsonl`
5. Train and test the selector:
   `python -m scripts.width_selector results/width/train_qwen1.5b.jsonl --test results/width/dev_qwen1.5b.jsonl --save agent1_retrieval/width_selector.joblib`
   It prints fixed W1..W4, the complexity rule, the elbow (if swept), the learned selector, the same selector with
   complexity features only, retry with the next wider width (tokens count every width tried) and the oracle,
   with paired statistics. Test fixed in advance (hypothesis 3): the learned selector beats every fixed width and
   the complexity rule at p < 0.0125. The other rows are secondary.
6. With Agent 3's adapter in place of an Ollama model: add `--agent3 <adapter folder>` to step 3 and step 4.

Token counts use tiktoken by default (as in all earlier results). Set `J26_TOKENIZER=Qwen/Qwen2.5-1.5B-Instruct`
to count with the model's own tokenizer; report which one was used.

## Baseline, application and full pipeline

- Adaptive-elbow baseline: add `--elbow` to the sweep commands. The selector script then shows an "adaptive elbow" row.
  It is a simplified form of arXiv 2611.20979 (no smoothing).
- Selector in the application: set `J26_WIDTH_SELECTOR=agent1_retrieval/width_selector.joblib` before the start.
  The handoff then has a `width` field. After a failed attempt, the retry gets the next wider schema.
- Full pipeline: `python -m scripts.e2e_eval --pairs eval/spider_dev_full.json eval/chinook_pairs.json --name <configuration>`
  then `--compare results/e2e/A.jsonl results/e2e/B.jsonl`.

## Novelty check (22 November 2026)

Method: a new literature search (text-to-SQL and general retrieval-augmented generation), a check of every paper
cited earlier, and a full-text read of the closest papers. Full text was read for: QCMA-SQL, EllieSQL, AutoLink,
AttnLink, EviLink, Adaptive-Elbow, LitE-SQL, Rethinking Schema Linking, both DSR-SQL papers, DecoSearch, CHS-SQL,
BudgetSchemaBench (partly). Other entries: abstract only. The web tool gave summaries, so check each quote in the
paper before you cite it.

### Claim (narrowest form that the search supports)

For one given small local SQL model (0.5B to 7B), Agent 1 selects one of four nested schema widths for each
question, before generation. The selector learns from labels that come from the same model's own execution
results (label = the narrowest width whose SQL returned the gold rows). Its inputs are known before generation.
The study also reports execution accuracy against width, by model size and by SQL complexity (the distraction
curves). Retry with the next wider width is an ablation, not a claim. Say "to our knowledge, as of November 2026".

### What is NOT new (credit it, do not claim it)

| Idea | Prior work |
|---|---|
| A different amount of schema for each question | QCMA-SQL (NAACL 2025 Findings; learned selector, gold-SQL labels), AttnLink (arXiv 2608.00693; top-p cut), EviLink (2605.29670), Adaptive-Elbow (2611.20979), DSR-SQL (arXiv 2511.21402; token-count rule), DecoSearch (2606.17821; LLM selection), CHESS, GRAST-SQL (2512.16083) |
| A router learned from the model's own results | Adaptive-RAG (Jeong et al., NAACL 2024, arXiv 2403.14403): complexity classifier, labels from model outcomes, chooses the retrieval strategy |
| The label "cheapest option that succeeds" | EllieSQL (COLM 2025, arXiv 2503.22402): "the most efficient capable" pipeline per question |
| A learned number of context items from generator feedback | DynamicRAG (NeurIPS 2025, arXiv 2505.07233; read from summaries only), Dynamic Context Selection (arXiv 2512.14313; labels from hop count) |
| Accuracy against schema amount | BudgetSchemaBench (arXiv 2610.00092; fixed budgets, API models, no split by model size or difficulty), Balancing Content Size (2502.15723), LitE-SQL (2510.09014; fixed k, 1.5B to 7B, "smaller models less robust to irrelevant columns") |
| Pruned against full schema, chosen per question | RSL-SQL, DSR-SQL (EMNLP 2026, Dual-Schema): both run for every question, an execution-aware merger chooses AFTER generation (two generations per question) |
| Wider schema after an error | AutoLink (arXiv 2511.17190) widens the schema on verification errors BEFORE generation; after a failed execution it revises only the SQL. LitE-SQL: execution-guided SQL correction. So retry-wider is close, not identical: keep it an ablation |
| Small models are distracted by extra context | LitE-SQL (App. B.3), Lost in the Middle (TACL 2023), The Distracting Effect (ACL 2025), arXiv 2603.11513 (abstract snippet only) |

### What is left (the contribution)

The combination, for schema width, on small local models:
1. Nested structural widths over the FK graph (anchor table, pruned, related tables, full schema), not a ranked list.
2. Labels from the deployed small model's own execution results, not from gold-schema relevance (QCMA-SQL,
   GRAST-SQL), model confidence (CHS-SQL), or an LLM (DecoSearch). AttnLink states that the best
   precision/recall balance "is generator-dependent"; this study learns it per generator.
3. One choice BEFORE generation: one generation per question (DSR-SQL EMNLP and RSL-SQL generate twice).
4. Distraction curves by model size (0.5B to 7B) AND SQL complexity. BudgetSchemaBench sweeps the budget but has
   no small open models and no size or difficulty split.

### Baselines this requires (all in `scripts/width_selector.py`)

| Baseline | Answers the question |
|---|---|
| Best fixed width (W1..W4) | Does selection beat one good setting? (hypothesis 3, with the complexity rule) |
| Complexity rule (`choose_rule`) | Does learning beat a hand rule? |
| Adaptive elbow (`--elbow`) | Does learning beat a training-free per-question cut? |
| Learned, complexity only (`COMPLEXITY_ONLY`) | Adaptive-RAG design. If the full selector does not beat it, the schema and retrieval features add nothing |
| W2 + retry wider, selector + retry | The app's retry rule (offline: the retry gets a wider schema but no error hint) |
| Oracle | Upper limit |

Not built: a two-generation post-hoc choice (RSL-SQL / DSR-SQL style). It costs a second generation per question;
add it only if a reviewer asks.

### Read before PP2

Full text not read: DynamicRAG, arXiv 2603.11513 (small models and retrieval), Google "Is Long Context All You
Need?" (arXiv 2501.12372), MCTS-SQL (2501.16607), MSc-SQL (2410.12916), JOLT-SQL (2505.14305). One search round is
not the whole field: search again before PP2 and before the thesis.

## Not done yet

- No model run exists: the code was tested with synthetic rows and stub models only.
- With the selector, Agent 1 builds all four contexts for each question. Measure the retrieval time against the
  500 ms target.
