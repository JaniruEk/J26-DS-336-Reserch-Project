# Execution Plan — J26-DS-336 (all four members, phase by phase)

Derived from the individual proposals' WBS/Gantt and the project scope. Months are project months (Month 1 = kickoff). Each phase lists **what to build**, **done when** (exit criteria) and **hands off**. Items marked *proposed* are suggestions not yet agreed with the owner.

## 0. Shared assets already in this repo (reuse, don't rebuild)

| Asset | Where | Used by |
|---|---|---|
| Complexity taxonomy from SQL (`classify_sql`) — labels any (question, SQL) pair as simple / single-join / multi-join / aggregation | `agent1_retrieval/complexity.py` | Agent 3 dataset labelling; Agent 4 stratified evaluation |
| NL complexity classifier (`classify_query`), live, pre-retrieval (Spider dev acc 0.57) | `agent1_retrieval/complexity.py`, `complexity_nl.joblib` | Agent 3 head routing |
| Eval sets: Chinook (14), TPC-H (14), Spider dev stratified (120), with gold SQL | `eval/*.json`, databases via `scripts/` | everyone's evaluation |
| Execution-match scorer (row multiset vs gold) and paired stats (bootstrap CI, exact McNemar) | `agent1_retrieval/execution.py`, `stats.py` | Agents 2, 3, 4 accuracy comparisons |
| Handoff contract Agent 1 → Agent 3 (`Agent1.run` dict: `query, complexity, mode, anchor, tables, ddl, tokens, latency_ms`) — *Thathsarani to confirm* | `agent1_retrieval/agent.py` | Agent 3 prompt construction |
| FastAPI harness with JSON-lines handoff log and bounded retry; Agents 3/4 pluggable via `create_app(generate=, execute=)` | `harness/app.py` | integration phase |
| Generator stand-in: local phi3 via Ollama | `agent1_retrieval/execution.py` | placeholder until real models exist |

**Rules for fair comparison (all members):** same evaluation pairs, same mid-range hardware budget, one variable changed at a time, report per complexity bucket and with paired statistics — not a single aggregate. A negative result is a valid result.

**Open interface decisions to lock early (Month 1–2):**
1. Agent 1 → Agent 3 payload format (JSON with DDL inside, as implemented) — Ekanayake ↔ Thathsarani.
2. Base-model checkpoint format and tokenizer (e.g. HF safetensors + same tokenizer for distilled and native) — Wathsala ↔ Thathsarani.
3. Fine-tuned artefact format for winner **and runner-up** (adapter weights + config + versioned eval log) — Thathsarani ↔ Karunanayake.
4. Shared fine-tuning configuration (rank, LR, epochs, seed, dataset split) — Wathsala ↔ Thathsarani, frozen before either runs the comparison.

### Shared config (fill in; nothing below is decided yet)

| Item | Decision | Owner | Status |
|---|---|---|---|
| Placeholder base model until Wathsala's checkpoints exist | **Recommended (Ekanayake): one ~1.5B-parameter instruct model for everyone**, same tokenizer family as the student; Phi-3 Mini (3.8B, in PR #1) kept only as an optional strong-model reference. Name/version: *TBD* | Wathsala picks (student size must match) | Pending group reply |
| Why not Phi-3 Mini for all | Native baseline must equal the distilled student's size (≈0.5–1.5B); 3.8B is tight for LoRA/HydraLoRA/QAT on mid-range hardware; weakens the small-model efficiency claim vs MATS | — | Rationale |
| Checkpoint format | Proposed: Hugging Face folder (`config.json`, safetensors, tokenizer files); same tokenizer for distilled and native | Wathsala ↔ Thathsarani | Pending |
| Training platform | Not recorded anywhere (local mid-range GPU vs Kaggle T4/P100 vs Colab T4). Each member records theirs | each member | Pending |
| GPU memory cap | **the same mid-range memory cap for every training/eval run**, even on larger cloud GPUs, so results are comparable; record actual GPU + peak VRAM beside each result | all | Proposed |
| Exact model/version, seeds, LoRA rank/LR/epochs, data split | Freeze in this table before the first comparison run | Wathsala ↔ Thathsarani | Pending |

