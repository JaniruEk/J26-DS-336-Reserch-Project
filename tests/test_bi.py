import json
import sqlite3

import httpx
import pytest
from fastapi.testclient import TestClient

from harness.app import create_app
from harness.bi import chart_hint, push_to_superset


@pytest.fixture
def db(tmp_path):
    p = str(tmp_path / "b.db")
    c = sqlite3.connect(p)
    c.executescript("""CREATE TABLE sales (region TEXT, month TEXT, total REAL);
        INSERT INTO sales VALUES ('North','2026-01',10),('South','2026-01',5),('North','2026-02',7);""")
    c.close()
    return p


def make(db, tmp_path, superset=lambda: None, sql="SELECT region FROM sales"):
    """App whose stand-in generator always answers `sql`; answers can only be saved from a /query trace."""
    return TestClient(create_app({"t": db}, generate=lambda q, ddl, **kw: sql, log_path=str(tmp_path / "log.jsonl"),
                                 answers_path=str(tmp_path / "answers.db"), superset=superset, agent1_config={}))


def ask_and_save(c, question="sales by region per month"):
    r = c.post("/query", json={"query": question, "db": "t", "mode": "structural"}).json()
    return r, c.post("/answers", json={"trace": r["trace"]})


def test_chart_hint_rules():
    assert chart_hint(["n"], [(3,)]) == "number"
    from decimal import Decimal
    assert chart_hint(["region", "total"], [("N", Decimal("1.5"))]) == "bar"  # PostgreSQL NUMERIC
    assert chart_hint(["region", "total"], [("N", 1.0), ("S", 2)]) == "bar"
    assert chart_hint(["month", "total"], [("2026-01", 1.0)]) == "line"
    assert chart_hint(["a", "b", "c"], [(1, 2, 3)]) == "table"
    assert chart_hint(["region", "total"], []) == "table"


def test_save_then_replay_csv_without_the_model(db, tmp_path):
    sql = "SELECT region, SUM(total) AS total FROM sales GROUP BY region ORDER BY region"
    c = make(db, tmp_path, sql=sql)
    q, res = ask_and_save(c)
    r = res.json()
    assert q["ok"] and r["chart"] == "bar" and r["rows"] == 2 and r["csv"] == f"answers/{r['id']}.csv"
    csv1 = c.get(f"/answers/{r['id']}.csv").text
    assert csv1.splitlines() == ["region,total", "North,17.0", "South,5.0"]
    assert c.get(f"/answers/{r['id']}.csv").text == csv1  # replay is deterministic: same SQL, same rows
    assert c.get("/answers").json()[0]["sql"] == sql
    assert c.get(f"/answers/{r['id']}").json()["rows"] == [["North", 17.0], ["South", 5.0]]


def test_answers_only_saves_sql_the_pipeline_produced(db, tmp_path):
    c = make(db, tmp_path, sql="DELETE FROM sales")
    q, res = ask_and_save(c)
    assert not q["ok"] and res.status_code == 404  # refused answer: nothing to save
    assert c.post("/answers", json={"trace": "made-up"}).status_code == 404
    # the old client-SQL shape is rejected outright: no raw SQL door around Agent 1 / value-linking settings
    assert c.post("/answers", json={"question": "x", "db": "t", "sql": "SELECT * FROM sales"}).status_code == 422
    assert c.get("/answers/99.csv").status_code == 404
    assert c.get("/answers").json() == []


def test_saved_sql_that_stops_working_gives_409(db, tmp_path):
    c = make(db, tmp_path)
    _, res = ask_and_save(c)
    a = res.json()
    con = sqlite3.connect(db)
    con.execute("ALTER TABLE sales RENAME TO sales_old")
    con.commit(); con.close()
    assert c.get(f"/answers/{a['id']}.csv").status_code == 409


def test_superset_disabled_gives_501(db, tmp_path):
    c = make(db, tmp_path)
    _, res = ask_and_save(c)
    assert c.post(f"/answers/{res.json()['id']}/superset").status_code == 501
    assert c.get("/health").json()["superset"] is False


