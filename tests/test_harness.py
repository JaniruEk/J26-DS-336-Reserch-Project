import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from harness.app import MAX_ATTEMPTS, create_app, run_sql

pytestmark = pytest.mark.skipif(not (Path(__file__).parent.parent / "agent1_retrieval" / "complexity_nl.joblib").exists(),
                                reason="run scripts/train_complexity.py")


@pytest.fixture
def db(tmp_path):
    p = str(tmp_path / "h.db")
    c = sqlite3.connect(p)
    c.executescript("CREATE TABLE invoice (invoice_id INTEGER PRIMARY KEY, total REAL); INSERT INTO invoice VALUES (1, 9.5);")
    c.close()
    return p


def client(db, tmp_path, generate):
    log = tmp_path / "log.jsonl"
    return TestClient(create_app({"t": db}, generate=generate, log_path=str(log))), log


def test_retry_loop_passes_error_hint_and_logs_every_handoff(db, tmp_path):
    seen = []

    def gen(q, ddl, hint=None):
        seen.append(hint)
        return "SELECT total FROM invoice" if hint else "SELECT nope FROM invoice"

    c, log = client(db, tmp_path, gen)
    r = c.post("/query", json={"query": "what is the total of each invoice", "db": "t", "mode": "structural"}).json()
    assert r["ok"] and r["attempts"] == 2 and r["rows"] == [[9.5]]
    assert seen[0] is None and "no such column" in seen[1]  # hint carries the DB error back to generation
    stages = [json.loads(line)["stage"] for line in log.read_text().splitlines()]
    assert stages == ["agent1", "agent3.generate", "agent4.execute", "agent3.generate", "agent4.execute"]


def test_retry_is_bounded(db, tmp_path):
    c, _ = client(db, tmp_path, lambda q, ddl, hint=None: "SELECT nope FROM invoice")
    r = c.post("/query", json={"query": "total invoice", "mode": "structural"}).json()
    assert not r["ok"] and r["attempts"] == MAX_ATTEMPTS


def test_retrieve_endpoint_and_input_validation(db, tmp_path):
    c, _ = client(db, tmp_path, None)
    out = c.post("/retrieve", json={"query": "total of each invoice", "mode": "structural"}).json()
    assert out["anchor"] == "invoice" and "ddl" in out
    assert c.post("/retrieve", json={"query": "x", "db": "/etc/passwd"}).status_code == 404  # no raw paths
    assert c.post("/retrieve", json={"query": "x", "mode": "bogus"}).status_code == 422


def test_run_sql_is_read_only(db):
    assert run_sql(db, "DELETE FROM invoice")[0] is False


def test_empty_or_too_long_question_rejected_before_any_agent(db, tmp_path):
    c, log = client(db, tmp_path, None)
    for q in ["", "   ", "x" * 501]:
        assert c.post("/query", json={"query": q}).status_code == 422
    assert not log.exists()  # nothing reached Agent 1


def test_off_topic_question_declined_without_generation(db, tmp_path):
    called = []
    c, _ = client(db, tmp_path, lambda *a, **k: called.append(1))
    for q in ["asdkjh qwelkj zzxv", "best pizza recipe"]:
        r = c.post("/query", json={"query": q, "mode": "structural"}).json()
        assert not r["ok"] and r["attempts"] == 0 and not r["context"]["matched"] and "couldn't match" in r["error"]
    assert not called


def test_explorer_page_and_db_list(db, tmp_path):
    c, _ = client(db, tmp_path, None)
    assert "Retrieval Explorer" in c.get("/").text
    assert c.get("/dbs").json() == ["t"]


def test_query_returns_per_attempt_trace_with_timings(db, tmp_path):
    c, _ = client(db, tmp_path, lambda q, ddl, hint=None: "SELECT total FROM invoice" if hint else "SELECT nope FROM invoice")
    r = c.post("/query", json={"query": "what is the total of each invoice", "mode": "structural"}).json()
    assert [s["ok"] for s in r["steps"]] == [False, True] and "no such column" in r["steps"][0]["error"]
    assert r["steps"][1]["hint"] and r["steps"][1]["rows"] == 1 and r["columns"] == ["total"] and r["total_ms"] >= 0


def test_generator_down_gives_503_not_500(db, tmp_path):
    def down(*a, **k):
        raise ConnectionRefusedError("refused")
    c, _ = client(db, tmp_path, down)
    r = c.post("/query", json={"query": "total of each invoice", "mode": "structural"})
    assert r.status_code == 503 and "Ollama" in r.json()["detail"]


def test_chat_page_and_health(db, tmp_path):
    c, _ = client(db, tmp_path, None)
    assert "Local SQL Assistant" in c.get("/chat").text
    h = c.get("/health").json()
    assert h["dbs"] == ["t"] and h["schema_only"] == []


def test_runaway_query_is_aborted(db):
    ok, err = run_sql(db, "WITH RECURSIVE r(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM r) SELECT count(*) FROM r", timeout=0.2)
    assert not ok and "interrupt" in err


def test_sql_guard_blocks_non_select_and_multiple_statements(db):
    from harness.app import BLOCKED
    for sql in ["DELETE FROM invoice", "BEGIN TRANSACTION", "DROP TABLE invoice", ""]:
        ok, err = run_sql(db, sql)
        assert not ok and err.startswith(BLOCKED), sql
    assert not run_sql(db, "SELECT 1; DELETE FROM invoice")[0]  # one statement only
    assert not run_sql(db, "WITH x AS (SELECT 1) DELETE FROM invoice")[0]  # passes the keyword guard, read-only connection stops it
    assert run_sql(db, "SELECT total FROM invoice") == (True, [(9.5,)])


def test_blocked_request_is_refused_not_retried(db, tmp_path):
    calls = []
    c, _ = client(db, tmp_path, lambda q, ddl, hint=None: calls.append(hint) or ("DELETE FROM invoice" if not calls[1:] else "BEGIN TRANSACTION"))
    r = c.post("/query", json={"query": "delete every invoice total", "mode": "structural"}).json()
    assert not r["ok"] and r["attempts"] == 1 and "Blocked" in r["error"] and len(calls) == 1
