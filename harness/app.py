"""Orchestration + observability harness (shared infra): sequence agents, log every handoff as JSON lines, bounded retry.
Agent 1 is real. Agents 3 (generate) and 4 (execute) are injectable callables; the defaults are stand-ins
(local phi3 + plain sqlite) until the teammates' components replace them.
Run: uvicorn harness.app:app   |   GET / = Agent 1 Retrieval Explorer   |   GET /chat = team chatbot   |   POST /query {"query": "...", "db": "chinook"}"""
import json
import os
import re
import time
import uuid
from collections import OrderedDict
from functools import partial
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, StringConstraints

from agent1_retrieval import LIVE, MODES, Agent1
from agent1_retrieval.db import DBError, dialect, query, tables_with_rows
from agent1_retrieval.execution import ollama_generate
from agent1_retrieval.schema import reflect

from .bi import AnswerStore, chart_hint, push_to_superset, superset_config, to_csv

MAX_ATTEMPTS = 3
MAX_QUESTION = 500  # chars; longer input is rejected at the boundary, before any agent runs
DEFAULT_DBS = {k: p for k, p in {"chinook": "data/chinook.db", "tpch": "data/tpch.db"}.items() if Path(p).exists()} or {"chinook": "data/chinook.db"}


def env_dbs():
    """Extra databases from the environment, so connection strings (with passwords) never live in the code:
    J26_DATABASES='{"bank": "postgresql+psycopg://readonly_user:pw@dbhost/bank"}'. Merged over the defaults."""
    return {**DEFAULT_DBS, **json.loads(os.environ.get("J26_DATABASES", "{}"))}


def env_no_value_linking():
    """J26_NO_VALUE_LINKING=bank,hr : databases whose data values Agent 1 must never read (personal data)."""
    return {n.strip() for n in os.environ.get("J26_NO_VALUE_LINKING", "").split(",") if n.strip()}


def env_glossaries():
    """J26_GLOSSARIES='{"bank": "config/bank_glossary.json"}' : per-database data dictionary, {"Table.Column": "meaning"},
    shown to the model as column comments (e.g. "C = closed, A = active"). Any database, any number."""
    return json.loads(os.environ.get("J26_GLOSSARIES", "{}"))


BLOCKED = "Blocked by SQL guard"  # an error starting with this is final: the harness does not retry it


def run_sql(db, sql, timeout=10):
    """Stand-in for Agent 4's Execution sub-agent -> (ok, rows | error message). Read-only; runaway queries are aborted.
    ponytail: keyword guard (first word SELECT/WITH); Agent 4's safety sub-agent replaces it. The read-only connection is the real backstop."""
    if not re.match(r"\s*(SELECT|WITH)\b", sql or "", re.I):
        return False, f"{BLOCKED}: only read-only SELECT queries are allowed."
    try:
        return True, query(db, sql, timeout=timeout)[1]
    except DBError as e:
        return False, str(e)


def sql_columns(db, sql, timeout=10):
    """Result column names for display. ponytail: re-prepares the query (description is known after the first step);
    move into Agent 4's execute result if the double prepare ever shows up in timings."""
    try:
        return query(db, sql, timeout=timeout)[0]
    except DBError:
        return []


def has_rows(db):
    """False for schema-only databases (e.g. the generated TPC-H file), where every answer would be 'no rows'."""
    return tables_with_rows(db, reflect(db))


def safe_has_rows(db):
    try:
        return has_rows(db)
    except DBError:
        return True  # unreachable: don't claim it is empty


class SaveAnswer(BaseModel):
    trace: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]  # a /query answer, never client SQL


class Query(BaseModel):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUESTION)]  # empty / too long -> 422
    db: str | None = None  # a key of the configured databases, never a raw path
    mode: str = "hybrid_pruned"


