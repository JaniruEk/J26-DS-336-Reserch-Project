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
