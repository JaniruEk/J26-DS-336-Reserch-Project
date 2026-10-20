# Running the app

How to start the team's application (chat, Pipeline Explorer, dashboard) on your own machine, share it with the team, and plug your own agent in. Commands are for **Windows PowerShell**; run them from the repository folder. On macOS or Linux the commands are the same except settings: write `export J26_GENERATOR=adaptive_qwen` instead of `$env:J26_GENERATOR = "adaptive_qwen"`. All settings are listed in [section 7](#7-settings-reference).

What you get:

| Page | Address | What it shows |
|---|---|---|
| Chat | http://localhost:8765/chat | Ask a question; the answer shows the four-agent pipeline and each agent's input and output |
| Pipeline Explorer | http://localhost:8765/ | One question, a tab per agent: Agent 1's four retrieval modes and pruning, the gate's decision, the SQL written per attempt (and per retrieval mode), execution attempts and Agent 4's layer-by-layer precision map |
| Dashboard | http://localhost:8765/dashboard | Answers saved from the chat, re-run live as charts |

Both the chat and the Explorer offer example questions for each database (from `harness/examples.js`); click one to run it.

Until Agents 2–4 are plugged in, some stages are stand-ins, and both pages mark them so: Agent 1's word check is the question gate, the SQL is written by the model chosen with `J26_GENERATOR` (Karunanayake's quantized Qwen, or phi3 through Ollama), and a read-only runner executes it.

**The short version, once set up:** `.\scripts\start_app.ps1` (details in section 2).

---

## Quick setup with Agent 4's model (NVIDIA GPU, no Ollama)

For a machine with an NVIDIA GPU, using Karunanayake's quantized Qwen as the SQL model. Ollama is not needed. You need Python 3.11, Git, and an NVIDIA driver recent enough for CUDA 12.4 (`nvidia-smi` shows "CUDA Version: 12.4" or higher).

```powershell
git clone https://github.com/JaniruEk/J26-DS-336-Reserch-Project.git
cd J26-DS-336-Reserch-Project
python -m venv .venv; .\.venv\Scripts\Activate.ps1     # optional: keeps these packages separate from your own
pip install -r requirements.txt
pip install -r requirements-gpu.txt                    # torch with CUDA, transformers, bitsandbytes (about 3 GB)
python -m spacy download en_core_web_md
python scripts/get_chinook.py                          # data/chinook.db; the other databases in section 1 are optional
python -c "import torch; print(torch.cuda.is_available())"   # must print True

.\scripts\start_app.ps1                               # picks Agent 4's model by itself when the line above prints True
```

Open http://localhost:8765/chat. The first start downloads Qwen2.5-1.5B-Instruct (about 3 GB) and builds the mixed INT4/INT8 model (about 2 minutes, printed in the terminal); the first question waits for it. The chat page says "SQL is written by ..." with the model's name; if it says "phi3 via Ollama (adaptive_qwen unavailable: ...)", see Troubleshooting. The layer plan comes from `results/qwen/qwen_precision_allocation.csv`, so a new allocation from your experiments is used after a restart.

If `Activate.ps1` or `start_app.ps1` is blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once. Next time, only `.\scripts\start_app.ps1` is needed (after activating the venv, if you made one).

---

## 1. One-time setup

You need **Python 3.11**, **Git** and **Ollama** (https://ollama.com). Docker is only needed for the optional PostgreSQL databases.

```powershell
git clone https://github.com/JaniruEk/J26-DS-336-Reserch-Project.git
cd J26-DS-336-Reserch-Project
pip install -r requirements.txt
python -m spacy download en_core_web_md
python scripts/get_chinook.py        # data/chinook.db
python scripts/make_tpch.py          # data/tpch.db (tables only, no rows)
python scripts/get_spider.py         # 20 Spider databases (~200 MB download)
ollama pull phi3                     # the stand-in SQL model
```

Optional:
- **Northwind:** download `northwind.db` from https://github.com/jpwhite3/northwind-SQLite3 into `data/`. It appears in the app automatically.
- **Qwen2.5-Coder:** `ollama pull qwen2.5-coder:1.5b-instruct` for the evaluation scripts that use it.

`data/` is not in Git, so everyone downloads the databases once.

---

## 2. Start it

From the repository folder:

```powershell
.\scripts\start_app.ps1             # this machine only
.\scripts\start_app.ps1 -Restart    # an old copy is still holding the port: stop it first
```

The script does the checks that usually go wrong, then starts the app and prints the three addresses:
- **Port:** if port 8765 is in use, it says which process holds it and stops (or, with `-Restart`, stops that old copy first).
- **SQL model:** Karunanayake's quantized Qwen if this machine has an NVIDIA GPU with the GPU packages installed, otherwise phi3 through Ollama (with a warning if Ollama isn't running). Choose yourself with `-Generator ollama:phi3` or `-Generator adaptive_qwen`.
- **PostgreSQL copies** of Chinook and Northwind: added only if Docker Desktop is running and the `j26-postgres` container exists (see `scripts/load_postgres.py`). Start Docker Desktop first if you want them; the rest works without it.