def create_app(dbs=None, generate=partial(ollama_generate, cache=False), execute=run_sql, log_path="data/handoff.log.jsonl",
               agent1_config=LIVE, answers_path="data/answers.db", superset=superset_config, no_value_linking=None,
               glossaries=None):
    """agent1_config: Retriever options for the live Agent 1 (pass {} for the original Phase 1-7 settings).
    superset: callable returning the Superset config or None (BI push disabled).
    dbs: name -> SQLite path or SQLAlchemy URL. no_value_linking: db names whose data values Agent 1 must not read."""
    dbs = dbs or env_dbs()
    no_values = env_no_value_linking() if no_value_linking is None else set(no_value_linking)
    glossaries = env_glossaries() if glossaries is None else glossaries
    app, agents = FastAPI(title="J26-DS-336 harness"), {}
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    Path(answers_path).parent.mkdir(parents=True, exist_ok=True)
    answers = AnswerStore(answers_path)
    answered = OrderedDict()  # trace -> (question, db name, sql) of successful /query answers: the only SQL /answers will save

    def log(trace, stage, **fields):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "trace": trace, "stage": stage, **fields}, default=str) + "\n")

    def agent1(req):
        name = req.db or next(iter(dbs))
        if name not in dbs:
            raise HTTPException(404, f"unknown db '{name}', choose from {list(dbs)}")
        if req.mode not in MODES:
            raise HTTPException(422, f"mode must be one of {MODES}")
        if (name, req.mode) not in agents:
            try:
                agents[name, req.mode] = Agent1(dbs[name], req.mode, **agent1_config, value_linking=name not in no_values,
                                                glossary=glossaries.get(name))
            except DBError as e:  # server database down / wrong credentials: say so, don't 500
                raise HTTPException(503, f"database '{name}' unavailable: {e}")
        return dbs[name], agents[name, req.mode]

    @app.get("/", include_in_schema=False)
    def explorer():
        return FileResponse(Path(__file__).with_name("explorer.html"))

    @app.get("/chat", include_in_schema=False)
    def chat():
        return FileResponse(Path(__file__).with_name("chat.html"))

    @app.get("/health")
    def health():
        return {"ok": True, "dbs": list(dbs), "schema_only": [n for n, p in dbs.items() if not safe_has_rows(p)], "max_attempts": MAX_ATTEMPTS,
                "superset": superset() is not None}

    @app.get("/dbs")
    def list_dbs():
        return list(dbs)

    @app.post("/retrieve")
    def retrieve(req: Query):
        """Agent 1 only: returns the handoff payload Agent 3 would receive."""
        trace = uuid.uuid4().hex[:8]
        _, a1 = agent1(req)
        out = a1.run(req.query)
        log(trace, "agent1", input=req.query, output=out)
        return out

    @app.post("/query")
    def query(req: Query):
        trace, t0 = uuid.uuid4().hex[:8], time.perf_counter()
        ms = lambda t: round((time.perf_counter() - t) * 1000, 1)
        path, a1 = agent1(req)
        ctx = a1.run(req.query)
        log(trace, "agent1", input=req.query, output=ctx)
        out = {"trace": trace, "context": ctx, "steps": []}  # steps: one entry per generate -> execute attempt
        if not ctx["matched"]:  # decline instead of letting the model guess SQL for an off-topic question
            return {**out, "ok": False, "sql": None, "attempts": 0, "total_ms": ms(t0),
                    "error": "I couldn't match this question to any table or column in this database."}
        hint = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            t = time.perf_counter()
            try:
                d = dialect(path)  # server databases tell the generator their SQL dialect; SQLite calls are unchanged
                sql = generate(req.query, ctx["ddl"], hint=hint, **({} if d == "SQLite" else {"dialect": d}))  # Agent 3 (stand-in)
            except OSError as e:  # model server down / unreachable: say so instead of a bare 500
                log(trace, "agent3.generate", attempt=attempt, error=str(e))
                raise HTTPException(503, f"SQL generator unavailable ({e}). Is the model server (Ollama) running?")
            gen_ms, t = ms(t), time.perf_counter()
            log(trace, "agent3.generate", attempt=attempt, hint=hint, sql=sql)
            ok, result = execute(path, sql)  # Agent 4 (stand-in)
            log(trace, "agent4.execute", attempt=attempt, ok=ok, result=result if not ok else f"{len(result)} rows")
            out["steps"].append({"attempt": attempt, "hint": hint, "sql": sql, "ok": ok, "generate_ms": gen_ms, "execute_ms": ms(t),
                                 **({"rows": len(result)} if ok else {"error": result})})
            if ok:
                cols = sql_columns(path, sql)
                answered[trace] = (req.query, req.db or next(iter(dbs)), sql)
                if len(answered) > 1000:  # ponytail: in-memory, recent answers only; a restart forgets unsaved traces
                    answered.popitem(last=False)
                return {**out, "ok": True, "sql": sql, "columns": cols, "rows": result, "chart": chart_hint(cols, result),
                        "attempts": attempt, "total_ms": ms(t0)}
            if str(result).startswith(BLOCKED):  # unsafe request: refuse, don't coax the model into a different query
                return {**out, "ok": False, "sql": sql, "error": result, "attempts": attempt, "total_ms": ms(t0)}
            hint = f"Your previous query failed with: {result}\nPrevious query: {sql}\nFix it."  # ponytail: Agent 4's error-diagnosis sub-agent replaces this raw-error hint
        return {**out, "ok": False, "sql": sql, "error": result, "attempts": MAX_ATTEMPTS, "total_ms": ms(t0)}

    # --- BI integration: save a trusted answer, replay its frozen SQL (no model involved) ---
    def stored(answer_id):
        a = answers.get(answer_id)
        if a is None:
            raise HTTPException(404, f"no saved answer {answer_id}")
        return a

    def replay(a):
        ok, rows = execute(dbs[a["db"]], a["sql"])  # same read-only guard as live answers
        if not ok:
            raise HTTPException(409, f"saved SQL no longer runs: {rows}")
        return rows

    @app.post("/answers")
    def save_answer(req: SaveAnswer):
        """Saves an answer the pipeline itself produced (by its trace id). Clients can't submit SQL, so this endpoint is no
        back door around Agent 1's no-value-linking setting or the generator."""
        if req.trace not in answered:
            raise HTTPException(404, f"no recent successful answer with trace '{req.trace}'; ask the question again")
        question, name, sql = answered[req.trace]
        ok, rows = execute(dbs[name], sql)  # re-checked: never store SQL that the guard or the read-only connection rejects
        if not ok:
            raise HTTPException(422, f"SQL rejected: {rows}")
        cols = sql_columns(dbs[name], sql)
        answer_id = answers.add(question, name, sql, cols, chart_hint(cols, rows))
        log(req.trace, "bi.save", answer_id=answer_id, question=question, sql=sql)
        return {"id": answer_id, "csv": f"answers/{answer_id}.csv", "chart": chart_hint(cols, rows), "rows": len(rows)}

    @app.get("/answers")
    def list_answers():
        return answers.all()

    @app.get("/answers/{answer_id}.csv", response_class=PlainTextResponse)
    def answer_csv(answer_id: int):
        """Fixed GET URL for BI tools (Power BI Report Server web/CSV source, Excel, Grafana, Tableau): replays the saved SQL."""
        a = stored(answer_id)
        return PlainTextResponse(to_csv(a["columns"], replay(a)), media_type="text/csv")

    @app.get("/answers/{answer_id}")
    def answer_json(answer_id: int):
        a = stored(answer_id)
        return {**a, "rows": replay(a)}

    @app.post("/answers/{answer_id}/superset")
    def answer_to_superset(answer_id: int):
        cfg = superset()
        if cfg is None:
            raise HTTPException(501, "Superset is not configured (set SUPERSET_URL, SUPERSET_USER, SUPERSET_PASSWORD, SUPERSET_DATABASES)")
        a = stored(answer_id)
        if a["superset_chart_id"]:  # already promoted: don't create duplicate charts
            return {"chart_id": a["superset_chart_id"], "url": f"{cfg['url']}/explore/?slice_id={a['superset_chart_id']}", "existing": True}
        try:
            ds, chart, url = push_to_superset(cfg, a)
        except ValueError as e:
            raise HTTPException(422, str(e))
        except Exception as e:  # Superset down / API mismatch: report it, don't 500
            raise HTTPException(502, f"Superset request failed: {e}")
        answers.set_superset(answer_id, chart)
        log(uuid.uuid4().hex[:8], "bi.superset", answer_id=answer_id, dataset=ds, chart=chart)
        return {"dataset_id": ds, "chart_id": chart, "url": url}

    return app


app = create_app()