Note: Agent 1's execution-accuracy numbers so far used phi3 (3.8B) via Ollama as a stand-in generator; they must be re-run on the agreed model (≈30 min per configuration).

### Research protocol (all members) — how we get trustworthy results

Ordered by value; items 1–3 first if time is short.

1. **Fine-tune before comparing.** Off-the-shelf phi3 scores only ≈0.40 on our Chinook/Spider test; differences between LoRA vs HydraLoRA or QAT vs PTQ only show on a model already trained for SQL. First deliverable: standard LoRA baseline on Spider **train**.
2. **Train with Agent 1's context format.** Pruning hurt phi3 partly because phi3 never saw pruned schemas in training. Fine-tune on pruned, multi-anchor context (same `ddl` format as inference) and test whether pruning then helps. Untested — the most promising idea for Agent 1. (Compare train-on-full-schema vs train-on-pruned, same model/seeds.)
3. **Freeze one shared setup:** one base model, one config (rank, LR, epochs, seeds), one train/val/test split; keep `eval/*.json` and Spider dev out of every training set; log everything needed to reproduce.
4. **Bigger test set + repeated runs.** n≈128 scored queries gives wide CIs (why several differences were not significant). Move headline results to the full Spider dev set (≈1,000 questions); run every fine-tune with **3 seeds**; keep paired comparisons (bootstrap CI, exact McNemar) and per-complexity-bucket reporting.
5. **Report an upper bound.** For retrieval: feed the **gold** tables/columns and measure accuracy — shows the headroom left for better retrieval and makes a neutral result interpretable. Equivalent oracle/ceiling for each agent (e.g. unquantized model for Agent 4).
6. **Report effect sizes, not just significance:** differences with 95% CIs, plus tokens, latency and VRAM beside accuracy. A well-measured neutral/negative result is a valid dissertation result.
7. **Optional harder benchmark:** BIRD, to test multi-join weakness more convincingly than Spider, if time allows.

---

## 1. Agent 1 — J.K.B. Ekanayake: Retrieval & Column-Level Pruning

Status: **Phases 1–7 below are implemented** (see CLAUDE.md for results and commands).

