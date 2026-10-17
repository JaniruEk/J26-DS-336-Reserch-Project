# J26-DS-336 — Distributed Multi-Agent SLM Framework for Privacy-Preserving Enterprise Data Intelligence

SLIIT B.Sc. (Hons) IT, Data Science, Y4S1 final-year research project (Sept 2026). Supervisors: Prof. Nathali Silva, Mr. Theshan Senanayake. Research dissertation: the deliverable is **evidence** (controlled experiments), not software. Negative results are valid. Method: Design Science.

## Source docs (in repo root — read these for detail)
- [Project_Scope_J26-DS-336.md](Project_Scope_J26-DS-336.md) — full scope (problem, architecture, per-agent detail, interfaces)
- [Combined_Proposal_J26-DS-336.md](Combined_Proposal_J26-DS-336.md) — team proposal. **Truncated** at Section 4 (Agent 3 sub-agents); sections 5+ not yet saved
- [Individual_Proposal_Ekanayake_J26-DS-336.md](Individual_Proposal_Ekanayake_J26-DS-336.md) — complete individual proposal for Agent 1
- [Individual_Proposal_Wathsala_J26-DS-336.md](Individual_Proposal_Wathsala_J26-DS-336.md) — Agent 2 (distillation)
- [Individual_Proposal_Thathsarani_J26-DS-336.md](Individual_Proposal_Thathsarani_J26-DS-336.md) — Agent 3 (LoRA vs HydraLoRA)
- [Individual_Proposal_Karunanayake_J26-DS-336.md](Individual_Proposal_Karunanayake_J26-DS-336.md) — Agent 4 (QAT vs PTQ + cross-check)
- [Execution_Plan_J26-DS-336.md](Execution_Plan_J26-DS-336.md) — phase-by-phase plans for all four members (shared assets, interfaces to lock, per-agent phases/exit criteria); Agent 1 phases 1–6 done
- [Market_Research_Comparable_Systems.md](Market_Research_Comparable_Systems.md) — prior-art / novelty check

## Problem & framing
Regulated enterprises (regional banks, insurers, credit unions, FinTech) want NL→SQL over internal DBs. Cloud generative-AI vendors are blocked by **internal AI-governance / vendor-risk policy** (reinforced by GDPR/CCPA) — NOT a blanket legal ban on third-party sharing. Local SLMs hallucinate on multi-join/aggregation queries. Question: can a fully local SLM system be private *and* accurate?
- **Wording rule:** never write "law prohibits sending data to third parties" / "cloud AI is illegal". Say generative-AI vendors are a newer, less-precedented category under AI-governance policy.
- Delivery: licensed on-premise appliance, one instance in the org's own data center, accessed over private network.
- Target customers lack large GPU infra / ML teams. Hardware budget everywhere: **8GB VRAM (RTX 3070 Ti class)**.

## Four agents (sequential pipeline, run fresh per query; no independent track)
| Agent | Owner | Role |
|---|---|---|
| 1 Retrieval | J.K.B. Ekanayake (IT23199262) | Schema retrieval + column-level pruning; builds shared complexity classifier |
| 2 Foundation model | W.A.T. Wathsala (IT23282704) | Knowledge distillation (~7B teacher → small student vs. native baseline); critical path |
| 3 Fine-tuned generation | K.G.Y.V. Thathsarani (IT23404250) | Standard LoRA vs. HydraLoRA (hard-coded complexity routing); live SQL generation; outputs winner **and runner-up** |
| 4 Quantized execution | K.M.I.N. Karunanayake (IT23179912) | QAT vs. PTQ (8/4-bit, GGUF/AWQ); cross-check winner strategy on Agent 3's runner-up; SQL execution + error diagnosis/retry |

Handoffs: A1→A3 pruned schema context + complexity label (live); A2→A3 two base checkpoints (distilled, native); A3→A4 winner+runner-up artefacts (offline) and candidate SQL (live); A4→user executed SQL + results. Retry loop: A4 Error-Diagnosis → A3 Generation, bounded attempts. **Still open:** exact handoff formats (DDL vs JSON; checkpoint format).

### Agent 1 detail (Ekanayake — the user's own component)
- Sub-agents: Anchor-Selection (ChromaDB semantic or keyword match) → Traversal (FK graph via `PRAGMA foreign_key_list`) → Pruning (lemma overlap first, spaCy cosine fallback vs tuned threshold).
- Four switchable modes: semantic-only, structural-only, hybrid, hybrid+pruning (novel). Baseline = table-level hybrid.
- Metrics: token count, schema-linking precision/recall, execution accuracy — stratified by complexity.
- NFRs: <500ms retrieval per query; ≥20 tables; tolerate missing FKs.