Open http://localhost:8765/chat. Stop the app with **Ctrl + C** in that terminal. Closing the terminal stops it too, so keep it open during a demo.

<details><summary>Without the script (macOS / Linux, or to set things by hand)</summary>

1. If you use Ollama: make sure it is running (`ollama serve`; "address already in use" means it already is).
2. Optional, PostgreSQL: start Docker Desktop, then
   ```powershell
   docker start j26-postgres
   $env:J26_DATABASES = '{"chinook_postgres": "postgresql+psycopg://ro_user:ro_pass@127.0.0.1:55432/chinook", "northwind_postgres": "postgresql+psycopg://ro_user:ro_pass@127.0.0.1:55432/northwind"}'
   ```
3. Choose the SQL model (next section), then start the app:
   ```powershell
   $env:J26_GENERATOR = "adaptive_qwen"     # or leave unset for phi3 through Ollama
   python -m uvicorn harness.app:app --port 8765
   ```
</details>

Ask one warm-up question per database before a demo: the first one loads the models and takes a few seconds.

**Add your own database:** on the chat page, open "Add a database" and drop a SQLite file there, or paste a PostgreSQL link. Use a read-only database login. Tick "don't read data values" for databases with personal data.

---

### Choose the SQL model (`J26_GENERATOR`)

Set this before starting the app. The chat page shows which model is answering.

| Value | Model | Needs |
|---|---|---|
| *(unset)* or `ollama:phi3` | phi3 through Ollama (default) | Ollama |
| `ollama:<any model>` | any Ollama model, e.g. `ollama:qwen2.5-coder:1.5b-instruct` | `ollama pull <model>` |
| `adaptive_qwen` | Karunanayake's (Agent 4) adaptive mixed-precision Qwen2.5-1.5B: sensitive layers 8-bit, the rest 4-bit, from `results/qwen/` | An NVIDIA GPU, and once: `pip install -r requirements-gpu.txt` |

```powershell
$env:J26_GENERATOR = "adaptive_qwen"
python -m uvicorn harness.app:app --port 8765
```

`adaptive_qwen` downloads Qwen2.5-1.5B (about 3 GB) the first time and builds the model at startup (about 2 minutes; the first question waits for it). After that, answers take a few seconds. It is the base model quantized, **not fine-tuned for SQL** yet, so expect wrong answers on joins. Without an NVIDIA GPU or those libraries, the app says so in its log and falls back to phi3.

---

## 3. Share it with the team (same Wi-Fi or university network)

```powershell
.\scripts\start_app.ps1 -Share
```

It prints the address teammates open (`http://<your IP>:8765/chat`) and an admin token, generated for this run unless `J26_ADMIN_TOKEN` is already set.

- If the printed IP is wrong, `ipconfig` lists the others. By hand: set `J26_ADMIN_TOKEN`, set `J26_ALLOWED_HOSTS` to your IP, and start uvicorn with `--host 0.0.0.0`.
- Windows Firewall asks about Python: allow it on **Private networks** only.
- Adding a database from another machine needs the admin token, typed into the "Admin token" box.
- **Do not put it on the public internet.** Asking questions and the dashboard have no login yet.
- `$env:` settings last only for that terminal window.

---

## 4. Plug your agent in

The harness calls two functions per question. Replace the stand-ins by passing yours to `create_app`; your stage in the chat then switches from "stand-in" to "real" by itself.