| Phase | Months | Build | Done when | Status |
|---|---|---|---|---|
| 1 Core engine | 1–2 | Schema reflection + FK graph; four modes (semantic, structural, hybrid, hybrid+pruning); pruning (keys kept → lemma overlap → spaCy similarity); `classify_sql`; evaluation harness (tokens, latency, table/column P/R by bucket) | all four modes run on Chinook; tests pass | Done |
| 2 Tune | 2–3 | Sweep depth × threshold; fix stop-word bug; `labels` ablation | decisions recorded with numbers | Done |
| 3 Datasets | 3 | Spider (120 stratified pairs) and TPC-H loaders; per-pair DB support | evaluation runs on 3 datasets, deterministic | Done |
| 4 Interfaces | 3–4 | NL complexity classifier; JSON handoff contract (`Agent1`) | contract test passes | Done (format awaiting Agent 3 sign-off) |
| 5 Execution metric | 4 | Execution accuracy with stand-in SLM; paired bootstrap + McNemar | result with CI reported | Done (phi3 stand-in; result: pruning −44 tokens, exec .40→.35, p=0.33) |
| 6 Harness | 4–5 | FastAPI `/retrieve` + `/query`, logged handoffs, bounded retry | smoke test end to end | Done |
| 7 Fix multi-join | 5 | Try `labels=True` as default; widen context on retry; depth-2 only for predicted multi-join; maybe retrieved-table-count feature for the NL classifier | multi-join exec ≥ hybrid on Spider dev, or documented as limitation | Done: multi-anchor + shortest-path bridging fixes multi-join table recall (.75→.94); pruned config `multi_anchors=3, gate=False, min_cols=8` matches hybrid accuracy (.41) at fewer tokens than 3-anchor hybrid; no accuracy gain over hybrid with phi3 |
| 8a Strengthen evidence (can start now) | 5–6 | Oracle upper bound (gold tables/columns as context); extend evaluation to the full Spider dev set (≈1,000 questions); re-run on the agreed ~1.5B placeholder model instead of phi3 | headroom number + tighter CIs; results recorded in CLAUDE.md | To do (needs placeholder model decision) |
| 8b Train-with-pruned-context | 6–7 | Coordinate with Thathsarani: fine-tune the same model on full vs pruned/multi-anchor context (3 seeds, shared config) and compare execution accuracy | answer to "does pruning help once the model is trained for it?" | Blocked on shared config + Agent 3 |
| 8 Re-run with real model | 7 | Repeat Phase 5 with Agent 3's fine-tuned model (and quantized variant); final tables for the thesis | final per-bucket results, CIs | Blocked on Agent 3 |
| 9 Integration & report | 9–12 | End-to-end feasibility on Chinook/Spider/TPC-H, latency check (<500 ms retrieval), write-up | feasibility demo + dissertation chapter | To do |
| 10 Unseen-database test | 6 | Northwind (13 tables, ~625k rows) as SQLite and PostgreSQL; 20 gold pairs (`eval/northwind_pairs.json`) | retrieval and execution measured on a database Agent 1 was never tuned on | Done (colR .99, pruning −24–28% tokens, exec parity; 3 bugs fixed) |
| 11 Value-coded data | 6 | Sample values of code columns in the schema (`value_hints`), per-database glossary (`glossary`, `J26_GLOSSARIES`), value-coded test set (`eval/value_coded_pairs.json`, 16 pairs, 9 DBs). See section 6 | measured with vs without on value-coded + ordinary sets | Done (value-coded exec .31→.69 phi3, .12→.56 Qwen-Coder, p=.016) |

Risks: pruning hurts multi-join and abbreviated schemas (TPC-H); result with phi3 is neutral — claim measurement rigor, not guaranteed gains (see `Market_Research_Comparable_Systems.md`: GRASP/RASL are stronger on retrieval technique; read before finalising methodology).

---

## 2. Agent 2 — W.A.T. Wathsala: Foundation Model via Knowledge Distillation (critical path)

Why first: Agent 3 cannot do its real comparison until the two base models exist; compute-heavy (teacher inference needs rented GPU).

| Phase | Months | Build | Done when | Hands off |
|---|---|---|---|---|
| 1 Select & freeze | 1 | Pick teacher (~7B, strong at SQL/code) and student size (≈0.5B–1.5B) matched to the native baseline; confirm both fit mid-range hardware for fine-tuning; pick the native baseline of identical parameter count and tokenizer family. *Proposed:* decide candidates by a 1-day smoke test (load, generate, fine-tune 50 steps) | model cards chosen, versions pinned, fit verified | Config to Thathsarani |
| 2 Prompt pool | 1 | Build ~1,500–3,000 prompts: general reasoning/instruction + SQL-adjacent schema comprehension. *Proposed:* seed SQL-adjacent prompts from Spider **train** schemas (not dev/eval pairs) to avoid leakage into evaluation | pool documented, no overlap with `eval/*.json` | — |
| 3 Teacher generation | 1–2 | Run teacher (inference only) over the pool on rented GPU; log prompt, response, params; dedupe/filter obvious failures. Budget cap from proposal: LKR 35k compute + 10k contingency | dataset versioned (e.g. JSONL + hash) | — |
| 4 Student training | 2–3 | Standard supervised fine-tuning of student on teacher responses; fixed seed, saved config | student checkpoint + training log | — |
| 5 Pre-FT comparison | 3 | Distilled vs native on **general reasoning** before any SQL tuning; paired comparison (bootstrap/McNemar from `stats.py`) | table with CI; decision recorded | Early result for report |
| 6 Hand-off | 3–4 | Deliver **both** base checkpoints (distilled, native) + shared fine-tuning config agreed with Agent 3 | Agent 3 can load both, same tokenizer | → Thathsarani |
| 7 Post-FT support | 6–7 | After Agent 3 fine-tunes both identically: exact-match + execution accuracy by bucket (`execution.py`, `classify_sql`) | per-bucket distilled-vs-native table | Final finding |
| 8 Report/integration | 9–12 | Write-up; support end-to-end tests | chapter + feasibility support | — |
| 9 Value-coded data (new, see section 6) | 2–3 | Include prompts where the schema carries value comments (`Sex VARCHAR(1) /* values: 'F', 'M' */`) in the SQL-adjacent part of the distillation pool, so the student learns to read them | some teacher prompts use Agent 1's value-hinted schema format | — |

