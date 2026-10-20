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
    return TestClient(create_app({"t": db}, generate=generate, log_path=str(log), answers_path=str(tmp_path / "answers.db"),
                                 superset=lambda: None)), log


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
    assert stages == ["agent1", "agent2.gate", "agent3.generate", "agent4.execute", "agent3.generate", "agent4.execute"]


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
    assert "Pipeline Explorer" in c.get("/").text
    ex = c.get("/examples.js")  # one list of example questions for the chat page and the explorer
    assert ex.status_code == 200 and "javascript" in ex.headers["content-type"] and "const EXAMPLES" in ex.text
    assert c.get("/dbs").json() == ["t"]
    a = c.get("/agents").json()  # what each agent runs, for the explorer's tabs
    assert a["gate"]["stand_in"] and a["generate"]["stand_in"] and a["execute"]["stand_in"]
    assert a["quantization"] is None or {"layers", "runs"} <= set(a["quantization"])


def test_quantization_results_read_agent4_files(tmp_path):
    from harness.app import quantization_results
    assert quantization_results(tmp_path) is None  # her files missing: the explorer says so instead of failing
    (tmp_path / "qwen_precision_allocation.csv").write_text("layer,sensitivity_score,precision\n0,0.1,INT8\n")  # what her model loads
    (tmp_path / "fp16_results.csv").write_text("EX,latency,peak_vram_mb\n1,2.0,100\n0,4.0,100\n")
    (tmp_path / "int4_results.csv").write_text("EX,latency,peak_vram_mb\n1,1.0,40\n")
    q = quantization_results(tmp_path)
    assert q["layers"][0]["precision"] == "INT8"
    assert q["runs"] == [{"config": "FP16", "n": 2, "ex": 0.5, "latency_s": 3.0, "mem_vs_fp16": 1.0},
                         {"config": "Uniform INT4", "n": 1, "ex": 1.0, "latency_s": 1.0, "mem_vs_fp16": 0.4}]


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


def test_chat_page_and_health(db, tmp_path, monkeypatch):
    c, _ = client(db, tmp_path, lambda q, ddl, **kw: "SELECT 1")
    assert "Local SQL Assistant" in c.get("/chat").text
    h = c.get("/health").json()
    assert h["dbs"] == ["t"] and h["schema_only"] == []
    assert h["stand_ins"] == ["gate", "execute"]  # a real generator injected; executor and gate are still placeholders
    monkeypatch.delenv("J26_GENERATOR", raising=False)
    h = client(db, tmp_path, None)[0].get("/health").json()  # default: phi3 via Ollama, a stand-in
    assert h["stand_ins"] == ["gate", "generate", "execute"] and h["generator"] == "phi3 via Ollama"
    monkeypatch.setenv("J26_GENERATOR", "ollama:qwen2.5-coder:1.5b-instruct")
    assert client(db, tmp_path, None)[0].get("/health").json()["generator"] == "qwen2.5-coder:1.5b-instruct via Ollama"
    monkeypatch.setenv("J26_GENERATOR", "nonsense")
    with pytest.raises(ValueError):
        client(db, tmp_path, None)


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


def test_wrong_inputs_are_rejected_cleanly(db, tmp_path):
    c, _ = client(db, tmp_path, lambda q, ddl, hint=None: "SELECT 1")
    assert c.post("/retrieve", json={"query": "   ", "db": "t"}).status_code == 422
    assert c.post("/retrieve", json={"query": "x" * 501, "db": "t"}).status_code == 422
    assert c.post("/retrieve", json={"db": "t"}).status_code == 422
    assert c.post("/retrieve", json={"query": "invoices", "db": "../../etc/passwd"}).status_code == 404
    assert c.post("/retrieve", json={"query": "invoices", "db": "t", "mode": "magic"}).status_code == 422
    r = c.post("/query", json={"query": "asdkjh qwelkj zzzz", "db": "t"}).json()
    assert r["ok"] is False and r["attempts"] == 0  # gibberish is declined before any model call


def test_multiple_statements_are_an_error_not_a_crash(db):
    ok, err = run_sql(db, "SELECT 1; SELECT 2")
    assert not ok and err


def test_chat_page_has_save_as_chart(db, tmp_path):
    c, _ = client(db, tmp_path, None)
    page = c.get("/chat").text
    assert "Save as chart" in page and 'fetch("answers"' in page


