# J26-DS-336: Distributed Multi-Agent SLM Framework for Privacy-Preserving Enterprise Data Intelligence

SLIIT B.Sc. (Hons) IT (Data Science) final-year research project, 2026.
Supervisors: Prof. Nathali Silva and Mr. Theshan Senanayake.

Regulated enterprises want to ask questions of their databases in plain English, but internal AI-governance and vendor-risk policies keep that data away from cloud generative-AI vendors. This project builds a fully local pipeline of four agents around one small language model that runs on mid-range hardware:

```
question ─► Agent 1 Retrieval ─► Agent 3 Generation ─► Agent 4 Execution ─► answer
            (pruned schema +       (LoRA / HydraLoRA     (quantized model,
             complexity label)      on Agent 2's base)    run SQL, diagnose, retry)
```

| Agent | Owner | Status in this repo |
|---|---|---|
| 1 Schema retrieval and column-level pruning | J.K.B. Ekanayake (IT23199262) | `agent1_retrieval/`: working, evaluated (Phases 1–8) |
| 2 Foundation model (distillation) | W.A.T. Wathsala (IT23282704) | see team branches |
| 3 Fine-tuned generation (LoRA vs HydraLoRA) | K.G.Y.V. Thathsarani (IT23404250) | see team branches |
| 4 Quantized execution (adaptive mixed-precision INT4/INT8) | K.M.I.N. Karunanayake (IT23179912) | see team branches |
| Harness (shared) | team | `harness/`: FastAPI sequencing, handoff logging, bounded retry, explorer and chat UI |

## Setup

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_md
python scripts/get_chinook.py        # data/chinook.db
python scripts/make_tpch.py          # data/tpch.db (schema only)
python scripts/get_spider.py         # 20 Spider dev DBs + eval/spider_pairs.json (~200 MB download)
ollama pull phi3                     # stand-in SQL generator until Agent 3's model is ready
```

## Run

**Starting the app, sharing it with the team and plugging your agent in: see [RUNNING_THE_APP.md](RUNNING_THE_APP.md).**

```bash
python -m pytest tests
python -m agent1_retrieval "Which customers are from Canada?" --json
uvicorn harness.app:app                                   # http://localhost:8000      Agent 1 Retrieval Explorer
                                                          # http://localhost:8000/chat team chatbot (needs Ollama)
python -m agent1_retrieval.evaluate --pairs eval/chinook_pairs.json eval/tpch_pairs.json eval/spider_pairs.json --recommended
python -m agent1_retrieval.evaluate --pairs eval/chinook_pairs.json eval/spider_pairs.json --recommended --exec phi3
```

## Agent 1 in brief

There are three sub-agents, and each makes one bounded decision:

1. **Anchor selection** decides where retrieval starts. It uses either ChromaDB MiniLM similarity over table DDL, or keyword matching.
2. **FK traversal** decides which related tables are needed to join. It walks the foreign-key graph read live from the database and adds bridge tables between anchors. Foreign keys can be inferred from column names when none are declared.
3. **Column pruning** decides which columns inside those tables reach the model. Keys are always kept. Other columns are kept on value, lemma, split-name, synonym or word-vector evidence. Each column records the reason it was kept or pruned.

There are four switchable modes: `semantic`, `structural`, `hybrid` (the table-level baseline) and `hybrid_pruned` (the proposed method). The handoff to Agent 3 is a JSON-serialisable dict with these fields: `query`, `complexity`, `mode`, `anchor`, `matched`, `tables`, `ddl`, `tokens`, `latency_ms` and `trace`.

Results for hybrid_pruned with the `RECOMMENDED` configuration (column recall at tokens):

| Set | hybrid_pruned | hybrid with the same tables |
|---|---|---|
| Chinook (14) | .95 at 200 | .95 at 262 |
| TPC-H (14) | .97 at 241 | .97 at 322 |
| Spider (120, never used for tuning) | .98 at 138 | .99 at 161 |

Warm retrieval latency is about 80–120 ms on average, against a 500 ms target. Execution accuracy with phi3 is reported in `CLAUDE.md` (Phases 5 and 7). On the evidence so far, pruning breaks even on accuracy and saves tokens. Full detail: `reports/agent1_phase8/README.md`, `pp1/01_Ekanayake_PP1_Response.md`.

## Repository map

| Path | Contents |
|---|---|
| `agent1_retrieval/` | schema reflection, retrieval modes, pruning, linking, complexity classifier, evaluation, statistics |
| `harness/` | FastAPI orchestration, Retrieval Explorer (`/`), chatbot (`/chat`) |
| `eval/` | labelled question/SQL pairs (Chinook, TPC-H, Spider) |
| `scripts/` | data download, TPC-H generator, complexity classifier training, parameter sweeps |
| `reports/` | measured results |
| `pp1/` | PP1 panel responses and flow diagrams |
| `*_J26-DS-336.md` | scope, proposals, execution plan, market research |

`data/` is git-ignored; the scripts above recreate it.
