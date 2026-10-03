import json
import sqlite3
from pathlib import Path

import pytest

from agent1_retrieval import Retriever, classify_sql
from agent1_retrieval.evaluate import gold_links
from agent1_retrieval.schema import adjacency, reflect

ROOT = Path(__file__).parent.parent
CHINOOK = ROOT / "data" / "chinook.db"


@pytest.fixture
def tiny_db(tmp_path):
    p = str(tmp_path / "t.db")
    c = sqlite3.connect(p)
    c.executescript("""
        CREATE TABLE customer (customer_id INTEGER PRIMARY KEY, first_name TEXT, fax TEXT, company TEXT);
        CREATE TABLE invoice (invoice_id INTEGER PRIMARY KEY, total REAL, notes TEXT,
            customer_id INTEGER REFERENCES customer(customer_id));
        CREATE TABLE orphan (id INTEGER PRIMARY KEY, blob TEXT);  -- no FKs at all
    """)
    c.close()
    return p


def test_classify():
    assert classify_sql("SELECT Name FROM Artist") == "simple"
    assert classify_sql("SELECT * FROM a JOIN b ON 1=1") == "single-join"
    assert classify_sql("SELECT * FROM a JOIN b ON 1=1 JOIN c ON 1=1") == "multi-join"
    assert classify_sql("SELECT a FROM t JOIN u ON 1=1 GROUP BY a") == "aggregation"


def test_reflect_and_missing_fks(tiny_db):
    t = reflect(tiny_db)
    adj = adjacency(t)
    assert adj["customer"] == {"invoice"} and adj["invoice"] == {"customer"}
    assert adj["orphan"] == set()  # table without FKs must not break the graph


def test_structural_mode_and_traversal(tiny_db):
    r = Retriever(tiny_db)
    c = r.retrieve("what is the total of each invoice", "structural")
    assert c.anchor == "invoice" and list(c.columns) == ["invoice"]  # no traversal in structural mode
    assert r._traverse("invoice") == ["invoice", "customer"]


def test_pruning_keeps_keys_and_relevant_drops_rest(tiny_db):
    r = Retriever(tiny_db)
    r.depth = 1
    r._semantic_anchors = lambda q, k=1: ["invoice"]  # isolate pruning from the embedding model
    c = r.retrieve("what is the total of each invoice", "hybrid_pruned")
    assert {"invoice_id", "customer_id", "total"} <= set(c.columns["invoice"])
    assert "notes" not in c.columns["invoice"]
    assert c.columns["customer"] == ["customer_id"]  # only the join key survives
    assert c.tokens > 0


def test_gold_links_aliases():
    t = reflect(str(CHINOOK)) if CHINOOK.exists() else pytest.skip("run scripts/get_chinook.py")
    gt, gc = gold_links(t, "SELECT t.Name FROM Track t JOIN Genre g ON t.GenreId = g.GenreId WHERE g.Name = 'Rock';")
    assert gt == {"Track", "Genre"}
    assert ("Track", "Name") in gc and ("Genre", "Name") in gc and ("Track", "GenreId") in gc


@pytest.mark.skipif(not CHINOOK.exists(), reason="run scripts/get_chinook.py")
def test_eval_pairs_are_valid_against_chinook():
    con = sqlite3.connect(CHINOOK)
    for p in json.load(open(ROOT / "eval" / "chinook_pairs.json", encoding="utf-8")):
        con.execute(p["sql"]).fetchall()  # gold SQL must execute
    con.close()


def test_pruning_keeps_columns_named_by_spacy_stop_words(tiny_db):
    r = Retriever(tiny_db)
    r._semantic_anchors = lambda q, k=1: ["customer"]
    assert "first_name" in r.retrieve("show the first name of each customer", "hybrid_pruned").columns["customer"]


@pytest.mark.parametrize("name", ["tpch", "spider"])
def test_other_eval_pairs_are_wellformed(name):
    f = ROOT / "eval" / f"{name}_pairs.json"
    if not f.exists():
        pytest.skip("run scripts/make_tpch.py / scripts/get_spider.py")
    for p in json.load(open(f, encoding="utf-8")):
        if not (ROOT / p["db"]).exists():
            pytest.skip("database missing")
        sqlite3.connect(ROOT / p["db"]).execute("EXPLAIN " + p["sql"])  # gold SQL must compile against its DB


MODEL = ROOT / "agent1_retrieval" / "complexity_nl.joblib"


@pytest.mark.skipif(not MODEL.exists(), reason="run scripts/train_complexity.py")
def test_nl_classifier_and_handoff_contract(tiny_db):
    import json as _json
    from agent1_retrieval import BUCKETS, Agent1, classify_query
    assert classify_query("How many customers are there in each market segment?") == "aggregation"
    out = Agent1(tiny_db, mode="structural").run("what is the total of each invoice")
    assert set(out) == {"query", "complexity", "mode", "anchor", "tables", "ddl", "tokens", "latency_ms"}
    assert out["complexity"] in BUCKETS and out["anchor"] == "invoice"
    assert _json.loads(_json.dumps(out)) == out  # contract must survive JSON transport


def test_stats_and_exec_match(tmp_path):
    from agent1_retrieval.execution import exec_match
    from agent1_retrieval.stats import bootstrap_ci, mcnemar_exact
    assert mcnemar_exact(0, 0) == 1.0 and mcnemar_exact(5, 0) == pytest.approx(0.0625)
    m, lo, hi = bootstrap_ci([1.0, 1.0, 1.0])
    assert m == lo == hi == 1.0
    db = str(tmp_path / "e.db")
    c = sqlite3.connect(db)
    c.executescript("CREATE TABLE t (a INTEGER, b TEXT); INSERT INTO t VALUES (1,'x'),(2,'y'); CREATE TABLE empty (a INTEGER);")
    c.close()
    assert exec_match(db, "SELECT b, a FROM t ORDER BY a DESC", "SELECT b, a FROM t") is True  # row order ignored
    assert exec_match(db, "SELECT a FROM t", "SELECT b FROM t") is False
    assert exec_match(db, "SELEKT nonsense", "SELECT a FROM t") is False  # invalid SQL = miss, not crash
    assert exec_match(db, "SELECT a FROM empty", "SELECT a FROM empty") is None  # trivial match is excluded