def test_add_database_at_runtime(db, tmp_path):
    up = tmp_path / "uploads"
    make = lambda **kw: TestClient(create_app({"t": db}, generate=lambda q, ddl, **k: "SELECT total FROM invoice",
                                              log_path=str(tmp_path / "l.jsonl"), answers_path=str(tmp_path / "a.db"),
                                              superset=lambda: None, uploads_dir=str(up), **kw))
    c = make(admin_token="t0k", admin_hosts={"testserver"}, db_hosts=set())
    H = {"X-J26-Admin": "t0k"}
    r = c.post("/dbs/upload?name=shop", content=Path(db).read_bytes(), headers=H)
    assert r.status_code == 200 and r.json()["tables"] == 1 and (up / "shop.db").exists()
    assert c.post("/query", json={"query": "total of each invoice", "db": "shop"}).json()["rows"] == [[9.5]]
    assert c.post("/dbs/upload?name=shop", content=Path(db).read_bytes(), headers=H).status_code == 409  # never overwrite
    assert (up / "shop.db").stat().st_size > 0  # the refused upload did not touch the existing file
    assert c.post("/dbs/upload?name=..%2Fevil", content=b"x", headers=H).status_code == 422  # name is the file name: no paths
    assert c.post("/dbs/upload?name=junk", content=b"not a database", headers=H).status_code == 400
    assert not (up / "junk.db").exists() and not list(up.glob("*.part"))
    assert c.post("/dbs", json={"name": "p", "url": db}, headers=H).status_code == 422  # a client can't point at a file on disk
    r = c.post("/dbs", json={"name": "m", "url": "mysql+pymysql://u:secret@h/x"}, headers=H)
    assert r.status_code == 422 and "secret" not in r.text  # only read-only-enforced dialects; password never echoed
    for bad in ("postgresql+psycopg://u:p@h/x?host=/var/run", "postgresql+psycopg://u:p@h/x?passfile=/etc/x",
                "postgresql+psycopg://u:p@/x"):  # no host overrides, files or Unix sockets
        assert c.post("/dbs", json={"name": "q", "url": bad}, headers=H).status_code == 422, bad
    r = c.post("/dbs", json={"name": "q", "url": "postgresql+psycopg://u:p@127.0.0.1:1/x?connect_timeout=1"}, headers=H)
    assert r.status_code == 400 and "could not connect" in r.json()["detail"]  # generic: no driver detail to probe with
    assert c.get("/dbs").json() == ["t", "shop"]
    # admin only, never from another site
    assert c.post("/dbs/upload?name=a1", content=Path(db).read_bytes()).status_code == 403  # no custom header
    assert c.post("/dbs/upload?name=a1", content=Path(db).read_bytes(), headers={"X-J26-Admin": "nope"}).status_code == 403
    assert make(admin_token="t0k").post("/dbs/upload?name=a1", content=b"x", headers=H).status_code == 403  # Host 'testserver' not allowed
    assert make(admin_token="", admin_hosts={"testserver"}).post(  # no token set: only this machine ('testclient' is not)
        "/dbs/upload?name=a1", content=b"x", headers={"X-J26-Admin": "local"}).status_code == 403
    local = TestClient(create_app({"t": db}, log_path=str(tmp_path / "l.jsonl"), answers_path=str(tmp_path / "a.db"),
                                  superset=lambda: None, uploads_dir=str(up), admin_token="", admin_hosts={"testserver"}),
                       client=("127.0.0.1", 50000))  # a direct request from this machine, no token configured
    assert local.post("/dbs/upload?name=l1", content=Path(db).read_bytes(), headers={"X-J26-Admin": "local"}).status_code == 200
    r = local.post("/dbs/upload?name=l2", content=Path(db).read_bytes(),  # same peer via a reverse proxy: refused
                   headers={"X-J26-Admin": "local", "X-Forwarded-For": "10.0.0.5"})
    assert r.status_code == 403 and "proxy" in r.json()["detail"]
    assert make(admin_token="t0k", admin_hosts={"testserver"}, db_hosts={"db.bank.local"}).post(
        "/dbs", json={"name": "q", "url": "postgresql+psycopg://u:p@evil.example/x"}, headers=H).status_code == 403


def test_question_gate_agent2(db, tmp_path):
    def make(gate):
        return TestClient(create_app({"t": db}, generate=lambda q, ddl, **kw: "SELECT total FROM invoice", log_path=str(tmp_path / "g.jsonl"),
                                     answers_path=str(tmp_path / "ga.db"), superset=lambda: None, gate=gate))
    general = lambda q: {"database": False, "p_database": 0.02}
    general.label, general.stand_in = "Agent 2 test gate", False
    c = make(general)
    assert "gate" not in c.get("/health").json()["stand_ins"]  # a real gate removes the stand-in badge
    r = c.post("/query", json={"query": "total of each invoice", "mode": "structural"}).json()
    assert not r["ok"] and r["attempts"] == 0 and r["gate"] == {"by": "Agent 2 test gate", "database": False, "p_database": 0.02}
    assert "general question" in r["error"]
    data = lambda q: {"database": True, "p_database": 0.99}
    data.label, data.stand_in = "Agent 2 test gate", False
    assert make(data).post("/query", json={"query": "total of each invoice", "mode": "structural"}).json()["ok"]
    def broken(q):
        raise RuntimeError("CUDA out of memory")
    broken.label, broken.stand_in = "Agent 2 test gate", False
    r = make(broken).post("/query", json={"query": "total of each invoice", "mode": "structural"}).json()
    assert r["ok"] and "CUDA out of memory" in r["gate"]["error"]  # her model failing never blocks the pipeline
    r = make(None).post("/query", json={"query": "total of each invoice", "mode": "structural"}).json()
    assert r["ok"] and r["gate"]["by"] == "Agent 1's word-match check"
