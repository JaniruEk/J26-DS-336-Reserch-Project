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

## Results: Qwen2.5-1.5B-Instruct FP16 (22 November 2026)

Model: Qwen2.5-1.5B-Instruct through transformers, FP16, Agent 4's loader, prompt and `generate_sql` (greedy,
max 100 new tokens). Retriever: `RECOMMENDED`, no value hints. Tokens: tiktoken cl100k (default). Commands:

    python -m scripts.width_sweep --pairs eval/spider_dev_full.json eval/chinook_pairs.json eval/northwind_pairs.json --local fp16 --elbow --out results/width/dev_qwen1.5b_fp16.jsonl
    python -m scripts.width_sweep --pairs eval/spider_train_width.json --local fp16 --elbow --out results/width/train_qwen1.5b_fp16.jsonl
    python -m scripts.width_selector results/width/train_qwen1.5b_fp16.jsonl --test results/width/dev_qwen1.5b_fp16.jsonl --save agent1_retrieval/width_selector.joblib

### Execution accuracy by width (distraction curves for 1.5B)

Test set (Spider dev + Chinook + Northwind, 869 scored, 40 skipped because the gold SQL returns no rows; 22 DBs):

| Bucket | n | W1 | W2 | W3 | W4 | E (elbow) | any width |
|---|---|---|---|---|---|---|---|
| simple | 245 | .79 | .64 | .69 | .61 | .79 | .84 |
| single-join | 104 | .18 | .47 | .43 | .39 | .36 | .56 |
| multi-join | 37 | .03 | .32 | .32 | .32 | .08 | .49 |
| aggregation | 483 | .48 | .58 | .57 | .53 | .51 | .70 |
| ALL | 869 | .51 | .57 | .57 | .53 | .55 | .71 |
| mean tokens | | 58 | 151 | 180 | 245 | 84 | |

Training set (Spider train, 1,144 scored, 56 skipped (one gold SQL names a missing table); 137 DBs, none in the test set):

| Bucket | n | W1 | W2 | W3 | W4 | any width |
|---|---|---|---|---|---|---|
| simple | 297 | .77 | .72 | .73 | .70 | .87 |
| single-join | 282 | .13 | .38 | .38 | .37 | .54 |
| multi-join | 273 | .03 | .32 | .33 | .45 | .55 |
| aggregation | 292 | .45 | .55 | .56 | .54 | .68 |
| ALL | 1144 | .35 | .50 | .50 | .52 | .67 |
| mean tokens | | 55 | 177 | 192 | 342 | |

Answers of 95 or more tokens (possible cut at the 100-token limit), test set: W1 10, W2 3, W3 3, W4 7, E 11 of 869
(at most 1.3%): the limit was kept. No schema was too long for the model.

### Selector (trained on Spider train, tested on the test set)

Training labels (narrowest correct width): W1 405, W2 235, W3 10, W4 97; no correct width 397 (not used).
Each row against the best fixed width (W2); paired bootstrap 95% CI and exact McNemar.

| System | simple | single-join | multi-join | aggregation | ALL | tokens | diff vs W2 | 95% CI | wins/losses | p |
|---|---|---|---|---|---|---|---|---|---|---|
| fixed W1 | .79 | .18 | .03 | .48 | .51 | 58 | -.060 | [-.093, -.026] | 86/138 | .001 |
| fixed W2 | .64 | .47 | .32 | .58 | .57 | 151 | | | | |
| fixed W3 | .69 | .43 | .32 | .57 | .57 | 180 | .000 | [-.014, +.014] | 19/19 | 1.000 |
| fixed W4 | .61 | .39 | .32 | .53 | .53 | 245 | -.044 | [-.071, -.017] | 55/93 | .002 |
| complexity rule | .73 | .45 | .30 | .57 | .59 | 127 | +.018 | [+.003, +.033] | 31/15 | .026 |
| adaptive elbow | .79 | .36 | .08 | .51 | .55 | 84 | -.024 | [-.055, +.006] | 85/106 | .148 |
| **learned selector** | .77 | .42 | .27 | .55 | .58 | 84 | +.010 | [-.016, +.036] | 78/69 | .510 |
| learned, complexity only | .77 | .34 | .16 | .51 | .55 | 77 | -.028 | [-.056, +.001] | 76/100 | .083 |
| W2 + retry wider | .67 | .52 | .41 | .61 | .61 | 219 | +.036 | [+.024, +.049] | 31/0 | <.001 |
| selector + retry | .78 | .48 | .38 | .60 | .63 | 129 | +.054 | [+.030, +.078] | 85/38 | <.001 |
| oracle (limit) | .84 | .55 | .49 | .69 | .71 | 80 | +.135 | [+.113, +.157] | 117/0 | <.001 |