```python
# my_app.py  (run with: python -m uvicorn my_app:app --port 8765)
from harness.app import create_app

def generate(question, ddl, hint=None, dialect="SQLite"):
    """Agent 3. ddl = Agent 1's pruned schema text; hint = Agent 4's retry hint (None on the first attempt).
    dialect is passed only for server databases ("PostgreSQL"). Return one SQL string."""
    ...

def execute(db, sql):
    """Agent 4. db = a SQLite path or a SQLAlchemy URL. Return (True, rows) or (False, "error message").
    Keep it read-only: use cols, rows = agent1_retrieval.db.query(db, sql) (raises DBError on failure) rather than
    opening your own connection, and refuse non-SELECT SQL with an error starting "Blocked by SQL guard" (never retried)."""
    ...

app = create_app(generate=generate, execute=execute)
```

Agent 1's handoff to Agent 3 (what `run(question)` returns, as JSON): `query, complexity, mode, anchor, matched, tables, ddl, tokens, latency_ms, trace`. Every handoff is logged to `data/handoff.log.jsonl`.

---

## 5. Check it works

```powershell
python -m pytest tests                                         # should all pass (PostgreSQL tests skip without a database)
python -m agent1_retrieval "Which customers are from Canada?" --json
```

---

## 6. Troubleshooting

| Problem | Fix |
|---|---|
| "address already in use" / "Port 8765 is already in use" | An old copy is still running: `.\scripts\start_app.ps1 -Restart`, or use `-Port 8000` |
| `start_app.ps1 cannot be loaded because running scripts is disabled` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or run `powershell -ExecutionPolicy Bypass -File .\scripts\start_app.ps1` |
| Chat says the SQL generator is unavailable | Ollama isn't running (`ollama serve`) or phi3 isn't pulled (`ollama pull phi3`) |
| `chinook_postgres` missing or "database unavailable" | Start **Docker Desktop** and wait until it says it is running, then start the app again (the script adds them by itself) |
| `Can't find model 'en_core_web_md'` | `python -m spacy download en_core_web_md` |
| Only chinook appears | The other databases aren't downloaded: run the scripts in section 1 |
| Adding a database gives 403 | From another machine: set `J26_ADMIN_TOKEN` on the server and type it in the "Admin token" box |
| `git fetch` fails with "cannot lock ref ... .lock: File exists" | Branch names that differ only in capital letters clash on Windows. Close GitHub Desktop and VS Code's Git, delete the named `.lock` file under `.git\refs`, and fetch again |
| Chat shows "phi3 via Ollama (adaptive_qwen unavailable: ...)" | `adaptive_qwen` could not start; the reason is in brackets. Usually no NVIDIA GPU, or a CPU-only torch: `pip uninstall torch` then `pip install -r requirements-gpu.txt`. Check with `python -c "import torch; print(torch.cuda.is_available())"` (must print `True`) |

---

## 7. Settings reference

All settings are environment variables, read when the app starts. Set them in the same terminal before `python -m uvicorn ...`. None are needed for a local demo.

| Setting | What it does | Example |
|---|---|---|
| `J26_GENERATOR` | Which model writes the SQL (see "Choose the SQL model") | `adaptive_qwen` |
| `J26_DATABASES` | Extra databases, as JSON `{"name": "SQLite path or PostgreSQL URL"}`. Keeps passwords out of the code; use a read-only login | `{"bank": "postgresql+psycopg://ro_user:pw@dbhost/bank"}` |
| `J26_NO_VALUE_LINKING` | Databases whose data values Agent 1 must never read (personal data), comma-separated | `bank,hr` |
| `J26_GLOSSARIES` | Per-database data dictionary file, `{"Table.Column": "meaning"}`, shown to the model | `{"bank": "bank_glossary.json"}` |
| `J26_ADMIN_TOKEN` | Needed to add databases from another machine or behind a proxy; typed into the "Admin token" box | any secret |
| `J26_ALLOWED_HOSTS` | Addresses the app is reached by, besides localhost (comma-separated) | `192.168.1.20` |
| `J26_DB_HOSTS` | If set, the only database servers that may be added at runtime | `dbhost.internal` |
| `SUPERSET_URL`, `SUPERSET_USER`, `SUPERSET_PASSWORD`, `SUPERSET_DATABASES` | Optional "push to Superset" for saved answers. All required together; use a low-privilege account | `SUPERSET_DATABASES={"chinook": 1}` |