## Shared foundations
- Complexity taxonomy: simple / single-join / multi-join / aggregation (from ground-truth SQL).
- DB proxies: Chinook (primary), Spider, TPC-H. Synthetic Python-generated pairs fill thin buckets.
- Orchestration: lightweight FastAPI harness (sequencing, structured handoff logging, bounded retry) — deliberately NOT LangGraph; shared infra, not anyone's novelty.
- Parallel-work fix: Agent 3 runs LoRA-vs-Hydra on a placeholder base first, Agent 4 on a placeholder fine-tuned model; both re-run on real upstream artefacts.

## Novelty positioning (from market research — keep claims honest)
- Closest competitor: **MATS** (arXiv 2512.18622; 5 SLM agents, 9B total, 24GB GPU, 87.1% Spider / 64.73% BIRD). Do NOT claim multi-agent SLM text-to-SQL as novel. Claim efficiency (one shared base + adapters + quantization on 8GB) and depth on fine-tuning/quantization.
- Strongest claim: complexity-routed HydraLoRA for SQL (Thathsarani). Be ready to defend hard-coded vs learned router (auditable, avoids gating collapse).
- Quantization: QAT vs PTQ + cross-check is a narrow but real gap; distinguish from arXiv 2607.25583 ("How Small Can You Go?", 60M model).
- Schema retrieval is crowded (GRASP, RASL, RSL-SQL, SchemaGraphSQL) — Ekanayake's contribution is the four-mode ablation/measurement rigor, not a novel retrieval algorithm. Read GRASP and RASL.
- Privacy: combination of local hosting + active schema pruning (Prem-1B-SQL skips pruning; MaskSQL uses redaction instead of local hosting).
- Commercial tools (Snowflake Cortex Analyst, Databricks Genie, ThoughtSpot): cite once as market context / proof of demand.