Risks: scope creep of the distillation set (keep proof-of-concept scale); unfair comparison if the native model differs in anything but construction method (tokenizer, size, steps) — enforce identical post-distillation fine-tuning; compute overruns delay everyone, so Phase 3 gets the contingency budget. Possible negative result (no advantage) is reportable.

---

## 3. Agent 3 — K.G.Y.V. Thathsarani: LoRA vs HydraLoRA + Live Generation

Parallel-work fix: run the full comparison immediately on an off-the-shelf placeholder base, re-validate on Agent 2's base once delivered.

| Phase | Months | Build | Done when | Hands off |
|---|---|---|---|---|
| 1 Dataset | 2–3 | Text-to-SQL training/eval data labelled by complexity. *Proposed:* start from Spider **train** (≈6k non-nested, labelled via `classify_sql`; bucket counts: simple 1,815 / single-join 858 / multi-join 396 / aggregation 2,912) and over-sample multi-join; use the shared schema context format from Agent 1 (`ddl` field, pruned) so training matches inference; keep `eval/*.json` held out | bucket sizes checked, splits fixed, no leakage | Shared with Agent 4 |
| 2 Standard LoRA baseline | 3–4 | PEFT LoRA on a placeholder base (control condition); fixed seeds | trains within the mid-range memory budget; exact-match + execution accuracy baseline | — |
| 3 HydraLoRA module | 4–6 | Custom module: shared A, multiple B heads (one per bucket); **hard-coded routing** via the shared classifier (deliberate design choice: auditable, avoids gating collapse — state this in the thesis). Build incrementally, validate on a tiny subset first (PEFT has no multi-head B) | unit test: correct head receives each example; param count reported | — |
| 4 Placeholder comparison | 4–6 | LoRA vs HydraLoRA, identical base/data/epochs/budget; metrics: exact-match, JOIN/aggregation accuracy, trainable params, per bucket with paired stats | winner + runner-up identified | early finding |
| 5 Re-validation | 6–7 | Re-run on Agent 2's distilled and native bases (shared config); shorter pass | table for both bases | — |
| 6 Hand-off packaging | 7–8 | Package **winner and runner-up** as versioned artefacts (weights, config, eval log) | Agent 4 can load both | → Karunanayake |
| 7 Live sub-agents | 8–9 | Head-Selection (uses `complexity` from Agent 1 payload) + Generation sub-agent (consumes `ddl`, honours retry `hint`); expose as `generate(question, ddl, hint=None) -> sql` to drop into `harness.create_app` | harness `/query` works with the real generator | → harness |
| 8 Report/integration | 8–12 | Analysis, thesis chapter, end-to-end tests | — | — |
| 9 Value-coded data (new, see section 6) | next training run | Build training prompts with the SAME schema format used live: Agent 1's `ddl` with value comments (`Agent1(db, **agent1_retrieval.LIVE).run(q)["ddl"]`, the live config). Train-test mismatch otherwise: a model never trained on `/* values: ... */` may ignore it. Evaluate on `eval/value_coded_pairs.json` as well as the shared sets | value-coded exec reported for LoRA and HydraLoRA | — |

