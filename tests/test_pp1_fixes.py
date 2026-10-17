"""PP1 panel fixes for Agent 1: rich linking, explanations, missing FKs, wrong inputs, NFRs."""
import sqlite3
import time
from pathlib import Path

import pytest

from agent1_retrieval import RECOMMENDED, Agent1, Retriever
from agent1_retrieval.linking import ValueLinker, identifier_words, literals, segment
from agent1_retrieval.pruning import explain_columns, query_terms
from agent1_retrieval.schema import adjacency, infer_fks, reflect

ROOT = Path(__file__).parent.parent
CHINOOK = ROOT / "data" / "chinook.db"


@pytest.fixture
def shop(tmp_path):
    p = str(tmp_path / "shop.db")
    c = sqlite3.connect(p)
    c.executescript("""
        CREATE TABLE customer (customer_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, country TEXT, fax TEXT);
        CREATE TABLE orders (o_orderkey INTEGER PRIMARY KEY, o_totalprice REAL, o_orderdate TEXT, o_clerk TEXT,
            customer_id INTEGER REFERENCES customer(customer_id));
        INSERT INTO customer VALUES (1, 'Ann', 'Silva', 'Canada', NULL), (2, 'Ben', 'Perera', 'Sri Lanka', NULL);
    """)
    c.close()
    return p


@pytest.fixture
def nofk(tmp_path):
    p = str(tmp_path / "nofk.db")
    c = sqlite3.connect(p)
    c.executescript("""
        CREATE TABLE region (r_regionkey INTEGER PRIMARY KEY, r_name TEXT);
        CREATE TABLE nation (n_nationkey INTEGER PRIMARY KEY, n_name TEXT, n_regionkey INTEGER);
        CREATE TABLE dept (dept_id INTEGER PRIMARY KEY, dept_name TEXT);
        CREATE TABLE emp (emp_id INTEGER PRIMARY KEY, emp_name TEXT, dept_id INTEGER, salary REAL);
    """)
    c.close()
    return p


# --- function 2: column pruning, rich signals ---------------------------------------------------------------
def test_abbreviated_and_run_together_names_are_readable():
    assert segment("totalprice") == ["total", "price"]
    assert {"account", "balance"} <= identifier_words("c_acctbal", "c")
    assert {"extend", "price"} <= identifier_words("l_extendedprice", "l") or {"extended", "price"} <= identifier_words("l_extendedprice", "l")


def test_rich_pruning_explains_every_column(shop):
    t = reflect(shop)["orders"]
    why = explain_columns(t, query_terms("total price of every order"), rich=True)
    assert why["o_orderkey"] == "primary_key" and why["customer_id"] == "join_key"
    assert why["o_totalprice"] == "lemma_match"  # unreadable to the original lemma rule
    assert why["o_clerk"] == "pruned"
    plain = explain_columns(t, query_terms("total price of every order"))
    assert set(plain) == set(why)  # same columns get a verdict in both rule sets


def test_synonym_and_label_columns(shop):
    t = reflect(shop)
    why = explain_columns(t["orders"], query_terms("how much did each customer spend"), rich=True)
    assert why["o_totalprice"] == "synonym_match"  # "spend" ~ price
    who = explain_columns(t["customer"], query_terms("which customers are there"), rich=True, named=True)
    assert who["first_name"] == who["last_name"] == "label_column" and who["fax"] == "pruned"


def test_value_linking_finds_the_column_of_a_literal(shop):
    assert "Canada" in literals("Which customers are from Canada?")
    hits = ValueLinker(shop, reflect(shop)).link("Which customers are from Sri Lanka?", ["customer", "orders"])
    assert hits == {"customer": {"country"}}


def test_original_rule_set_unchanged_by_default(shop):
    r = Retriever(shop)
    r._semantic_anchors = lambda q, k=1: ["orders"]
    c = r.retrieve("what is the total price of each order", "hybrid_pruned")
    assert "o_totalprice" not in c.columns["orders"]  # documented Phase 3 limitation, reproduced with defaults
    rich = Retriever(shop, rich=True)
    rich._semantic_anchors = lambda q, k=1: ["orders"]
    c2 = rich.retrieve("what is the total price of each order", "hybrid_pruned")
    assert "o_totalprice" in c2.columns["orders"] and c2.reasons["orders"]["o_totalprice"] == "lemma_match"
    assert c2.roles["orders"] == "anchor" and c2.roles["customer"] == "fk_neighbour"


# --- function 1: schema reflection with missing FKs ----------------------------------------------------------
def test_missing_fks_are_inferred_from_names(nofk):
    t = reflect(nofk)
    assert all(not adjacency(t)[n] for n in t)  # nothing declared
    added = infer_fks(t)
    assert ("nation", "n_regionkey", "region") in added and ("emp", "dept_id", "dept") in added
    assert adjacency(t)["emp"] == {"dept"}


def test_retrieval_without_fks_does_not_crash_and_joins_when_inferred(nofk):
    plain = Retriever(nofk)
    plain._semantic_anchors = lambda q, k=1: ["emp"]
    assert list(plain.retrieve("average salary per department", "hybrid").columns) == ["emp"]
    inferred = Retriever(nofk, infer_missing_fks=True)
    inferred._semantic_anchors = lambda q, k=1: ["emp"]
    c = inferred.retrieve("average salary per department", "hybrid")
    assert set(c.columns) == {"emp", "dept"} and "REFERENCES dept" in c.text


# --- handoff contract ----------------------------------------------------------------------------------------
def test_handoff_carries_explanations(shop):
    out = Agent1(shop, "hybrid_pruned", rich=True).run("Which customers are from Canada?")
    assert out["trace"]["reasons"]["customer"]["country"] == "value_match"
    assert out["trace"]["roles"]["customer"] == "anchor"
    assert {"first_name", "last_name", "country"} <= set(out["tables"]["customer"])


# --- NFRs ----------------------------------------------------------------------------------------------------
def _synthetic(path, n):
    c = sqlite3.connect(path)
    for i in range(n):
        parent = f", t{i - 1}_id INTEGER REFERENCES table{i - 1}(t{i - 1}_id)" if i else ""
        c.execute(f"CREATE TABLE table{i} (t{i}_id INTEGER PRIMARY KEY, name TEXT, amount REAL, status TEXT, created TEXT{parent})")
    c.close()


@pytest.mark.parametrize("n", [20, 60])
def test_scales_to_many_tables_within_budget(tmp_path, n):
    db = str(tmp_path / f"s{n}.db")
    _synthetic(db, n)
    r = Retriever(db, **RECOMMENDED)
    r.retrieve("total amount per status")  # warm-up (index build, model load)
    t0 = time.perf_counter()
    c = r.retrieve("total amount per status for each name")
    assert (time.perf_counter() - t0) * 1000 < 500 and c.columns


@pytest.mark.skipif(not CHINOOK.exists(), reason="run scripts/get_chinook.py")
def test_warm_latency_under_500ms_on_chinook():
    r = Retriever(str(CHINOOK), **RECOMMENDED)
    qs = ["Which customers are from Canada?", "How many tracks does each genre have?",
          "What is the total sales amount handled by each support representative?", "List all albums by AC/DC"]
    for q in qs:
        r.retrieve(q)
    worst = max(r.retrieve(q).ms for q in qs)
    assert worst < 500, worst