## Code (Agent 1, package `agent1_retrieval/`)
Reference prototype: github.com/JaniruEk/enterprise-slm-framework (`pillar1_rag/`, SQLite + ChromaDB + Ollama phi3). This repo's package is a cleaner rewrite, not a copy.
- `schema.py` reflect DB + FK graph + DDL render · `retrieval.py` `Retriever.retrieve(query, mode)` for modes `semantic|structural|hybrid|hybrid_pruned` · `pruning.py` keys kept, else lemma overlap, else spaCy similarity ≥ threshold (0.6) · `complexity.py` `classify_sql` · `evaluate.py` tokens/latency/table+column P/R per mode × complexity bucket.
- Setup: `pip install -r requirements.txt`, `python -m spacy download en_core_web_md`, `python scripts/get_chinook.py`, `python scripts/make_tpch.py` (schema only), `python scripts/get_spider.py` (~200MB Drive download; extracts 20 dev DBs, writes stratified 120 pairs, nested/compound queries skipped). data/ is gitignored; eval/*.json pairs carry their own `db` path.
- Run: `python -m pytest tests` · `python -m agent1_retrieval "question"` · `python -m agent1_retrieval.evaluate --pairs eval/chinook_pairs.json eval/tpch_pairs.json eval/spider_pairs.json` (multiple files OK)
- Phase 2 tuning (Chinook, 14 pairs, `python -m scripts.sweep`): fixed a bug where spaCy stop words ('name','first','last') were dropped before lemma matching (colR 0.64→0.73). Similarity threshold (0.5–0.7) barely matters; FK depth 1 is the sweet spot (depth 2: +0.04 table recall, table precision 0.49→0.31, +80 tokens). Remaining misses are display columns (FirstName/LastName/Name/Title) that questions don't name; `labels=True` ablation keeps them → colR 0.91 at 183 tokens (vs hybrid 251, pruned default 168). `labels` is a hardcoded-heuristic ablation arm, default off.
- Phase 3 results, hybrid → hybrid_pruned (tokens / colP / colR): Chinook 251→168 / .17→.23 / .95→.73 · TPC-H 240→137 / .13→.24 / .86→.46 · Spider(120) 126→87 / .28→.49 / .93→.89. Pruning is a clear win on Spider (natural column names); it hurts recall on TPC-H because columns are abbreviated/concatenated (`c_acctbal`, `l_extendedprice`) which lemma/word-vector matching can't read — report as a limitation; table-prefix stripping added but did not fix it. Spider multi-join recall is the weak bucket (tblR .76, anchor+depth-1 can't reach 3+ tables).
- Gotcha fixed: shared `chromadb.EphemeralClient` intermittently returned no anchor across many collections (non-deterministic results); each Retriever now owns a PersistentClient in a temp dir.
- Phase 4: `classify_query(question)` (TF-IDF+LogReg trained on Spider *train* gold-SQL labels via `scripts/train_complexity.py`, model committed at `agent1_retrieval/complexity_nl.joblib`). Accuracy: Spider dev 0.57 (majority 0.25), Chinook 0.57, TPC-H 0.71. Aggregation is reliable (27/30); join count is weak (single vs multi-join confused) because it depends on the schema, not just the text. Possible upgrade: add retrieved-table count as a feature.
- **Handoff contract to Agent 3** (`Agent1(db, mode).run(query)` → JSON-serialisable dict): `query, complexity, mode, anchor, tables{table:[cols]}, ddl (pruned DDL text), tokens, latency_ms`. Proposed by Ekanayake (JSON with DDL inside); still needs Thathsarani's sign-off. `--json` flag on the CLI prints it.
- Known pruning miss: "which customers spent the most?" keeps Invoice keys but drops Invoice.Total ("spent" vs "total" similarity < 0.6).
- Phase 5: `evaluate --exec phi3` (Ollama phi3 as stand-in for Agent 3; strict row-multiset match; cached in data/gen_cache.json; ~19 gens/min) + paired bootstrap CIs and exact McNemar (`stats.py`). Chinook+Spider, n=134 (128 scored): execution accuracy semantic .34 · structural .34 · hybrid **.40** · hybrid_pruned .35. Pruning vs hybrid: tokens −44 [−51,−37], colP +.19, colR −.06 [−.08,−.04], exec −.05 (only-pruned 10 vs only-hybrid 16, McNemar p=0.33 → **not significant**). By bucket the loss is concentrated in multi-join (.31→.16); single-join actually improves (.35→.42). Honest reading so far: pruning saves ~31% tokens but has not shown an accuracy gain with phi3 — a valid negative/neutral result; re-run with Agent 3's real model before concluding. Single-table modes already reach .34.
- Phase 6: `harness/app.py` (FastAPI; `uvicorn harness.app:app`). `POST /retrieve` = Agent 1 handoff payload; `POST /query {query, db, mode}` = Agent 1 → generate → execute with bounded retry (MAX_ATTEMPTS=3), every handoff logged as JSON lines to `data/handoff.log.jsonl` (trace id, stage, attempt, hint, sql, result). `db` is a configured key (unknown → 404, never a raw path); executor opens DB read-only. Agent 3 (`generate`) and Agent 4 (`execute`) are injectable; defaults are stand-ins (phi3 + sqlite) and the retry hint is the raw DB error (Agent 4's error-diagnosis sub-agent should replace it). Harness is shared infra — teammates should plug in via `create_app(generate=..., execute=...)`.
- Live smoke test: "How many tracks does each genre have?" fails all 3 retries because pruning dropped `Genre.Name` (retry can't recover a pruned column) — supports trying `labels=True` / deeper context on retry.
- Phase 7 (multi-join fix; options on `Retriever`: `labels`, `adaptive`, `multi_anchors=k`, `gate`, `min_cols`; CLI flags on `evaluate`; `python -m scripts.sweep`): 50 of 62 missed multi-join columns were whole tables never reached, so the fix is table-level: top-k semantic anchors connected by shortest FK paths (bridge tables). The NL classifier gate catches only ~1/3 of true multi-join questions, so `gate=False` (apply to every question) is needed. Chinook+Spider exec (phi3, 128 scored): hybrid(1 anchor) .40 @139 tok · hybrid(3 anchors) .41 @171 · pruned(3 anchors) .33 @119 (multi-join .22 vs .38, McNemar p=0.035 — pruning *hurts* when column recall is .92) · **pruned(3 anchors, min_cols=8) .41 @142 (colR .96, multi-join .38 = hybrid)**. Reading: with weak phi3, pruning only breaks even on accuracy; it saves 17% tokens vs an equally wide hybrid but not vs the 1-anchor hybrid. Pruning needs near-perfect column recall to avoid costing accuracy. Recommended config: `Retriever(db, multi_anchors=3, gate=False, min_cols=8)`; defaults unchanged so earlier numbers reproduce. No execution evidence yet that pruning *improves* accuracy — report as neutral; revisit with Agent 3's fine-tuned model.
- Not built yet: re-run with Agent 3's fine-tuned model (Phase 8); agree handoff format with Thathsarani.
- Note: proposal's dataset sample labels `SELECT COUNT(*) FROM Track` "Simple" and a 1-join query "Multi-join"; `classify_sql` follows the structural rule (aggregate→aggregation, 1 JOIN→single-join), so those labels differ.

## Open TODOs
- Paste remainder of combined proposal (Sections 4 onward) and save.
- Redraw system diagrams by hand / diagramming tool (B&W, NOT AI-generated) per template.
- Verify all citations (references were compiled without live lookup).
- Add MATS, HydraLoRA (arXiv 2404.19245), arXiv 2607.25583 to literature reviews.
- Agree handoff formats between agents.
- Typo in Ekanayake proposal §1.1: "Road-scale enterprise data querying" (likely "Large-scale"); combined proposal refers to "Pillar 2" for fine-tuning component.

## Working conventions
- Audience is academic (supervisors/panel): keep claims defensible, cite limits. Proposals must include an AI-use disclosure (Appendix 3).
- Commit only when asked.