Risks: HydraLoRA custom implementation bugs; thin multi-join data; a reviewer asking why routing isn't learned (answer ready). Novelty is the strongest of the four, but HydraLoRA itself is not new — cite arXiv 2404.19245 and frame the contribution as complexity routing for SQL.

---

## 4. Agent 4 — K.M.I.N. Karunanayake: Quantization (QAT vs PTQ), Cross-Check, Execution

Parallel-work fix: build tooling now, run an early QAT-vs-PTQ pass on a self-fine-tuned placeholder, re-run on Agent 3's real artefacts.

| Phase | Months | Build | Done when | Hands off |
|---|---|---|---|---|
| 1 Tooling | 3–4 | llama.cpp setup; conversion to GGUF; AWQ path; measurement of VRAM and latency per configuration; *proposed:* reuse `execution.exec_match` and `classify_sql` | any model → quantized variant → measured | — |
| 2 Error-rate metrics suite | 4–6 | Separate **syntax validity** (query compiles: `EXPLAIN`) from **logical correctness** (JOIN/aggregation result match via `exec_match`), by bucket | suite validated on a placeholder model | — |
| 3 Placeholder pass | 5–6 | Self-fine-tune a small placeholder (plain LoRA); run PTQ (8/4-bit, GGUF/AWQ) and QAT at the same bit-rates; accuracy-vs-bit-rate curves | early standalone finding; pipeline proven | early finding |
| 4 Core comparison | 7–8 | Same on Agent 3's **winning** architecture: unquantized ceiling, PTQ baseline, QAT; find the bit-level inflection point per bucket | winning strategy identified with CIs | — |
| 5 Cross-check | 8 | Apply the winning strategy to Agent 3's **runner-up**; same bit-rates/protocol; report ranking stable or reversed | cross-architecture result (reversal is a valid finding) | — |
| 6 Live sub-agents | 8–9 | Execution sub-agent (read-only SQL run; `harness.run_sql` is the stand-in); Error-Diagnosis sub-agent: classify error (no such column/table, ambiguous, syntax) → hint back to Agent 3's generator within the bounded retry. *Starting point:* the reference prototype's "smart hint" categories | harness retry fixes cases the raw-error hint cannot | → harness |
| 7 Deployment model | 8–9 | Final deployment-ready quantized model, fits mid-range hardware, latency reported | end-to-end run on target hardware | — |
| 8 Report/integration | 9–12 | Analysis, thesis chapter, feasibility testing | — | — |
| 9 Empty-result check (new, see section 6) | with phase 6 | In the Error-Diagnosis sub-agent: when a query with a `WHERE`/`HAVING` filter returns **0 rows**, look up the filtered column's actual values (read-only, `agent1_retrieval.linking.code_values` or one bounded `SELECT DISTINCT ... LIMIT 7`) and retry once with a hint, e.g. "no rows matched 'yes'; Discontinued contains '0', '1'". Treat it as a soft failure: at most one retry, then return the empty result. Measure on `eval/value_coded_pairs.json` | retry recovers value mistakes that hints missed | → harness |

Risks: depends on Agent 3's artefacts (mitigated by placeholder pass); equal-budget fairness between QAT and PTQ; need to distinguish this from arXiv 2607.25583 ("How Small Can You Go?") in the literature review.

---

## 5. Integration phase (all, Months 9–12)

1. Replace harness stand-ins with real Agent 3 `generate` and Agent 4 `execute`/diagnosis; keep JSON-lines trace logging.
2. End-to-end evaluation on Chinook / Spider dev / TPC-H: execution accuracy by bucket, VRAM, latency; compare to MATS' published figures (efficiency framing: one shared model + adapters + quantization on mid-range hardware vs MATS' 9B/five models/24GB).
3. Feasibility demonstration only — the four independent studies carry the novelty claims, not the assembled system.
4. Dissertation write-up, paper, final presentation.

## 6. Value-coded data: a shared issue, one job per member (added 19 Oct 2026)

