# J26-DS-336: Distributed Multi-Agent SLM Framework for Privacy-Preserving Enterprise Data Intelligence

SLIIT B.Sc. (Hons) IT (Data Science) final-year research project, 2026.
Supervisors: Prof. Nathali Silva and Mr. Theshan Senanayake.

Regulated enterprises want to ask questions of their databases in plain English, but internal AI-governance and vendor-risk policies keep that data away from cloud generative-AI vendors. This project builds a fully local pipeline of four agents around one small language model that runs on mid-range hardware:

```
question ─► Agent 1 Retrieval ─► Agent 3 Generation ─► Agent 4 Execution ─► answer
            (selected schema +     (LoRA / HydraLoRA     (quantized model,
             complexity label)      on Agent 2's base)    run SQL, diagnose, retry)
```

| Agent | Owner | Status in this repo |
|---|---|---|
| 1 Schema retrieval and adaptive context width | J.K.B. Ekanayake (IT23199262) | `agent1_retrieval/`: working, evaluated; width study run on Qwen2.5 0.5B / 1.5B / 3B (`reports/agent1_width/`) |
| 2 Foundation model (distillation) | W.A.T. Wathsala (IT23282704) | `Agent2/`: distillation notebooks; `MultiTask_Research/`: distilled Qwen2.5-1.5B multitask student, now the app's question gate (`harness/gates.py`; model files are shared outside git) |
| 3 Fine-tuned generation (LoRA vs HydraLoRA) | K.G.Y.V. Thathsarani (IT23404250) | `agent3_finetune/`: LoRA vs HydraLoRA on Qwen2.5-1.5B-Instruct, preliminary results |
| 4 Quantized execution (adaptive mixed-precision INT4/INT8) | K.M.I.N. Karunanayake (IT23179912) | `src/`, `scripts/qwen_*`, `results/qwen/`: adaptive INT4/INT8 Qwen2.5-1.5B-Instruct, usable in the app |
| Harness (shared) | team | `harness/`: FastAPI sequencing, handoff logging, bounded retry, chat, Pipeline Explorer, dashboard |

The team's base model is **Qwen2.5-1.5B-Instruct**. Until Agent 3's fine-tuned model is plugged in, the app writes SQL with a stand-in: phi3 via Ollama by default, or Agent 4's quantized Qwen (`J26_GENERATOR=adaptive_qwen`, needs an NVIDIA GPU).

## Setup

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_md
python scripts/get_chinook.py        # data/chinook.db
python scripts/make_tpch.py          # data/tpch.db (schema only)
python scripts/get_spider.py         # 20 Spider dev DBs + eval/spider_pairs.json (~200 MB download)
ollama pull phi3                     # stand-in SQL generator until Agent 3's model is ready
```

Optional, to use Agent 4's quantized model in the app (NVIDIA GPU only):

```bash
pip install -r requirements-gpu.txt
```

Step-by-step for a GPU machine (no Ollama needed): [RUNNING_THE_APP.md, "Quick setup with Agent 4's model"](RUNNING_THE_APP.md#quick-setup-with-agent-4s-model-nvidia-gpu-no-ollama).

## Run

**Hosting the app, choosing the SQL model, sharing it on the team network, all settings, and plugging your agent in: see [RUNNING_THE_APP.md](RUNNING_THE_APP.md).**

```bash
python -m pytest tests
python -m agent1_retrieval "Which customers are from Canada?" --json
.\scripts\start_app.ps1                                   # Windows: start the app with checks (port, SQL model, PostgreSQL); -Restart, -Share
python -m uvicorn harness.app:app --port 8765             # or by hand. http://localhost:8765/chat team chatbot
                                                          # http://localhost:8765/           Pipeline Explorer (a tab per agent)
                                                          # http://localhost:8765/dashboard  saved answers as charts