def test_superset_needs_explicit_credentials(monkeypatch):
    from harness.bi import superset_config
    monkeypatch.setenv("SUPERSET_URL", "http://bi")
    monkeypatch.delenv("SUPERSET_USER", raising=False)
    monkeypatch.delenv("SUPERSET_PASSWORD", raising=False)
    assert superset_config() is None  # no admin/admin fallback
    monkeypatch.setenv("SUPERSET_USER", "bi_bot")
    monkeypatch.setenv("SUPERSET_PASSWORD", "x")
    assert superset_config()["user"] == "bi_bot"


def test_csv_neutralises_spreadsheet_formulas():
    from harness.bi import to_csv
    out = to_csv(["=cmd", "n"], [("=HYPERLINK(\"http://x\")", -5), ("+1", 3), ("@SUM(A1)", 0), ("safe", 1)]).splitlines()
    assert out[0] == "'=cmd,n" and out[1].startswith("\"'=HYPERLINK") and out[1].endswith(",-5")
    assert out[2] == "'+1,3" and out[3] == "'@SUM(A1),0" and out[4] == "safe,1"


def test_superset_push_sends_dataset_then_chart():
    calls = []

    def handler(req):
        calls.append((req.method, req.url.path, req.headers.get("authorization"), req.content))
        p = req.url.path
        if p == "/api/v1/security/login":
            return httpx.Response(200, json={"access_token": "tok"})
        if p == "/api/v1/security/csrf_token/":
            return httpx.Response(200, json={"result": "csrf"})
        if p == "/api/v1/dataset/" and req.method == "GET":
            return httpx.Response(200, json={"result": []})
        if p == "/api/v1/dataset/":
            return httpx.Response(201, json={"id": 7})
        if p == "/api/v1/chart/":
            return httpx.Response(201, json={"id": 42})
        return httpx.Response(404)

    cfg = {"url": "http://bi", "user": "u", "password": "p", "databases": {"t": 3}}
    answer = {"id": 1, "db": "t", "question": "sales by region", "sql": "SELECT region, total FROM sales",
              "columns": ["region", "total"], "chart": "bar"}
    client = httpx.Client(base_url="http://bi", transport=httpx.MockTransport(handler))
    assert push_to_superset(cfg, answer, client) == (7, 42, "http://bi/explore/?slice_id=42")
    assert [p for _, p, _, _ in calls] == ["/api/v1/security/login", "/api/v1/security/csrf_token/", "/api/v1/dataset/", "/api/v1/dataset/", "/api/v1/chart/"]
    assert calls[3][2] == "Bearer tok" and json.loads(calls[3][3]) == {"database": 3, "table_name": "answer_1", "sql": answer["sql"]}
    chart = json.loads(calls[4][3])
    assert chart["datasource_id"] == 7 and chart["viz_type"] == "echarts_timeseries_bar" and json.loads(chart["params"])["x_axis"] == "region" and json.loads(chart["query_context"])["queries"][0]["columns"] == ["region"]
    with pytest.raises(ValueError):
        push_to_superset({**cfg, "databases": {}}, answer, client)


def test_dashboard_page_remove_and_disconnected_db(db, tmp_path):
    c = make(db, tmp_path, sql="SELECT region, SUM(total) FROM sales GROUP BY region")
    assert "Saved Answers Dashboard" in c.get("/dashboard").text
    _, s = ask_and_save(c)
    aid = s.json()["id"]
    later = TestClient(create_app({"other": db}, generate=lambda q, ddl, **kw: "", log_path=str(tmp_path / "log.jsonl"),
                                  answers_path=str(tmp_path / "answers.db"), superset=lambda: None, agent1_config={}))
    r = later.get(f"/answers/{aid}")  # its database is no longer configured (e.g. runtime connection after a restart)
    assert r.status_code == 409 and "not connected" in r.json()["detail"]
    assert c.delete(f"/answers/{aid}").status_code == 200
    assert c.get(f"/answers/{aid}").status_code == 404 and c.delete(f"/answers/{aid}").status_code == 404
