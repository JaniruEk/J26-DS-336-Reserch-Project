"""Orchestration + observability harness (shared infra): sequence agents, log every handoff as JSON lines, bounded retry.
Agent 1 is real. Agents 3 (generate) and 4 (execute) are injectable callables; the defaults are stand-ins
(local phi3 + plain sqlite) until the teammates' components replace them.
Run: uvicorn harness.app:app   |   GET / = Agent 1 Retrieval Explorer   |   GET /chat = team chatbot   |   POST /query {"query": "...", "db": "chinook"}"""
import json
import re
import sqlite3
import time
import uuid
from functools import partial
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, StringConstraints

from agent1_retrieval import MODES, RECOMMENDED, Agent1
from agent1_retrieval.execution import ollama_generate

MAX_ATTEMPTS = 3
MAX_QUESTION = 500  # chars; longer input is rejected at the boundary, before any agent runs
DEFAULT_DBS = {k: p for k, p in {"chinook": "data/chinook.db", "tpch": "data/tpch.db"}.items() if Path(p).exists()} or {"chinook": "data/chinook.db"}


BLOCKED = "Blocked by SQL guard"  # an error starting with this is final: the harness does not retry it


def run_sql(db, sql, timeout=10):
    """Stand-in for Agent 4's Execution sub-agent -> (ok, rows | error message). Read-only; runaway queries are aborted.
    ponytail: keyword guard (first word SELECT/WITH); Agent 4's safety sub-agent replaces it. The read-only connection is the real backstop."""
    if not re.match(r"\s*(SELECT|WITH)\b", sql or "", re.I):
        return False, f"{BLOCKED}: only read-only SELECT queries are allowed."
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    deadline = time.time() + timeout
    con.set_progress_handler(lambda: time.time() > deadline, 10000)
    try:
        return True, con.execute(sql).fetchall()
    except (sqlite3.Error, sqlite3.Warning) as e:  # Python < 3.11 raises Warning for multiple statements
        return False, str(e)
    finally:
        con.close()


def sql_columns(db, sql, timeout=10):
    """Result column names for display. ponytail: re-prepares the query (description is known after the first step);
    move into Agent 4's execute result if the double prepare ever shows up in timings."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    deadline = time.time() + timeout
    con.set_progress_handler(lambda: time.time() > deadline, 10000)
    try:
        return [d[0] for d in con.execute(sql).description or []]
    except sqlite3.Error:
        return []
    finally:
        con.close()


def has_rows(db):
    """False for schema-only databases (e.g. the generated TPC-H file), where every answer would be 'no rows'."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        tables = [t for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return any(con.execute(f'SELECT 1 FROM "{t}" LIMIT 1').fetchone() for t in tables)
    finally:
        con.close()


class Query(BaseModel):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUESTION)]  # empty / too long -> 422
    db: str | None = None  # a key of the configured databases, never a raw path
    mode: str = "hybrid_pruned"


def create_app(dbs=None, generate=partial(ollama_generate, cache=False), execute=run_sql, log_path="data/handoff.log.jsonl",
               agent1_config=RECOMMENDED):
    """agent1_config: Retriever options for the live Agent 1 (pass {} for the original Phase 1-7 settings)."""
    dbs = dbs or DEFAULT_DBS
    app, agents = FastAPI(title="J26-DS-336 harness"), {}
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)

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
            agents[name, req.mode] = Agent1(dbs[name], req.mode, **agent1_config)
        return dbs[name], agents[name, req.mode]

    @app.get("/", include_in_schema=False)
    def explorer():
        return FileResponse(Path(__file__).with_name("explorer.html"))

    @app.get("/chat", include_in_schema=False)
    def chat():
        return FileResponse(Path(__file__).with_name("chat.html"))

    @app.get("/health")
    def health():
        return {"ok": True, "dbs": list(dbs), "schema_only": [n for n, p in dbs.items() if not has_rows(p)], "max_attempts": MAX_ATTEMPTS}

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
                sql = generate(req.query, ctx["ddl"], hint=hint)  # Agent 3 (stand-in)
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
                return {**out, "ok": True, "sql": sql, "columns": sql_columns(path, sql), "rows": result, "attempts": attempt, "total_ms": ms(t0)}
            if str(result).startswith(BLOCKED):  # unsafe request: refuse, don't coax the model into a different query
                return {**out, "ok": False, "sql": sql, "error": result, "attempts": attempt, "total_ms": ms(t0)}
            hint = f"Your previous query failed with: {result}\nPrevious query: {sql}\nFix it."  # ponytail: Agent 4's error-diagnosis sub-agent replaces this raw-error hint
        return {**out, "ok": False, "sql": sql, "error": result, "attempts": MAX_ATTEMPTS, "total_ms": ms(t0)}

    return app


app = create_app()
