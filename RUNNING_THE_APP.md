# Running the app

How to start the team's application (chat, Retrieval Explorer, dashboard) on your own machine, share it with the team, and plug your own agent in. Commands are for **Windows PowerShell**; run them from the repository folder.

What you get:

| Page | Address | What it shows |
|---|---|---|
| Chat | http://localhost:8765/chat | Ask a question; the answer shows the four-agent pipeline and each agent's input and output |
| Retrieval Explorer | http://localhost:8765/ | Agent 1 alone: all four retrieval modes, kept and pruned columns |
| Dashboard | http://localhost:8765/dashboard | Answers saved from the chat, re-run live as charts |

Until Agents 2–4 are plugged in, the chat uses stand-ins: **phi3 via Ollama** writes the SQL and a read-only runner executes it. The chat marks those stages "stand-in".

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

1. Make sure Ollama is running. It usually starts with Windows. If not, run `ollama serve` in a second terminal and leave it open. "Address already in use" means it is already running.
2. Optional: the PostgreSQL copies of Chinook and Northwind (needs the `j26-postgres` container; see `scripts/load_postgres.py`):
   ```powershell
   docker start j26-postgres
   $env:J26_DATABASES = '{"chinook_postgres": "postgresql+psycopg://ro_user:ro_pass@127.0.0.1:55432/chinook", "northwind_postgres": "postgresql+psycopg://ro_user:ro_pass@127.0.0.1:55432/northwind"}'
   ```
3. Start the app:
   ```powershell
   python -m uvicorn harness.app:app --port 8765
   ```
4. Open http://localhost:8765/chat. Stop the app with **Ctrl + C**.

Ask one warm-up question per database before a demo: the first one loads the models and takes a few seconds.

**Add your own database:** on the chat page, open "Add a database" and drop a SQLite file there, or paste a PostgreSQL link. Use a read-only database login. Tick "don't read data values" for databases with personal data.

---

## 3. Share it with the team (same Wi-Fi or university network)

```powershell
$env:J26_ADMIN_TOKEN = "pick-a-secret"
$env:J26_ALLOWED_HOSTS = (Get-NetIPAddress -AddressFamily IPv4 | ? { $_.IPAddress -notlike '127.*' } | Select -First 1).IPAddress
$env:J26_ALLOWED_HOSTS          # prints the IP to share
python -m uvicorn harness.app:app --host 0.0.0.0 --port 8765
```

- Teammates open `http://<that IP>:8765/chat`. If the IP is wrong, `ipconfig` lists the others.
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
| "address already in use" on port 8765 | An old copy is running: `Get-NetTCPConnection -LocalPort 8765 -State Listen \| % { Stop-Process -Id $_.OwningProcess -Force }`, or use `--port 8000` |
| Chat says the SQL generator is unavailable | Ollama isn't running (`ollama serve`) or phi3 isn't pulled (`ollama pull phi3`) |
| `chinook_postgres` missing or "database unavailable" | `docker start j26-postgres`, and set `J26_DATABASES` in the same terminal before starting the app |
| `Can't find model 'en_core_web_md'` | `python -m spacy download en_core_web_md` |
| Only chinook appears | The other databases aren't downloaded: run the scripts in section 1 |
| Adding a database gives 403 | From another machine: set `J26_ADMIN_TOKEN` on the server and type it in the "Admin token" box |
| `git fetch` fails with "cannot lock ref ... .lock: File exists" | Branch names that differ only in capital letters clash on Windows. Close GitHub Desktop and VS Code's Git, delete the named `.lock` file under `.git\refs`, and fetch again |
