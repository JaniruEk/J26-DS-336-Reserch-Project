"""Orchestration + observability harness (shared infra): sequence agents, log every handoff as JSON lines, bounded retry.
Agent 1 is real. Agents 3 (generate) and 4 (execute) are injectable callables; the defaults are stand-ins
(local phi3 + plain sqlite) until the teammates' components replace them.
Run: uvicorn harness.app:app   |   POST /query {"query": "...", "db": "chinook"}"""
import json
import sqlite3
import time
import uuid
from functools import partial
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent1_retrieval import MODES, Agent1
from agent1_retrieval.execution import ollama_generate

MAX_ATTEMPTS = 3


def run_sql(db, sql):
    """Stand-in for Agent 4's Execution sub-agent -> (ok, rows | error message)."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return True, con.execute(sql).fetchall()
    except sqlite3.Error as e:
        return False, str(e)
    finally:
        con.close()


class Query(BaseModel):
    query: str
    db: str | None = None  # a key of the configured databases, never a raw path
    mode: str = "hybrid_pruned"


def create_app(dbs=None, generate=ollama_generate, execute=run_sql, log_path="data/handoff.log.jsonl"):
    dbs = dbs or {"chinook": "data/chinook.db"}
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
            agents[name, req.mode] = Agent1(dbs[name], req.mode)
        return dbs[name], agents[name, req.mode]

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
        trace = uuid.uuid4().hex[:8]
        path, a1 = agent1(req)
        ctx = a1.run(req.query)
        log(trace, "agent1", input=req.query, output=ctx)
        hint = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            sql = generate(req.query, ctx["ddl"], hint=hint)  # Agent 3 (stand-in)
            log(trace, "agent3.generate", attempt=attempt, hint=hint, sql=sql)
            ok, result = execute(path, sql)  # Agent 4 (stand-in)
            log(trace, "agent4.execute", attempt=attempt, ok=ok, result=result if not ok else f"{len(result)} rows")
            if ok:
                return {"trace": trace, "ok": True, "sql": sql, "rows": result, "attempts": attempt, "context": ctx}
            hint = f"Your previous query failed with: {result}\nPrevious query: {sql}\nFix it."  # ponytail: Agent 4's error-diagnosis sub-agent replaces this raw-error hint
        return {"trace": trace, "ok": False, "sql": sql, "error": result, "attempts": MAX_ATTEMPTS, "context": ctx}

    return app


app = create_app()
