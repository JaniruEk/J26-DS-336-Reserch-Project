# Execution Plan — J26-DS-336 (all four members, phase by phase)

Derived from the individual proposals' WBS/Gantt and the project scope. Months are project months (Month 1 = kickoff). Each phase lists **what to build**, **done when** (exit criteria) and **hands off**. Items marked *proposed* are suggestions not yet agreed with the owner.

*Last updated 19 Oct 2026: status of all four members after PRs #6, #14 and #15 (each section's Status/Progress note); Agent 2 keeps a 0.5B student for PP1; Agent 4 scope changed to adaptive mixed-precision quantization (section 4); shared assets, shared config, research protocol, Agent 1 phases 8–13, teammates' progress, value-coded data (section 6), security and deployment (section 8), reports and wording fixes (section 9).*

## 0. Shared assets already in this repo (reuse, don't rebuild)

| Asset | Where | Used by |
|---|---|---|
| Complexity taxonomy from SQL (`classify_sql`) — labels any (question, SQL) pair as simple / single-join / multi-join / aggregation | `agent1_retrieval/complexity.py` | Agent 3 dataset labelling; Agent 4 stratified evaluation |
| NL complexity classifier (`classify_query`), live, pre-retrieval (Spider dev acc 0.57) | `agent1_retrieval/complexity.py`, `complexity_nl.joblib` | Agent 3 head routing |
| Eval sets with gold SQL: Chinook (14), TPC-H (14, schema only), Spider dev stratified (120), Northwind (20, unseen database), value-coded (16, 9 databases) | `eval/*.json`, databases via `scripts/` (Northwind: `data/northwind.db`) | everyone's evaluation |
| Execution-match scorer (row multiset vs gold) and paired stats (bootstrap CI, exact McNemar) | `agent1_retrieval/execution.py`, `stats.py` | Agents 2, 3, 4 accuracy comparisons |
| Handoff contract Agent 1 → Agent 3 (`Agent1.run` dict: `query, complexity, mode, anchor, matched, tables, ddl, tokens, latency_ms, trace`). `matched=False` = off-topic question, declined before generation; `ddl` may carry column comments (`/* values: 'F', 'M' */`, glossary meanings) — *Thathsarani to confirm* | `agent1_retrieval/agent.py` | Agent 3 prompt construction |
| Agent 1 settings: `RECOMMENDED` (research config, fixed so results reproduce: 3 anchors, ungated, narrow tables whole, rich linking) and `LIVE` (= `RECOMMENDED` + value hints, the app default) | `agent1_retrieval/retrieval.py` | Agent 3 training prompts must use `LIVE` |
| Read-only database layer: SQLite files or PostgreSQL URLs; read-only connection, one statement per call, timeout, passwords hidden in errors. Other server dialects are refused | `agent1_retrieval/db.py` | every agent that touches data |
| Copy any SQLite database into PostgreSQL (for server-database tests) | `scripts/load_postgres.py` | testing |
| FastAPI harness: `/query` (Agent 1 → generate → execute, bounded retry, JSON-lines handoff log), `/retrieve`, `/health`, `/dbs`; SQL guard (SELECT/WITH only, `BLOCKED` = refused, not retried); generator down → 503. Agents 3/4 pluggable via `create_app(generate=, execute=)` | `harness/app.py` | integration phase |
| Web pages: chat (`/chat`, answer + SQL + per-agent trace + "Save as chart") and Retrieval Explorer (`/`, Agent 1's four modes, kept/removed columns and why) | `harness/chat.html`, `harness/explorer.html` | demos, panel |
| BI integration ("explore, then promote"): save a `/query` answer by its trace id, replay its frozen SQL as CSV (`/answers/{id}.csv`, for Power BI Report Server, Excel, Grafana, Tableau) or push it to Superset as a chart. The model is never on the dashboard refresh path | `harness/bi.py` | dashboards, demos |
| Configuration by environment: `J26_DATABASES` (extra databases), `J26_NO_VALUE_LINKING` (personal-data databases: never read values), `J26_GLOSSARIES` (per-database data dictionary), `SUPERSET_URL/USER/PASSWORD/DATABASES` | `harness/app.py`, `harness/bi.py` | deployment |
| Generator stand-in: local phi3 or Qwen2.5-Coder-1.5B-Instruct via Ollama. Interface `generate(question, ddl, hint=None, dialect=...)`; `dialect` is passed only for server databases ("PostgreSQL") | `agent1_retrieval/execution.py` | placeholder until real models exist |

**Rules for fair comparison (all members):** same evaluation pairs, same mid-range hardware budget, one variable changed at a time, report per complexity bucket and with paired statistics — not a single aggregate. A negative result is a valid result.

**Open interface decisions to lock early (Month 1–2):**
1. Agent 1 → Agent 3 payload format (JSON with DDL inside, as implemented) — Ekanayake ↔ Thathsarani.
2. Base-model checkpoint format and tokenizer (e.g. HF safetensors + same tokenizer for distilled and native) — Wathsala ↔ Thathsarani.
3. Fine-tuned artefact format for winner **and runner-up** (adapter weights + config + versioned eval log) — Thathsarani ↔ Karunanayake.
4. Shared fine-tuning configuration (rank, LR, epochs, seed, dataset split) — Wathsala ↔ Thathsarani, frozen before either runs the comparison.

### Shared config (base model agreed 19 Oct 2026; the rest not frozen yet)

| Item | Decision / current state | Owner | Status |
|---|---|---|---|
| Base model | **Qwen2.5-1.5B-Instruct** (`Qwen/Qwen2.5-1.5B-Instruct`, general, not Coder; Apache 2.0; 28 layers): fine-tuned by Agent 3 and quantized by Agent 4, and the target size for Agent 2's distilled and native students. **Exception until after PP1:** Agent 2's current students are Qwen2.5-0.5B-Instruct (no time to redo them at 1.5B before PP1); she moves to 1.5B after PP1 if she finishes it, otherwise the 0.5B results stand as her finding. Until then Agent 2's checkpoints cannot be dropped into Agent 3's 1.5B pipeline. Teacher should share its tokenizer: **Qwen2.5-7B-Instruct** (Apache 2.0) — *Wathsala to confirm*. The research report had recommended the Coder variant; the general model is what Agent 3 already trains on. **Still to move over:** Inushki's Phi-3 Mini 3.8B work (keep as preliminary results); Agent 1 stand-ins (phi3, Qwen2.5-Coder-1.5B via Ollama) → re-run on Qwen2.5-1.5B-Instruct | whole team | **Agreed 19 Oct 2026** |
| Why not Phi-3 Mini | Native baseline must equal the distilled student's size (≈0.5–1.5B); its ~7B sibling uses a different tokenizer; 3.8B is tight for LoRA/HydraLoRA on mid-range hardware (QLoRA only); Agent 4's layer allocation must be re-measured on whichever model ships; weakens the small-model efficiency claim vs MATS | — | Rationale |
| Checkpoint format | Agent 2 → 3: Hugging Face folder (`config.json`, `generation_config.json`, safetensors, tokenizer, chat template), private HF Hub repo, tags `native-v1` / `distilled-v1`, base commit hash recorded. Agent 3 → 4: PEFT adapter folders for LoRA; HydraLoRA = weights + `hydra_config.json` (head ↔ bucket map) + merged per-head folders. Agent 4 → deployment: GGUF (llama.cpp) and AWQ via llm-compressor (AutoAWQ is archived). See `reports/Deployment_runtime_plan.md` | Wathsala ↔ Thathsarani ↔ Karunanayake | Proposed |
| Training platform | Thathsarani: Google Colab (laptop has no NVIDIA GPU). Others: *not recorded*. Advice: Kaggle **T4 x2, never P100** (P100 is below the minimum for Unsloth and AWQ, no bf16); pin one platform for all reported runs | each member | Partly recorded |
| GPU memory cap | **the same mid-range memory cap for every training/eval run**, even on larger cloud GPUs, so results are comparable; record actual GPU + peak VRAM beside each result (Thathsarani's LoRA run: peak 5.62 GB) | all | Proposed |
| Exact model revision (HF commit hash), seeds, LoRA rank/LR/epochs, data split | Freeze in this table before the first comparison run | Wathsala ↔ Thathsarani | Pending |

Note: Agent 1's PP1 execution numbers used phi3 (3.8B) as the stand-in generator. Northwind and value-coded results were also measured with Qwen2.5-Coder-1.5B-Instruct. All must be re-run on Qwen2.5-1.5B-Instruct and on Agent 3's fine-tuned model (≈30 min per configuration).

### Research protocol (all members) — how we get trustworthy results

Ordered by value; items 1–3 first if time is short.

1. **Fine-tune before comparing.** Off-the-shelf phi3 scores only ≈0.40 on our Chinook/Spider test; differences between LoRA vs HydraLoRA or between quantization settings only show on a model already trained for SQL. First deliverable: standard LoRA baseline on Spider **train**.
2. **Train with Agent 1's context format.** Pruning hurt phi3 partly because phi3 never saw pruned schemas in training. Fine-tune on pruned, multi-anchor context (same `ddl` format as inference) and test whether pruning then helps. Untested — the most promising idea for Agent 1. (Compare train-on-full-schema vs train-on-pruned, same model/seeds.)
3. **Freeze one shared setup:** one base model, one config (rank, LR, epochs, seeds), one train/val/test split; keep `eval/*.json` and Spider dev out of every training set; log everything needed to reproduce.
4. **Bigger test set + repeated runs.** n≈128 scored queries gives wide CIs (why several differences were not significant). Move headline results to the full Spider dev set (≈1,000 questions); run every fine-tune with **3 seeds**; keep paired comparisons (bootstrap CI, exact McNemar) and per-complexity-bucket reporting.
5. **Report an upper bound.** For retrieval: feed the **gold** tables/columns and measure accuracy — shows the headroom left for better retrieval and makes a neutral result interpretable. Equivalent oracle/ceiling for each agent (e.g. unquantized model for Agent 4).
6. **Report effect sizes, not just significance:** differences with 95% CIs, plus tokens, latency and VRAM beside accuracy. A well-measured neutral/negative result is a valid dissertation result.
7. **Optional harder benchmark:** BIRD, to test multi-join weakness more convincingly than Spider, if time allows. Use BIRD Mini-Dev only as a secondary set: a 2026 audit found annotation errors in about half its items.
8. **Same decoding everywhere:** greedy decoding with fixed seeds; never compare greedy results with self-consistency (multi-sample) results, which many published small-model numbers use.
9. **Check the scorer:** cross-check our row-multiset scorer against Spider's official test-suite evaluator on the Spider items; single-database execution accuracy overstates test-suite accuracy by about 4–6 points in the literature.
10. **Sample size, pre-registered:** at the observed disagreement rate, detecting a 5-point difference needs about 600 paired questions (our own normal-approximation calculation); fix one primary comparison per agent in advance and apply Holm-Bonferroni to the rest. Per-bucket results are descriptive.
11. **Test on an unseen database too:** every agent reports Northwind (`eval/northwind_pairs.json`) next to the shared sets, so results are not tuned to Chinook/Spider.

---

## 1. Agent 1 — J.K.B. Ekanayake: Retrieval & Column-Level Pruning

Status (19 Oct 2026): **phases 1–8, 10 and 11 are done**; 9 is the next experiment; 8a can start now that the model is agreed (Qwen2.5-1.5B-Instruct; all phi3 / Qwen2.5-Coder numbers are preliminary); 8b and 12 wait on Agent 3; **14 is new and the most useful thing Agent 1 can do for the team** (Agent 3's results show the NL complexity classifier limits HydraLoRA); 13 is the final integration and write-up. Results and commands: `CLAUDE.md`, `reports/agent1_phase8/README.md`.

| Phase | Months | Build | Done when | Status |
|---|---|---|---|---|
| 1 Core engine | 1–2 | Schema reflection + FK graph; four modes (semantic, structural, hybrid, hybrid+pruning); pruning (keys kept → lemma overlap → spaCy similarity); `classify_sql`; evaluation harness (tokens, latency, table/column P/R by bucket) | all four modes run on Chinook; tests pass | Done |
| 2 Tune | 2–3 | Sweep depth × threshold; fix stop-word bug; `labels` ablation | decisions recorded with numbers | Done |
| 3 Datasets | 3 | Spider (120 stratified pairs) and TPC-H loaders; per-pair DB support | evaluation runs on 3 datasets, deterministic | Done |
| 4 Interfaces | 3–4 | NL complexity classifier; JSON handoff contract (`Agent1`) | contract test passes | Done (format awaiting Agent 3 sign-off) |
| 5 Execution metric | 4 | Execution accuracy with stand-in SLM; paired bootstrap + McNemar | result with CI reported | Done (first result, superseded by phases 7–8: default pruning −44 tokens, exec .40→.35, p=0.33) |
| 6 Harness | 4–5 | FastAPI `/retrieve` + `/query`, logged handoffs, bounded retry | smoke test end to end | Done; extended for PP1: chat page, Retrieval Explorer, off-topic decline (`matched`), SQL guard, 503 when the generator is down |
| 7 Fix multi-join | 5 | Try `labels=True` as default; widen context on retry; depth-2 only for predicted multi-join; maybe retrieved-table-count feature for the NL classifier | multi-join exec ≥ hybrid on Spider dev, or documented as limitation | Done: multi-anchor + shortest-path bridging fixes multi-join table recall (.75→.94); pruned config `multi_anchors=3, gate=False, min_cols=8` matches hybrid accuracy (.41) at fewer tokens than 3-anchor hybrid; no accuracy gain over hybrid with phi3 |
| 8 PP1 fixes | 5–6 | `linking.py`: compound/abbreviation splitting, business synonyms, read-only value linking; every column gets a reason (`trace` in the handoff); optional FK inference (`infer_missing_fks`); faster embedder (82 → 5.5 ms per question); `RECOMMENDED` setting used by the app | colR and exec re-measured on all sets | Done: colR Chinook .73→.95, TPC-H .46→.97, Spider .89→.98; exec (phi3, 128 scored) pruned **.43** @145 tokens vs hybrid .41 @171 (−16% tokens, McNemar p=.69): pruning now costs nothing. Retrieval latency median 278 ms, p95 380 ms, max 617 ms (n=148). Side finding: on simple questions single-table modes reach .68–.71 vs hybrid .39 — wide context distracts the model on easy questions |
| 8a Strengthen evidence (can start now) | 5–6 | Oracle upper bound (gold tables/columns as context); extend evaluation to the full Spider dev set (≈1,000 questions); re-run on Qwen2.5-1.5B-Instruct (agreed base) instead of phi3 | headroom number + tighter CIs; results recorded in CLAUDE.md | To do (unblocked: model agreed 19 Oct) |
| 8b Train-with-pruned-context | 6–7 | Coordinate with Thathsarani: fine-tune the same model on full vs pruned/multi-anchor context (3 seeds, shared config) and compare execution accuracy | answer to "does pruning help once the model is trained for it?" | Blocked on shared config + Agent 3 |
| 9 Complexity-adaptive width (next experiment) | 6–7 | From the phase 8 side finding: narrow context (anchor only) for questions predicted simple, multi-anchor context otherwise; compare with the fixed `RECOMMENDED` setting | exec by bucket with vs without adaptive width | To do |
| 10 Unseen-database test | 6 | Northwind (13 tables, ~625k rows) as SQLite and PostgreSQL; 20 gold pairs (`eval/northwind_pairs.json`) | retrieval and execution measured on a database Agent 1 was never tuned on | Done (colR .99, pruning −24–28% tokens, exec parity; 3 bugs fixed) |
| 11 Value-coded data | 6 | Sample values of code columns in the schema (`value_hints`), per-database glossary (`glossary`, `J26_GLOSSARIES`), value-coded test set (`eval/value_coded_pairs.json`, 16 pairs, 9 DBs). See section 6 | measured with vs without on value-coded + ordinary sets | Done (value-coded exec .31→.69 phi3, .12→.56 Qwen-Coder, p=.016) |
| 12 Re-run with real model | 7 | Repeat the execution evaluation with Agent 3's fine-tuned model (and Agent 4's quantized variant), on all sets incl. Northwind and value-coded; final tables for the thesis | final per-bucket results, CIs | Blocked on Agent 3 |
| 14 Better complexity classifier (new) | 7 | `classify_query` (TF-IDF + LogReg, Spider dev acc 0.57) routes HydraLoRA's heads. Agent 3 measured the cost: HydraLoRA with true labels 0.52 vs routed by `classify_query` 0.39 (18 vs 2 discordant, p < 0.001); single-join suffers most (0.65 → 0.35). Try: retrieved-table count / FK-path length from Agent 1's own retrieval as features (join count depends on the schema, not just the text); a small fine-tuned classifier; report per-bucket confusion | routing accuracy up, and HydraLoRA live-routed accuracy re-measured with Agent 3 | To do |
| 13 Integration & report | 9–12 | End-to-end feasibility on Chinook/Spider/TPC-H/Northwind (SQLite and PostgreSQL), latency check on the target hardware (<500 ms retrieval), write-up | feasibility demo + dissertation chapter | To do |

Also built (shared infrastructure, not research novelty): server-database support (`db.py`, PostgreSQL), BI integration (`harness/bi.py`), chat page and Retrieval Explorer — see section 0 and section 8.

Risks: with untrained stand-in models pruning has reached parity, not a gain — claim measurement rigor, not guaranteed accuracy gains (see `Market_Research_Comparable_Systems.md`: GRASP/RASL are stronger on retrieval technique; read before finalising methodology). Multi-join stays the weak bucket. Real bank schemas may use abbreviated or lower-case names (fixed for `firstname`-style compounds; `mandate` → man + date is a known mis-split). The "top 3 tables" setting can pull in a distractor table with same-named columns (Northwind: suppliers vs shippers).

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

Progress (from `Agent2/` notebooks on `main`, PRs #8 and #15, 19 Oct 2026): "Task 1" is a **DATABASE vs GENERAL question classifier**, teacher Qwen2.5-7B-Instruct, students Qwen2.5-0.5B-Instruct with LoRA (native, distilled, and distilled from a fine-tuned teacher); 4,000 train / 799 validation / 1,200 test, no overlap. Test accuracy (raw-text input): native 0.997 (4 errors in 1,200), distilled from the fine-tuned teacher 0.999 (1 error); no paired test run; both at the ceiling (TF-IDF + logistic regression already reaches 0.983), so the task leaves distillation no room to show an effect, and the fine-tuned teacher's soft targets are almost one-hot, i.e. close to plain label training. The student distilled from the un-tuned (prompted) teacher scored 0.92 on validation with the chat prompt it was trained on, but 0.59 on test because it was evaluated on raw text: a prompt mismatch at evaluation, not bad teacher labels (the prompted teacher's top class agreed with the labels on 90% of training rows, errors balanced). Re-evaluate it with its training prompt before reporting. **Gaps against the scope:** (1) the scope's question is multi-join/aggregation reasoning, not topic classification; (2) the student is 0.5B (kept for PP1 by team decision, 1.5B after PP1 if finished, see shared config); (3) the task overlaps Agent 1's `matched` off-topic gate. **Still missing:** the two base checkpoints (distilled, native) Agent 3 needs, an SQL-oriented distillation set, and the gold-SQL control arm. Method notes from the research report: add a control arm — the native model fine-tuned on the same prompts with gold-SQL targets — so a distillation gain is not just extra fine-tuning; keep only teacher responses whose SQL executes; draw teacher prompts only from Spider/BIRD **train**, never from the Spider dev databases used in `eval/`.

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

Progress (from `agent3_finetune/PROGRESS_LOG.md` on `main`, PR #6, 19 Oct 2026): first full comparison done, **preliminary** (Qwen2.5-1.5B-Instruct, rank 16, 1 seed, Spider + Chinook, 128 scored, about 31 questions per bucket). Execution accuracy: untrained base 0.41; standard LoRA **0.56** (vs base +0.13, p = 0.012; single-join +0.39); HydraLoRA with true bucket labels 0.52 (vs LoRA −0.05 [−0.11, +0.02], p = 0.21, not significant); HydraLoRA routed by Agent 1's `classify_query` **0.39** (vs LoRA −0.17, p < 0.001). The heads do specialise (each bucket scores best on its own head), so wrong routing is costly: true labels vs live classifier +0.12 (18 vs 2 discordant). Multi-join stays at ≈0.16 for every model. Preliminary decision: **winner LoRA** (not worse, 2.7x fewer parameters, no router, lower training memory), **runner-up HydraLoRA**. Stated limits: one seed, small buckets, untuned hyperparameters, multi-join head trained on only 654 rows, largest schemas dropped from training, full-schema (not pruned) evaluation context. Open: package winner and runner-up for Agent 4; live `generate(question, ddl, hint=None, **kw)` with head selection plugged into the harness (must accept `dialect=`); 3 seeds and full Spider dev; parameter-matched LoRA; re-run on Wathsala's bases (0.5B until after PP1, see shared config); train on Agent 1's pruned context (phase 8b of section 1).

---

## 4. Agent 4 — K.M.I.N. Karunanayake: Adaptive Mixed-Precision Quantization, Execution

**Scope (final, 19 Oct 2026; replaces QAT vs PTQ).** Instead of one bit-width for every layer, measure how much each transformer layer matters for SQL generation, keep the sensitive layers at INT8 and put the rest at INT4. Research question: *does a layer-wise INT4/INT8 model chosen by SQL-task sensitivity keep more accuracy per unit of GPU memory than uniform INT4, and come close to uniform INT8 with less memory, especially on multi-join and aggregation questions?* Model: **Qwen2.5-1.5B-Instruct** (28 layers), the team's base, first as released and then as fine-tuned by Agent 3; the final allocation is the one measured on Agent 3's fine-tuned winner. Earlier Phi-3 Mini work (32 layers) is kept as preliminary results and, if time allows, as a second-model check (is the sensitivity pattern similar across model families?).

**What is and isn't new.** Mixed precision itself is not new: HAWQ / HAWQ-V2 (Hessian-based per-layer bit-widths), OWQ, SpQR, SliM-LLM, and llama.cpp's own `Q4_K_M`, which already keeps some tensors (`attn_v`, `ffn_down`) at higher precision. The claim is narrower: whether **task-specific** sensitivity (measured on SQL generation, per complexity bucket) picks different layers from **generic** sensitivity (perplexity / llama.cpp importance matrix), and whether that matters for SQL accuracy. Verify these citations before using them.

**Fixed rules for the study.**
- Baselines at every comparison: FP16 (accuracy ceiling), uniform INT8, uniform INT4, llama.cpp `Q4_K_M` (existing heuristic mixed precision), and two controls with **the same number of INT8 layers**: randomly chosen layers (several draws) and layers chosen by generic sensitivity. Without the random control, "the sensitivity score helps" is not shown.
- Score sensitivity on a **calibration split** (Spider train questions), never on the test sets (`eval/*.json`, Spider dev).
- Rank layers with a continuous measure (drop in log-likelihood of the gold SQL, or KL divergence from the FP16 model's next-token distribution), then confirm with execution accuracy. Execution accuracy on a small set moves by whole questions and is mostly noise.
- Sweep the number of INT8 layers *k* (0 to all) and report the memory-vs-accuracy curve, not one cut-off.
- Measure memory and speed in the runtime that ships (llama.cpp GGUF, see `reports/Deployment_runtime_plan.md`), not only in bitsandbytes: INT4 vs INT8 speed depends on the runtime's kernels. Report peak GPU memory, model size on disk, tokens/s and latency per question.

Parallel-work fix: develop the method now on the released Qwen2.5-1.5B-Instruct (Agent 3's standard LoRA adapter already exists and can be used as soon as it is shared), then re-run it on Agent 3's final winner (and the runner-up for the cross-check).

| Phase | Months | Build | Done when | Hands off |
|---|---|---|---|---|
| 1 Pipeline and baseline | 3–4 | Spider SQL-generation pipeline (built on Phi-3 Mini; switch `MODEL_ID` to Qwen2.5-1.5B-Instruct and use the shared prompt/schema format); FP16 baseline; accuracy, latency and peak memory per question | baseline measured | — |
| 2 Uniform baselines | 4 | Uniform INT8 and INT4 (bitsandbytes now; GGUF `Q8_0` / `Q4_0` / `Q4_K_M` with llama.cpp) | accuracy-vs-memory point for each | — |
| 3 Error-rate metrics suite | 4–5 | Separate **syntax validity** (`EXPLAIN` succeeds) from **logical correctness** (`exec_match`), plus error classes (wrong join / column / aggregation / group by), by complexity bucket (`classify_sql`) | suite validated on FP16 vs INT4 | — |
| 4 Layer sensitivity | 5–6 | Quantize one layer at a time to INT4 (rest FP16) and score the damage on the calibration split, per layer and **per complexity bucket**; repeat with a generic score (perplexity on general text) for comparison | ranking stable when re-run on a second calibration sample (rank correlation reported) | — |
| 5 Precision allocation | 6 | Top-*k* layers to INT8, rest INT4; sweep *k*; check that the combined model behaves as the single-layer scores predicted (layers interact) | memory-vs-accuracy curve with the baselines and controls above | early finding |
| 6 Deployable mixed model | 6–7 | Build the mixed model as one GGUF with per-tensor types (`llama-quantize` per-tensor overrides; check the option on the pinned llama.cpp version); check its accuracy matches the research evaluation; measure memory and speed on mid-range hardware | GGUF runs in the harness through llama.cpp | → deployment |
| 7 Re-run on the real model | 7–8 | Phases 4–6 on Agent 3's **winner**, in the configuration that ships (quantized base with the adapters attached, see the runtime plan) | final allocation + test-set comparison with paired stats | → integration |
| 8 Cross-check | 8 | *Proposed (confirm with Karunanayake):* re-measure sensitivity on Agent 3's **runner-up**: is the layer ranking the same (rank correlation), and does the winner's allocation still work on it? | stable or different (both are valid findings) | — |
| 9 Live sub-agents | 8–9 | Execution sub-agent (read-only SQL run; `harness.run_sql` is the stand-in); Error-Diagnosis sub-agent: classify the error (no such column/table, ambiguous, syntax; `src/error_classifier.py` from Day 5 is the starting point) → hint back to Agent 3's generator within the bounded retry | harness retry fixes cases the raw-error hint cannot | → harness |
| 10 Empty-result check (see section 6) | with phase 9 | When a query with a `WHERE`/`HAVING` filter returns **0 rows**, look up the filtered column's actual values (read-only, `agent1_retrieval.linking.code_values` or one bounded `SELECT DISTINCT ... LIMIT 7`) and retry once with a hint, e.g. "no rows matched 'yes'; Discontinued contains '0', '1'". Soft failure: at most one retry, then return the empty result. Measure on `eval/value_coded_pairs.json` | retry recovers value mistakes that hints missed | → harness |
| 11 Report/integration | 9–12 | Analysis, thesis chapter, feasibility testing | — | — |

Risks: (1) **noisy sensitivity signal**: small per-layer differences are within sampling noise (see progress); (2) layers interact, so the sum of single-layer scores can mislead (phase 5 check); (3) an allocation found on the released model may not transfer to the fine-tuned one (phase 7 re-run); on a 1.5B model the absolute memory saving is small, so report accuracy kept per unit of memory; (4) the deployed runtime may not support every per-layer mix, or INT8 layers may cost speed (measure in llama.cpp); (5) a reviewer saying "this is `Q4_K_M` / HAWQ": answer with the generic-vs-task-specific comparison.

Progress (from her branches, 19 Oct 2026): phases 1–2 and first versions of 3–5 done on **Phi-3 Mini**: Spider pipeline and FP16 baseline; bitsandbytes INT8 and INT4 (NF4) baselines (Day 4, 100 questions on one database, concert_singer, not the Spider dev set: execution accuracy FP16 75, INT8 79, INT4 67; mean peak memory FP16 ≈4.6 GB, INT8 ≈3.9 GB, INT4 ≈2.4 GB; bitsandbytes INT8 was slower than INT4); error summary, 83/100 correct (Day 5); single-layer sensitivity with simulated (fake) per-row INT4 over all 32 layers on 25 questions (Day 6); top-4 layers (11, 14, 29, 31) to INT8, rest INT4 (Day 7, PR #9). **Caveat:** on 25 questions one question = 0.04, and most layers change execution accuracy by 0 or 1 question (largest drop: layer 29, 3 questions; some scores are negative, i.e. quantizing "helped"), so the current ranking is mostly noise. **Update 20 Oct 2026 (PR #16, merged): moved to Qwen2.5-1.5B-Instruct and built the mixed model.** Same method on the 28 layers (25 questions, single-layer INT4); 6 layers to INT8 (6, 8, 10, 11, 14, 16), 22 to INT4; the model is built with real bitsandbytes modules (`Linear8bitLt` / `Linear4bit` per layer, `scripts/qwen_build_adaptive.py`). Results (bitsandbytes, released model, not fine-tuned): on 100 questions FP16 EX 0.59, INT8 0.61, INT4 **0.51**; peak memory FP16 ≈2.97 GB, INT8 ≈1.74 GB, INT4 ≈1.20 GB, mixed ≈1.29 GB; median latency FP16 3.0 s, INT8 9.6 s (bitsandbytes INT8 is slow), INT4 2.6 s, mixed 3.1 s. The mixed model was scored on only 25 questions (EX 0.64); on those same 25, FP16 0.68, INT8 0.64, INT4 0.68 — differences of 1–2 questions, so **no difference can be claimed yet**. **Two problems to fix before PP2:** (1) the 25 test questions are the same 25 used to choose the INT8 layers (test = calibration), so the mixed model's score is optimistic; (2) the sensitivity scores still move in steps of one question (0.04), and the chosen layers differ from the rest by at most 3 questions. The useful signal so far is INT4's 8-point drop on 100 questions (0.59 → 0.51): the next run should score the mixed model on those 100 (or more, held-out) questions, pick layers on a separate calibration set, and add the random-layer and `Q4_K_M` controls. Next: a continuous score on a larger calibration split (phase 4); build and evaluate the mixed model itself (not built yet); add the random-layer and `Q4_K_M` controls. The fake INT4 (per-row, symmetric) also differs from the GGUF/NF4 formats that would be deployed; score with the target format where possible.

Phase 6 guarantee: the real Execution sub-agent must keep what the stand-in enforces today — read-only connection, one statement per call, statement timeout, refusal (not retry) of non-SELECT SQL — by calling `agent1_retrieval/db.py` rather than opening its own connection.

---

## 5. Integration phase (all, Months 9–12)

1. Replace harness stand-ins with real Agent 3 `generate` and Agent 4 `execute`/diagnosis; keep JSON-lines trace logging.
2. Switch the model runtime as planned in `reports/Deployment_runtime_plan.md`: Ollama until PP1 (done), Hugging Face transformers + PEFT for research evaluation, `llama-cpp-python` inside the application for deployment (loads Agent 4's GGUF and Agent 3's adapters directly; no separate model server). Quantize the configuration that will actually be deployed.
3. End-to-end evaluation on Chinook / Spider dev / TPC-H / Northwind, on SQLite **and** PostgreSQL, plus the value-coded set: execution accuracy by bucket, VRAM, latency; compare to MATS' published figures (efficiency framing: one shared model + adapters + quantization on mid-range hardware vs MATS' 9B/five models/24GB).
4. BI demo: question → answer → "Save as chart" → dashboard replaying the frozen SQL (Superset or Power BI Report Server via the CSV link).
5. Feasibility demonstration only — the four independent studies carry the novelty claims, not the assembled system.
6. Dissertation write-up, paper, final presentation.

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
                             ├──> Agent 3 (placeholder M3–6, real M6–9) ──> Agent 4 (method on released Qwen M3–6, fine-tuned model M7–9) ──> Integration M9–12
Agent 2 (M1–4, critical)  ───┘
```

Weekly sync checklist: Agent 2 delivery date vs Agent 3 re-validation slot; Agent 3 runner-up artefact format agreed before Month 6; shared fine-tuning config frozen; compute budget burn (Agent 2 is the largest, LKR 61k total).

## 8. Security and deployment (shared infrastructure; not a research contribution)

The system is a standalone on-premise appliance: one instance in the institution's own data centre, reached by branches over its private network. The model and the data never leave that network; no outside AI vendor is involved.

| Area | What is in place (19 Oct 2026) | Still open |
|---|---|---|
| Database access | `agent1_retrieval/db.py`: read-only connection (SQLite `mode=ro`; PostgreSQL read-only session and transaction, always rolled back), **one statement per call** (a `SELECT 1; COMMIT; DELETE ...` string did delete a row as a write-capable user before this fix; regression test `test_pg_multi_statement_cannot_escape_read_only_even_as_owner`), statement timeout, passwords hidden in errors. Only SQLite and PostgreSQL are accepted. | **Mandatory in deployment: a database login with SELECT-only permission.** It is the backstop for every case. |
| SQL guard | Only `SELECT`/`WITH` runs; anything else is refused with `BLOCKED` and not retried (found live: phi3 answered "Delete all customers" with `BEGIN TRANSACTION`) | Agent 4's safety and diagnosis sub-agents replace the stand-in (section 4, phase 6) |
| Input checks | Questions 1–500 characters; databases chosen by configured name only (never a path); off-topic questions declined before any model call | — |
| Personal data | `J26_NO_VALUE_LINKING`: Agent 1 never reads data values from those databases (no value linking, no value hints); value hints never show columns whose values differ on every row | Masking or a retention policy for questions and SQL in `data/handoff.log.jsonl` |
| BI | `/answers` saves only answers the pipeline produced (by trace id), never client SQL; CSV export neutralises spreadsheet formulas; Superset needs explicit credentials (no default password); dashboards replay frozen SQL, the model is never on the refresh path | Use a low-privilege Superset account and a SELECT-only database connection |
| Who may ask what | — | **Login on the app's endpoints** (ideally the institution's single sign-on) and **per-role visible schema** (e.g. a branch clerk must not see other branches' customers): filter the tables/columns a role may see before Agent 1 reads the schema, plus a per-role read-only database login |
| Network | Runs on `localhost` today | HTTPS on the internal network, no public exposure, rate limiting |
| Model runtime | Ollama during development | `llama-cpp-python` inside the app for deployment (section 5, step 2) |

## 9. Reports and documents to read

| Document | What it is for |
|---|---|
| `Project_Scope_J26-DS-336.md`, `Combined_Proposal_J26-DS-336.md`, `Individual_Proposal_*.md` | Scope and proposals (the combined proposal file is truncated at section 4) |
| `System_Walkthrough_J26-DS-336.md` | Panel-level explanation of the whole system with one example question |
| `reports/Base model selection for local Text2SQL.md` | Base model, teacher, hand-off formats, platform, experimental method (with sources and a verify-before-citing list) |
| `reports/Bank data access and BI integration.md` | How target institutions use data today, commercial NL tools, governance, how ours differs, BI integration pattern |
| `reports/Deployment_runtime_plan.md` | Ollama → transformers/PEFT → llama.cpp |
| `reports/agent1_phase8/README.md`, `pp1/` | Agent 1 phase 8 results; PP1 panel responses per member |
| `Market_Research_Comparable_Systems.md` | Prior art and honest novelty positioning (MATS, HydraLoRA, GRASP/RASL) |

**Wording to fix in the proposals and scope (from the research reports):**
- US model-risk guidance SR 11-7 was replaced by **SR 26-2** on 17 Apr 2026; do not cite SR 11-7 as current.
- Do not argue that AI vendors train on customer data: the major vendors' terms exclude it.
- No regulator requires on-premise hosting; the restriction is the institution's own AI-governance and vendor-risk policy, reinforced by regulation. Only about 15% of surveyed banks restrict or ban AI tools; 66% have an AI-use policy.
- "Ad hoc requests take days or weeks" rests on a single 2015 vendor survey: soften it.
- "Existing tools cannot run without a hosted LLM" is no longer true: add **Oracle Select AI** (private model endpoint) and **Metabase Metabot** (self-hosted model since v64) to related work.
- MATS figures (87.1% Spider / 64.73% BIRD) are still unverified against the paper; check before citing.
- Precondition to state: most surveyed smaller banks (about 61%) have no single data warehouse to query.