**The problem (found live on Northwind).** "Which products are discontinued?" produced `WHERE Discontinued = 'yes'` and returned 0 rows, because the column stores `'1'`/`'0'`. The model sees column names and types, not what the values look like or mean. Bank data is full of such codes (`acct_status = 'C'`, `kyc_flag = 'Y'`, `txn_type = 'WDL'`). The query does not fail, so nothing retries: the user just gets an empty or wrong answer.

**The rule for every fix: it must work on any connected database.** Everything goes through the read-only door `agent1_retrieval/db.py` (SQLite and PostgreSQL, the dialects whose read-only mode is enforced), uses portable SQL, stays cheap on very large tables, and never copies personal data into a prompt.

| Layer | Owner | What | Status |
|---|---|---|---|
| Show the codes | Ekanayake (Agent 1) | `value_hints`: columns with ≤ 6 short values that repeat across rows are shown as `Sex VARCHAR(1) /* values: 'F', 'M' */` and are kept through pruning. Judged on a 1,000-row sample, then one bounded `DISTINCT` (whole Northwind, 625k rows: 19 ms SQLite, 242 ms PostgreSQL). Columns whose values are all different (names, emails, account numbers) are never shown; off for databases in `J26_NO_VALUE_LINKING`. On in the live app (`LIVE` config) | **Done** |
| Explain the codes | Ekanayake (Agent 1) | Per-database glossary `{"Table.Column": "C = closed, A = active"}`, from the institution's data dictionary: `J26_GLOSSARIES='{"bank": "bank_glossary.json"}'` or `Retriever(glossary=...)` / `evaluate --glossary`. Configuration, not data, so it applies even where value reading is off | **Done** |
| Measure it | Ekanayake (Agent 1) | `eval/value_coded_pairs.json`: 16 questions on 9 databases whose wording never contains the stored code | **Done** |
| Train on it | Thathsarani (Agent 3) | Training prompts must use the same schema format as live, value comments included (section 3, phase 9) | To do |
| Teach it | Wathsala (Agent 2) | Some SQL-adjacent distillation prompts use the value-commented schema (section 2, phase 9) | To do |
| Catch what slips through | Karunanayake (Agent 4) | Empty-result check in error diagnosis: 0 rows after a filter → look up the column's real values → one retry with a hint (section 4, phase 9) | To do |
| Show the user | Shared (chat page) | The SQL is already shown; add a note on empty answers ("no matching rows; check the filter") | To do |

**Measured effect of value hints (Agent 1, hybrid_pruned, recommended config, 19 Oct 2026):**

| Test set | Model | Without hints | With hints | Paired test |
|---|---|---|---|---|
| Value-coded, 16 questions | phi3 | 0.31 | **0.69** | 8 vs 2 discordant, McNemar p = 0.11 |
| Value-coded, 16 questions | Qwen2.5-Coder-1.5B | 0.12 | **0.56** | 7 vs 0, **p = 0.016** |
| Chinook + Spider + Northwind, 148 questions | phi3 | 0.432 | 0.446 | 4 vs 2, p = 0.69 (no harm) |
| Chinook + Spider + Northwind, 148 questions | Qwen2.5-Coder-1.5B | 0.446 | 0.466 | 5 vs 2, p = 0.45 (no harm) |

Cost: about +17 tokens per question on the ordinary sets (+29 on value-coded). Models are untrained stand-ins; re-measure with Agent 3's fine-tuned model.

## 7. Cross-member dependency summary

```
Agent 1 (Months 1–5, done) ──┐
                             ├──> Agent 3 (placeholder M3–6, real M6–9) ──> Agent 4 (placeholder M4–6, real M7–9) ──> Integration M9–12
Agent 2 (M1–4, critical)  ───┘
```

Weekly sync checklist: Agent 2 delivery date vs Agent 3 re-validation slot; Agent 3 runner-up artefact format agreed before Month 6; shared fine-tuning config frozen; compute budget burn (Agent 2 is the largest, LKR 61k total).
