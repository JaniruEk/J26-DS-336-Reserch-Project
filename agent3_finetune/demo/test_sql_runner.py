"""Tests for the demo's safe SQL runner. Run from the project root:
    python -m pytest agent3_finetune/demo/test_sql_runner.py -v
"""
import sqlite3

import pytest

from agent3_finetune.demo.sql_runner import check_select, run_query


@pytest.fixture()
def db(tmp_path):
    p = tmp_path / "t.sqlite"
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE singer (id INTEGER, name TEXT)")
    con.executemany("INSERT INTO singer VALUES (?, ?)", [(i, f"s{i}") for i in range(50)])
    con.commit()
    con.close()
    return str(p)


def test_select_runs(db):
    r = run_query(db, "SELECT name FROM singer WHERE id < 3;")
    assert r["ok"] and r["columns"] == ["name"] and len(r["rows"]) == 3
    assert r["status"] == "Ran, 3 rows"


def test_with_select_allowed(db):
    assert run_query(db, "WITH x AS (SELECT id FROM singer) SELECT count(*) FROM x")["ok"]


def test_row_cap_20(db):
    r = run_query(db, "SELECT * FROM singer")
    assert len(r["rows"]) == 20 and r["truncated"] and r["status"] == "Ran, 20+ rows"


@pytest.mark.parametrize("sql", ["DELETE FROM singer", "DROP TABLE singer", "INSERT INTO singer VALUES (1,'x')",
                                 "PRAGMA table_info(singer)", "ATTACH DATABASE 'x.db' AS x", ""])
def test_non_select_refused(db, sql):
    r = run_query(db, sql)
    assert not r["ok"] and r["status"].startswith("Not run")


def test_two_statements_refused(db):
    assert not run_query(db, "SELECT 1; DROP TABLE singer")["ok"]
    assert run_query(db, "SELECT count(*) FROM singer")["rows"] == [[50]]  # table still there


def test_write_hidden_inside_with_is_blocked_by_readonly(db):
    r = run_query(db, "WITH x AS (SELECT 1) DELETE FROM singer")
    assert not r["ok"]
    assert run_query(db, "SELECT count(*) FROM singer")["rows"] == [[50]]


def test_bad_column_friendly(db):
    r = run_query(db, "SELECT nope FROM singer")
    assert not r["ok"] and r["status"].startswith("Failed: no such column")


def test_missing_database():
    assert run_query("/no/such/file.sqlite", "SELECT 1")["status"].startswith("Not run: database file not found")


def test_timeout(db):
    slow = ("WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c) SELECT count(*) FROM c")
    r = run_query(db, slow, timeout_s=1)
    assert not r["ok"] and "longer than 1 seconds" in r["status"]
    assert r["seconds"] < 5


def test_check_select_cleans_trailing_semicolons():
    assert check_select("SELECT 1 ;; ") == (True, "SELECT 1")
