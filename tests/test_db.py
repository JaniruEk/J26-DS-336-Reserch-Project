"""Database layer. SQLite tests always run. PostgreSQL tests run only when J26_TEST_PG is set to a read-only URL of a
Chinook copy made with scripts/load_postgres.py, e.g.
J26_TEST_PG=postgresql+psycopg://ro_user:ro_pass@127.0.0.1:55432/chinook"""
import os
import sqlite3

import pytest

from agent1_retrieval.db import DBError, dialect, is_url, query, quote, redact, session
from agent1_retrieval.schema import reflect

PG = os.environ.get("J26_TEST_PG")
needs_pg = pytest.mark.skipif(not PG, reason="set J26_TEST_PG to a PostgreSQL Chinook copy")


@pytest.fixture
def db(tmp_path):
    p = str(tmp_path / "d.db")
    c = sqlite3.connect(p)
    c.executescript('CREATE TABLE "Odd Name" (id INTEGER PRIMARY KEY, "x""y" TEXT); INSERT INTO "Odd Name" VALUES (1, \'a\');')
    c.close()
    return p


def test_url_detection_and_redaction():
    assert not is_url("data/chinook.db") and is_url("postgresql+psycopg://u:p@h/db")
    assert redact("postgresql+psycopg://ro:s3cr3t@host:5432/bank") == "postgresql+psycopg://ro:***@host:5432/bank"
    assert redact("data/chinook.db") == "data/chinook.db"
    assert redact("postgresql+psycopg://ro:p@ss@w0rd@host/bank") == "postgresql+psycopg://ro:***@host/bank"  # '@' in password
    assert "w0rd" not in redact("could not connect: postgresql://ro:p@ss@w0rd@host/bank refused")


def test_only_enforced_server_dialects_are_accepted():
    for url in ["mysql+pymysql://ro:x@host/bank", "mssql+pyodbc://ro:x@host/bank"]:
        with pytest.raises(DBError, match="not supported yet"):
            query(url, "SELECT 1")
    assert dialect("data/chinook.db") == "SQLite"


def test_sqlite_query_session_quote_and_read_only(db):
    t, c = quote(db, "Odd Name"), quote(db, 'x"y')
    assert query(db, f"SELECT {c} FROM {t} WHERE id = :i", {"i": 1}) == ([c.strip('"').replace('""', '"')], [("a",)])
    with session(db) as run:  # several statements, one connection; a failure doesn't end the session
        with pytest.raises(DBError):
            run("SELECT nope FROM nowhere")
        assert run("SELECT count(*) FROM " + t)[1] == [(1,)]
    with pytest.raises(DBError):
        query(db, f"DELETE FROM {t}")  # read-only connection
    assert query(db, f"SELECT count(*) FROM {t}")[1] == [(1,)]


@needs_pg
def test_pg_reflection_matches_sqlite_chinook():
    s, p = reflect("data/chinook.db"), reflect(PG)
    assert {n.lower() for n in s} == {n.lower() for n in p}
    assert sum(len(t.fks) for t in s.values()) == sum(len(t.fks) for t in p.values())
    assert dialect(PG) == "PostgreSQL"


@needs_pg
def test_pg_is_read_only_even_through_a_cte_and_has_a_timeout():
    for sql in ["DELETE FROM invoiceline", "WITH x AS (DELETE FROM invoiceline RETURNING 1) SELECT count(*) FROM x"]:
        with pytest.raises(DBError, match="read-only"):
            query(PG, sql)
    assert query(PG, "SELECT count(*) FROM invoiceline")[1] == [(2240,)]
    with pytest.raises(DBError, match="timeout"):
        query(PG, "SELECT pg_sleep(3)", timeout=0.3)


@needs_pg
def test_pg_failed_probe_does_not_abort_the_session():
    with session(PG) as run:
        with pytest.raises(DBError):
            run("SELECT nope FROM track")
        assert run("SELECT count(*) FROM track WHERE LOWER(name) = LOWER(:v)", {"v": "Balls to the Wall"})[1] == [(1,)]


@needs_pg
def test_pg_bad_password_is_a_clean_error_without_the_password():
    bad = PG.replace(PG.split("://", 1)[1].split("@")[0], "ro_user:WRONGPASS")
    with pytest.raises(DBError) as e:
        reflect(bad)
    assert "WRONGPASS" not in str(e.value)


@needs_pg
def test_pg_through_the_harness_with_value_linking_switch(tmp_path):
    from fastapi.testclient import TestClient

    from harness.app import create_app
    seen = []

    def gen(q, ddl, hint=None, dialect="SQLite"):
        seen.append(dialect)
        return "SELECT billingcountry, SUM(total) AS revenue FROM invoice GROUP BY billingcountry ORDER BY revenue DESC LIMIT 3"
    make = lambda off: TestClient(create_app({"pg": PG}, generate=gen, log_path=str(tmp_path / "l.jsonl"),
                                             answers_path=str(tmp_path / f"a{len(off)}.db"), superset=lambda: None,
                                             no_value_linking=off))
    c = make(set())
    r = c.post("/query", json={"query": "What is the total revenue per billing country?", "db": "pg"}).json()
    assert r["ok"] and r["rows"][0][0] == "USA" and r["chart"] == "bar" and seen == ["PostgreSQL"]
    a = c.post("/answers", json={"trace": r["trace"]}).json()  # saved by trace: clients never submit SQL
    assert c.get(f"/answers/{a['id']}.csv").text.splitlines()[1].startswith("USA,")
    q = "Which customers are from Canada?"
    on = c.post("/retrieve", json={"query": q, "db": "pg"}).json()
    off = make({"pg"}).post("/retrieve", json={"query": q, "db": "pg"}).json()
    value_reason = lambda out: any("value" in str(why) for t in out["trace"]["reasons"].values() for why in t.values())
    assert value_reason(on) and not value_reason(off)  # switched off: Agent 1 never read customer data values


def test_single_statement_check():
    from agent1_retrieval.db import single_statement
    assert single_statement("SELECT 1") and single_statement("SELECT 1;") and single_statement("SELECT ';' AS x -- a;b")
    assert single_statement("SELECT \"a;b\" FROM t /* x; y */")
    assert not single_statement("SELECT 1; COMMIT; DELETE FROM t") and not single_statement("SELECT 1;DELETE FROM t;")


@needs_pg
def test_pg_multi_statement_cannot_escape_read_only_even_as_owner():
    """Regression: 'SELECT 1; COMMIT; DELETE ...' used to delete a row when connected as a write-capable user."""
    owner = os.environ.get("J26_TEST_PG_OWNER")
    if not owner:
        pytest.skip("set J26_TEST_PG_OWNER to a write-capable URL of the same database")
    from harness.app import run_sql
    before = query(owner, "SELECT count(*) FROM playlisttrack")[1]
    for sql in ["SELECT 1; COMMIT; DELETE FROM playlisttrack WHERE playlistid = 18",
                "SELECT 1; SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE; COMMIT; DELETE FROM playlisttrack",
                "SELECT set_config('default_transaction_read_only', 'off', false)"]:
        run_sql(owner, sql)
        with pytest.raises(DBError):
            query(owner, "DELETE FROM playlisttrack WHERE playlistid = 18")  # the next call is still read-only
    assert query(owner, "SELECT count(*) FROM playlisttrack")[1] == before