python -m agent1_retrieval.evaluate --pairs eval/chinook_pairs.json eval/tpch_pairs.json eval/spider_pairs.json --recommended
python -m agent1_retrieval.evaluate --pairs eval/chinook_pairs.json eval/spider_pairs.json --recommended --exec phi3
```

For an opt-in run using the schema-aware complexity classifier (which uses
table names, column names, and foreign-key structure for routing), add
`--schema-classifier` to either the Agent 1 CLI or the evaluation command.
The live application already enables this through its `LIVE` configuration;
the reproducibility-focused `RECOMMENDED` configuration remains unchanged.

The Agent 1 CLI also exposes the two supported configurations:

```bash
python -m agent1_retrieval "Which products are discontinued?" --live --json
python -m agent1_retrieval "Which customers are from Canada?" --narrow-simple 0.6 --json
python -m agent1_retrieval "Which accounts are active?" --value-hints --json
```

Use `--plain` to reproduce the original Phase 1–7 settings. `--live` and
`--plain` are mutually exclusive. A glossary can be supplied with
`--glossary path/to/glossary.json`.

## Agent 1 in brief

There are three sub-agents, and each makes one bounded decision:

1. **Anchor selection** decides where retrieval starts. It uses either ChromaDB MiniLM similarity over table DDL, or keyword matching.
2. **FK traversal** decides which related tables are needed to join. It walks the foreign-key graph read live from the database and adds bridge tables between anchors. Foreign keys can be inferred from column names when none are declared.
3. **Column pruning** decides which columns inside those tables reach the model. Keys are always kept. Other columns are kept on value, lemma, split-name, synonym or word-vector evidence. Each column records the reason it was kept or pruned.

There are four switchable modes: `semantic`, `structural`, `hybrid` (the table-level baseline) and `hybrid_pruned`. The handoff to Agent 3 is a JSON-serialisable dict with these fields: `query`, `complexity`, `mode`, `width`, `anchor`, `matched`, `tables`, `ddl`, `tokens`, `latency_ms` and `trace`.

Results for hybrid_pruned with the `RECOMMENDED` configuration (column recall at tokens):

| Set | hybrid_pruned | hybrid with the same tables |
|---|---|---|
| Chinook (14) | .95 at 200 | .95 at 262 |
| TPC-H (14) | .97 at 241 | .97 at 322 |
| Spider (120, never used for tuning) | .98 at 138 | .99 at 161 |

Warm retrieval latency is about 80–120 ms on average, against a 500 ms target. Execution accuracy with phi3 is reported in `CLAUDE.md` (Phases 5 and 7). On the evidence so far, pruning breaks even on accuracy and saves tokens. Full detail: `reports/agent1_phase8/README.md`, `pp1/01_Ekanayake_PP1_Response.md`.

**Main claim since November 2026: adaptive context width.** The modes are four nested widths: W1 = anchor table (`semantic`), W2 = `hybrid_pruned`, W3 = `hybrid`, W4 = full schema. A selector picks one width per question before generation, trained on the SQL results of the small model in use. Results (Qwen2.5-Instruct 0.5B / 1.5B / 3B FP16, 869 test questions): the best fixed width grows with model size (W1, W2, W3) and depends on complexity; the selector matches the best fixed width at about half the tokens but does not beat it. Numbers, tests and charts: `reports/agent1_width/README.md`.

## Repository map

| Path | Contents |
|---|---|
| `agent1_retrieval/` | schema reflection, retrieval modes, pruning, linking, complexity classifier, evaluation, statistics |
| `harness/` | FastAPI orchestration, chatbot (`/chat`), Pipeline Explorer (`/`), dashboard (`/dashboard`), SQL model switch (`generators.py`) |
| `Agent2/` | Agent 2 distillation notebooks |
| `MultiTask_Research/` | Agent 2's 1.5B multitask results (CSV, in git) and model folders (not in git: copy her folder in) |
| `agent3_finetune/` | Agent 3 dataset, LoRA / HydraLoRA training, evaluation, results, progress log |
| `src/`, `scripts/qwen_*`, `results/qwen/` | Agent 4 quantization code, layer sensitivity and precision allocation results |
| `eval/` | labelled question/SQL pairs (Chinook, TPC-H, Spider, Northwind, value-coded, hard multi-join) |
| `scripts/` | data download, TPC-H generator, complexity classifier training, parameter sweeps |
| `reports/` | measured results |
| `pp1/` | PP1 panel responses and flow diagrams |
| `handoff/` | requests to teammates for model files to plug into the app |
| `RUNNING_THE_APP.md` | how to host and use the app |
| `*_J26-DS-336.md` | scope, proposals, execution plan, market research |

`data/` is git-ignored; the scripts above recreate it.