Learned selector against the complexity rule: -.008 [-.030, +.014], 48/55, p = .555. Against the complexity-only
selector: +.038 [+.021, +.054], 46/13, p < .001. Widths picked: W1 660, W2 189, W3 0, W4 20.
Retry rows are offline: the retry sees a wider schema but no error hint.

### Hypotheses (1.5B only)

1. Best fixed width narrower for smaller models: **not testable yet** (needs the 0.5B / 3B / 7B sweeps).
2. Best width differs by complexity: **supported descriptively** (test set: simple W1 .79 vs W4 .61; single-join
   W1 .18 vs W2 .47). No formal test run yet.
3. Learned selector beats every fixed width and the complexity rule at p < .0125: **not supported.** It equals the
   best fixed width (+.010, p = .51) at 84 against 151 tokens, and does not beat the complexity rule (p = .555).
4. Selector transfer across models: **not testable yet.**

Secondary: the schema and retrieval features add information over complexity alone (+.038, p < .001). Retry with a
wider schema adds accuracy (offline estimate), and the selector + retry reaches .63 at 129 tokens.

## Pre-registered rules for model sizes (written 22 November 2026; amended 23 November 2026, before any run of another size)

Plan: `reports/agent1_width/plan_weeks5-6.md`. Amendment: no Colab GPU runtime could be obtained, so every run is on the
laptop GPU used for the 1.5B run (mid-range hardware). Its memory holds 0.5B and 3B at FP16 but 7B only at INT4.
Runs: Qwen2.5 0.5B, 3B Instruct FP16 (dev + train), 7B Instruct INT4 (dev), 1.5B Instruct INT4 (dev, precision bridge);
same prompt and decoding as the 1.5B FP16 run. Results in `results/width/`.

- Test set: the dev ids of the sweep files; every comparison uses only the ids present in all files compared.
- Distraction D(model) = accuracy(W4) - accuracy(W2) on the test set.
- **H1 primary test:** D(3B FP16) - D(0.5B FP16) > 0, with a 95% paired bootstrap CI (10,000 resamples of
  questions, seed 0) that excludes 0. Secondary (descriptive): best fixed width per size; D for all sizes;
  simple-bucket accuracy(W1) - accuracy(W4) per size; 7B INT4 shown with the bridge.
- **Bridge:** D(1.5B INT4) - D(1.5B FP16) with the same CI. If its CI excludes 0, the 7B INT4 row is reported as
  "precision-confounded" and is not used for H1.
- **H4 test:** on the 0.5B and 3B test rows, the selector trained on that model's own train rows against the
  selector trained on the 1.5B train rows (exact McNemar). Supported if the own selector beats the transfer selector
  at p < 0.025 (0.05 / 2) for at least one of the two models.
- Not done in these weeks: 7B train rows (H4 on 7B); changing the label or the selector (post-hoc; separate decisions).

## Not done yet

- Other model sizes (0.5B, 3B, 7B) and hypotheses 1 and 4.
- With the selector, Agent 1 builds all four contexts for each question. Measure the retrieval time against the
  500 ms target.
