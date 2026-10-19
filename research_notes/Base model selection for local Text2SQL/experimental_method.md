# Experimental methodology for small-model (<=1.5B-3.8B) Text-to-SQL research (as of Oct 2026)

## Datasets: which to use for training vs headline evaluation, licences, contamination

### Takeaway
Train on Spider train (+ optionally BIRD train / synthetic SynSQL-style data) and report headline numbers on Spider dev/test with test-suite accuracy plus BIRD dev (or mini-dev, with caveats); use Spider-Syn/Realistic/DK as robustness checks. Spider 2.0 is far too hard for <=4B models to be a useful headline metric. Spider is plausibly contaminated in pretrained LLMs, so a held-out in-house/fresh DB set (e.g. Chinook pairs written by the team) should be reported alongside it.

### Cited Findings
- Spider 1.0: 7,000 train / 1,034 validation (dev) examples; the Hugging Face card lists the licence as CC BY-SA 4.0 — [TFDS/HF Spider card](https://tensorflow.google.cn/datasets/community_catalog/huggingface/spider); the official GitHub repo is labelled Apache-2.0 — [taoyds/spider](https://github.com/taoyds/spider). (Conflict: the code repo and the dataset card list different licences; cite the dataset card for the data.)
- Since 15 Nov 2020, Test-Suite Accuracy is the official Spider/SParC/CoSQL metric — [taoyds/spider](https://github.com/taoyds/spider). The Spider test set is now used by papers (e.g. OmniSQL reports Spider test 87.9% for 7B) — [OmniSQL](https://arxiv.org/html/2503.02240v2). I did not confirm the exact public-release date of the test set.
- Robustness variants Spider-DK, Spider-Syn, Spider-Realistic are standard secondary benchmarks; OmniSQL-7B: Spider-DK 76.1, Spider-Syn 69.7, Spider-Realistic 76.2 vs Spider dev 81.2 (greedy) — [OmniSQL](https://arxiv.org/html/2503.02240v2).
- BIRD Mini-Dev = 500 SELECT-only examples chosen by the BIRD team from BIRD dev (2 duplicates -> 498 unique) — [Jin et al. 2026](https://arxiv.org/abs/2601.08778).
- Annotation error rates: BIRD Mini-Dev 52.8%, Spider 2.0-Snow 62.8%; re-evaluating 16 agents on corrected BIRD dev subsets changed scores by -7% to +31% (relative) and ranks by -9 to +9; correlation of corrected subset with full dev only r=0.32 — [Jin, Choi, Zhu, Kang, Jan 2026](https://arxiv.org/abs/2601.08778). (This weakens BIRD as a precise headline metric; supersedes the assumption that BIRD dev labels are reliable.)
- Spider 2.0: 632 enterprise workflow problems, DBs often >1,000 columns on BigQuery/Snowflake/etc.; o1-preview agent solved 17.0% (vs 91.2% Spider 1.0, 73.0% BIRD); GPT-4o 10.1% — [Spider 2.0 paper](https://arxiv.org/pdf/2411.07763) (via search summary). Spider2-Snow = 547 examples on Snowflake — same source.
- Contamination: GPT-3.5 scored 10-20 points lower on an unseen dataset (Termite) than on Spider at matched difficulty (e.g. HARD 48.83% Spider vs 28.33% Termite), and could reconstruct masked Spider columns far better (DC-accuracy 33.42% vs 13.21%) — [Ranaldi et al., Findings ACL 2024](https://arxiv.org/html/2402.08100v1).
- OmniSQL does not discuss Spider/BIRD dev leakage into its synthetic training data — [OmniSQL](https://arxiv.org/html/2503.02240v2).

### Inferences
- For this project: train on Spider train (never dev), evaluate on Spider dev (test-suite) + team-authored Chinook pairs as a contamination-free "enterprise-like" check; treat BIRD mini-dev as optional/secondary because of label noise and because 3.8B models score low there.
- Report the Chinook result as the deployment-relevant number; Spider as the comparable-to-literature number. Absolute Spider numbers for phi3/Qwen may be inflated by contamination, but paired *relative* comparisons (A vs B on same items) are less affected.
- Spider 2.0 is not a sensible target for 8GB/<=4B models; mention it only to scope the work.

### Gaps
- Exact Spider 1.0 test-set release date and its licence text not verified.
- BIRD licence (believed CC BY-SA 4.0) not verified in this session.
- No source found that measures contamination specifically for phi3 / Qwen2.5 small models on Spider.

## Does fine-tuning/prompting a small model on pruned (schema-linked) context improve accuracy?

### Takeaway
For fine-tuned ~7B models, the literature consistently finds that a *high-recall* schema filter helps modestly (+1-7 EX points), and that gold-schema context gives a large upper bound (+5-15 points). For frontier long-context models, schema linking is neutral or harmful because recall loss outweighs noise reduction. The key condition for pruning to help is near-perfect recall plus training on the same kind of filtered context the model sees at test time.

### Cited Findings
- DTS-SQL (2 x 7B, Spider dev): full-schema fine-tuning vs two-stage (schema-linking model + generator fine-tuned on correct-table schema) vs gold-schema upper bound — DeepSeek-7B EX 82.1 -> 85.5 -> 90.3 (EM 69.0 -> 79.1 -> 84.2); Mistral-7B EX 71.9 -> 78.6 -> 86.6. Schema-linker table recall 97.7-97.8%, precision 97.5-98.4%. Spider test: DeepSeek 84.4 EX — [DTS-SQL, Pourreza & Rafiei 2024](https://arxiv.org/html/2402.01117).
- CodeS (1B-15B, SFT): Spider dev EX/TS — 1B 77.9/72.2, 3B 83.4/78.1, 7B 85.4/80.3; BIRD dev EX 1B 38.46, 3B 43.42, 7B 45.24. Schema filter (classifier AUC 0.991/0.993 table/column on Spider) keeps top-6 tables / top-10 columns for SFT; removing the filter cost 0.8-2.4 points Spider dev and 1.57-1.89 BIRD dev. To avoid train-test mismatch they pad training prompts with randomly selected unused tables up to top-k — [CodeS, Li et al. SIGMOD 2024](https://arxiv.org/html/2402.16347v1).
- "Death of Schema Linking?": aggressive column filtering dropped schema-linking recall to 77.44% (conservative 88.77%); with real schema linking, ft:GPT-4o fell 67.35 -> 62.58, Gemini 1.5 Pro 60.54 -> 55.78, Llama-3.1-405B 59.18 -> 56.46 on BIRD; weaker models (e.g. Llama 3.1-8B) gained from schema linking while top models degraded — [Maamari et al., NeurIPS 2024 TRL workshop](https://arxiv.org/html/2408.07702v2).
- "Is Long Context All You Need?" (Gemini-1.5, BIRD dev): all tables 62.32% vs top-7 tables 54.69% vs top-1 table 38.01%; KaggleDBQA all tables 56.75% vs top-2 50.27%. Authors: "recall is more important than precision"; model not confused by many irrelevant tables (<35% table precision) — [Chung et al., VLDB 2025 / arXiv 2501.12372](https://arxiv.org/html/2501.12372v5). Search summary of the same paper notes that for smaller/older models the gains from schema linking can justify the loss — [arXiv 2501.12372](https://arxiv.org/html/2501.12372v1).
- OmniSQL presents the full schema as CREATE TABLE with column descriptions and 2 representative values per column, plus question-relevant DB values, with no separate pruning step; 7B greedy: Spider dev 81.2, BIRD dev 63.9 (base Qwen2.5-Coder-7B: 73.4 / 50.9) — [OmniSQL](https://arxiv.org/html/2503.02240v2).
- SLM-SQL (IJCNLP-AACL Findings 2025): with SynSQL-derived SFT + RL + corrective self-consistency, 0.5B reaches 56.87% and 1.5B 67.08% EX on BIRD dev — [SLM-SQL](https://arxiv.org/abs/2507.22478) (note: uses self-consistency sampling, not greedy single-shot).

### Inferences
- The project's observed pattern (pruning saves ~30% tokens, no accuracy gain, hurts multi-join unless column recall ~1.0) matches the literature: Maamari et al. and Chung et al. both show recall loss dominates. The phi3 runs are *untrained* on pruned context — DTS-SQL and CodeS gains come from generators *fine-tuned* on filtered schemas. A fair test of pruning therefore requires Agent 3 to fine-tune on the same retrieval mode used at test time (train-on-pruned / test-on-pruned vs train-on-full / test-on-full), with CodeS-style random padding so the training distribution matches noisy retrieval.
- Suggested design: 2x2 (train context {full/table-level, pruned} x test context {full, pruned}) to isolate mismatch effects.
- Report a gold-schema (oracle) arm: it bounds how much any retrieval improvement could buy, and is cheap to compute from gold SQL.
- Expect gains to be small (CodeS: 1-2 points); the project's n must be sized accordingly (see statistics section).

### Gaps
- Did not fetch RESDSQL, RSL-SQL, CHESS, GRASP, RASL or the "AST-based retrieval-augmented pruning" paper in this session — numbers for those are not included here (not invented).
- No paper found that reports gold-schema accuracy specifically for <=3.8B models (CodeS-1B/3B ablations on gold schema not extracted).
- No direct experiment found that trains on pruned and tests on full (or vice versa) for small models; the mismatch claim rests on CodeS's design rationale.

## Oracle (gold-schema) upper bounds

### Takeaway
Gold schema typically adds ~5-8 EX points over the best realistic schema linker for fine-tuned 7B models on Spider dev.

### Cited Findings
- DTS-SQL Spider dev upper bound with gold tables: DeepSeek-7B 90.3 EX (vs 85.5 with predicted linking, 82.1 full schema); Mistral-7B 86.6 (vs 78.6, 71.9) — [DTS-SQL](https://arxiv.org/html/2402.01117).
- Maamari et al. use an SQL-parser oracle (100% recall) as the upper-bound arm and show accuracy differences across models shrink from ~28 to ~14 points as false-positive rate drops from 99% to 0% — [Death of Schema Linking?](https://arxiv.org/html/2408.07702v2).

### Inferences
- The project already has gold SQL, so an oracle-columns arm (columns parsed from gold SQL) and oracle-tables arm are cheap and make "pruning neutral" results interpretable (is the ceiling itself higher?).

### Gaps
- Gold-schema numbers for 1-4B models not found.

## Metrics: EX vs EM vs test-suite; per-bucket reporting

### Takeaway
Use execution accuracy (EX) as the primary metric, with test-suite accuracy (TS) on Spider dev; report EM only as a reference. Report per complexity bucket with bucket n and CIs.

### Cited Findings
- Test-suite accuracy executes predictions on multiple distilled DB instances and gives a "tighter upper-bound for semantic accuracy" than single-DB EX; supports Spider, SParC, CoSQL and 8 classical datasets; encourages reporting with model-predicted values (no `--plug_value`) — [test-suite-sql-eval](https://github.com/taoyds/test-suite-sql-eval).
- EX and EM diverge substantially, e.g. DeepSeek-7B full-schema 82.1 EX vs 69.0 EM — [DTS-SQL](https://arxiv.org/html/2402.01117); CodeS-7B 85.4 EX vs 80.3 TS on Spider dev — [CodeS](https://arxiv.org/html/2402.16347v1) (single-DB EX overstates by ~4-6 points).
- Spider's official difficulty buckets (easy/medium/hard/extra) are used for per-difficulty reporting, e.g. contamination study — [Ranaldi et al.](https://arxiv.org/html/2402.08100v1).

### Inferences
- The project's strict row-multiset match is an EX variant; note ORDER BY handling and value formatting rules explicitly. Run the official test-suite script on Spider dev items as a cross-check of the in-house evaluator.
- Report the project's own taxonomy (simple / single-join / multi-join / aggregation) alongside Spider hardness for comparability.

### Gaps
- Test-suite DBs exist only for Spider-family/classical datasets; not for Chinook/TPC-H.

## Statistics for small-n comparisons

### Takeaway
At n~128, only very large differences (~10+ points) are detectable. Detecting 3-5 point EX differences with 80% power needs roughly 300-1,700 paired items depending on how often the two systems disagree. Use paired tests (exact McNemar or paired bootstrap), report CIs and discordant counts, multiple training seeds for fine-tuned arms, and correct for multiple comparisons across the four studies/buckets.

### Cited Findings
- Dror et al. (ACL 2018) give a protocol for choosing significance tests in NLP and found significance testing often ignored or misused in ACL/TACL 2017 papers; appendix recommends tests per metric (e.g. McNemar for paired accuracy, bootstrap for non-decomposable metrics) — [Dror et al. 2018](https://aclanthology.org/P18-1128/); [appendix](https://arxiv.org/pdf/1809.01448).
- Card et al. (EMNLP 2020): underpowered experiments are common in NLP; small test sets mean most comparisons are not adequately powered; power depends on test, alpha, effect size, variance and n; they release power-analysis notebooks — [Card et al. 2020](https://arxiv.org/pdf/2010.06595); code: dallascard/NLP-power-analysis.
- Computed here (Connor's normal approximation for McNemar, alpha=0.05 two-sided, power 0.80; p_d = fraction of items where the two systems disagree, d = EX difference) — own calculation, not from a paper:
  - p_d=0.10: d=3 pts -> n~870; d=5 -> ~312; d=10 -> ~77
  - p_d=0.20: d=3 -> ~1,742; d=5 -> ~626; d=10 -> ~155
  - p_d=0.30: d=3 -> ~2,614; d=5 -> ~940; d=10 -> ~234
  - Project's current pruning-vs-hybrid run had 26/128 discordant (p_d~0.20), so ~600+ items would be needed to detect 5 points.

### Inferences
- Pool Chinook + Spider dev (1,034) + TPC-H to reach >=600-1,000 paired items for the headline comparisons; keep per-bucket results descriptive (CIs, not significance claims), since buckets will be ~150-250 each.
- For fine-tuning arms (Agents 2/3/4), run >=3 seeds and report mean +/- sd plus a paired test on pooled predictions or per-seed; variance across seeds can exceed the effect size.
- Pre-register the primary comparison per agent (one per study) and apply Holm-Bonferroni across secondary comparisons/buckets.
- Report effect sizes as EX difference with 95% paired bootstrap CI, plus discordant counts (b, c) and odds ratio b/c.

### Gaps
- Exact numeric power tables from Card et al. not extracted (PDF unreadable via fetch).
- No text-to-SQL-specific guidance on seed counts found.

## Common pitfalls

### Takeaway
Main risks: dev/test leakage and pretraining contamination, label errors in benchmarks, train/test prompt-format or context mismatch, stochastic decoding without fixed seeds, comparing greedy results to self-consistency results, and evaluator differences (EX vs TS vs EM, value plugging).

### Cited Findings
- Benchmark label errors are large enough to reorder leaderboards (BIRD Mini-Dev 52.8% error) — [Jin et al. 2026](https://arxiv.org/abs/2601.08778).
- Contamination inflates Spider scores by 10-20 points for GPT-3.5 — [Ranaldi et al.](https://arxiv.org/html/2402.08100v1).
- Papers mix decoding regimes: OmniSQL reports both greedy and 8-sample majority voting — [OmniSQL](https://arxiv.org/html/2503.02240v2); SLM-SQL uses corrective self-consistency — [SLM-SQL](https://arxiv.org/abs/2507.22478). Comparing a greedy result to these is unfair.
- Train-test schema-context mismatch is handled deliberately in CodeS by padding training prompts with random unused tables — [CodeS](https://arxiv.org/html/2402.16347v1).
- Test-suite eval distinguishes runs with/without gold value plugging (`--plug_value`), which changes scores — [test-suite-sql-eval](https://github.com/taoyds/test-suite-sql-eval).

### Inferences
- Use greedy decoding (temperature 0) with fixed seeds for all arms; keep one prompt template shared across agents; log the exact rendered prompt per item (the harness log already does this).
- Never tune thresholds (similarity 0.6, min_cols, anchors) on the same items used for headline results — split Spider dev or hold out a fixed test portion.
- Manually audit a sample of failures for gold-label errors, especially in Chinook pairs written by the team.

### Gaps
- No systematic study found on evaluator bugs in custom EX scripts (ordering, NULLs, float rounding); recommend cross-checking with the official script.
