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
    assert set(out) == {"query", "complexity", "mode", "width", "anchor", "matched", "tables", "ddl", "tokens", "latency_ms", "trace"}
    assert out["width"] is None  # no width selector in use
    assert out["complexity"] in BUCKETS and out["anchor"] == "invoice" and out["matched"]
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


def test_render_quotes_only_names_that_need_it(tmp_path):
    """Regression (Northwind): `CREATE TABLE Order Details` made the model write OrderDetails / a syntax error."""
    from agent1_retrieval.schema import render
    p = str(tmp_path / "q.db")
    c = sqlite3.connect(p)
    c.executescript('CREATE TABLE Orders (OrderID INTEGER PRIMARY KEY); CREATE TABLE "Order Details" (OrderID INTEGER REFERENCES Orders(OrderID), "Unit Price" REAL);')
    c.close()
    t = reflect(p)
    assert render(t["Orders"]) == "CREATE TABLE Orders (\n  OrderID INTEGER PRIMARY KEY\n);"  # plain names unchanged
    ddl = render(t["Order Details"])
    assert 'CREATE TABLE "Order Details"' in ddl and '"Unit Price" REAL' in ddl and "REFERENCES Orders(OrderID)" in ddl
    m = sqlite3.connect(":memory:")
    m.executescript(render(t["Orders"]) + ddl)  # the DDL shown to the model is valid SQL, quotes and all
    assert [r[0] for r in m.execute("SELECT name FROM sqlite_master")][-1] == "Order Details"


def test_lower_case_compound_names_are_split_but_real_words_are_not():
    """Regression (PostgreSQL Northwind): lower-cased firstname/productname were pruned as unrelated words."""
    from agent1_retrieval.linking import segment
    assert segment("firstname") == ["first", "name"] and segment("productname") == ["product", "name"]
    assert segment("category") == ["category"] and segment("customer") == ["customer"]


@pytest.mark.skipif(not (ROOT / "agent1_retrieval" / "complexity_schema.joblib").exists(),
                    reason="run scripts/train_complexity_schema.py")
def test_schema_classifier_is_wired_into_handoff(tiny_db):
    from agent1_retrieval import Agent1, BUCKETS
    from agent1_retrieval.complexity import schema_features

    r = Retriever(tiny_db, schema_classifier=True)
    features = schema_features(r, "what is the total of each invoice")
    assert len(features) == 7
    assert all(isinstance(value, int) and value >= 0 for value in features)

    out = Agent1(tiny_db, mode="structural", schema_classifier=True).run(
        "what is the total of each invoice"
    )
    assert out["complexity"] in BUCKETS


def test_adaptive_width_returns_anchor_only_for_confident_simple_question(tiny_db, monkeypatch):
    import agent1_retrieval.retrieval as retrieval_module

    r = Retriever(tiny_db, narrow_simple=0.6)
    r._semantic_anchors = lambda q, k=1: ["invoice"]
    monkeypatch.setattr(retrieval_module, "p_simple", lambda q, retriever=None: 0.99)

    context = r.retrieve("what is the total of each invoice", "hybrid_pruned")

    assert context.columns == {"invoice": ["invoice_id", "total", "notes", "customer_id"]}
    assert context.roles == {"invoice": "anchor"}
    assert set(context.reasons["invoice"].values()) == {"simple_question"}


@pytest.fixture
def coded_db(tmp_path):
    p = str(tmp_path / "coded.db")
    c = sqlite3.connect(p)
    c.executescript("""CREATE TABLE account (account_id INTEGER PRIMARY KEY, holder TEXT, status TEXT, balance REAL);""")
    c.executemany("INSERT INTO account VALUES (?,?,?,?)",
                  [(i, f"Person {i}", "AC"[i % 2] if i < 39 else "D", i * 10.0) for i in range(40)])
    c.commit()
    c.close()
    return p


def test_code_values_finds_codes_never_personal_data(coded_db):
    from agent1_retrieval.linking import code_values
    t = reflect(coded_db)["account"]
    assert code_values(coded_db, t) == {"status": ["A", "C", "D"]}  # rare 'D' (1 of 40 rows) still listed
    assert code_values(coded_db, t, sample=10) == {"status": ["A", "C", "D"]}  # judged on a sample, full list fetched


def test_value_hints_reach_the_schema_and_respect_privacy_and_glossary(coded_db, tmp_path):
    q = "how many dormant accounts are there"
    r = Retriever(coded_db, value_hints=True)
    r._semantic_anchors = lambda q, k=1: ["account"]
    ddl = r.retrieve(q, "hybrid_pruned").text
    assert "status TEXT /* values: 'A', 'C', 'D' */" in ddl and "Person" not in ddl  # codes kept through pruning
    off = Retriever(coded_db, value_hints=True, value_linking=False)  # personal-data database: never reads values
    off._semantic_anchors = lambda q, k=1: ["account"]
    assert "values:" not in off.retrieve(q, "hybrid_pruned").text
    g = tmp_path / "g.json"
    g.write_text('{"Account.Status": "A = active, C = closed, D = dormant"}', encoding="utf-8")
    gl = Retriever(coded_db, glossary=str(g), value_linking=False)  # glossary is configuration: applies even then
    gl._semantic_anchors = lambda q, k=1: ["account"]
    assert "/* A = active, C = closed, D = dormant */" in gl.retrieve(q, "hybrid").text
    assert Retriever(coded_db).retrieve(q, "structural").text.count("/*") == 0  # off by default: earlier results unchanged


def test_complexity_adaptive_width(tiny_db):
    wide = Retriever(tiny_db).retrieve("total of each invoice with the customer name", "hybrid_pruned", complexity="single-join")
    r = Retriever(tiny_db, narrow_simple=0.5)
    narrow = r.retrieve("total of each invoice with the customer name", "hybrid_pruned", complexity="simple")  # oracle: simple
    assert len(narrow.columns) == 1 and len(wide.columns) > 1 and narrow.mode == "hybrid_pruned"
    assert set(narrow.reasons[narrow.anchor].values()) == {"simple_question"}  # whole anchor table, explained
    assert len(r.retrieve("total of each invoice with the customer name", "hybrid_pruned", complexity="single-join").columns) > 1
    assert Retriever(tiny_db, narrow_simple=1.01).retrieve("list invoices", "hybrid_pruned").columns.keys() == \
        Retriever(tiny_db).retrieve("list invoices", "hybrid_pruned").columns.keys()  # threshold never met: unchanged


def test_schema_aware_classifier(tiny_db):
    from agent1_retrieval import BUCKETS, Agent1
    from agent1_retrieval.complexity import classify_query, schema_features
    r = Retriever(tiny_db)
    f = schema_features(r, "total of each invoice with the customer first name")
    assert len(f) == 7 and f[0] == 2 and f[5] == 2  # names 2 tables; 2 tables cover its words
    assert schema_features(r, "list all invoices")[5] == 1
    assert classify_query("total of each invoice with the customer first name", r) in BUCKETS
    out = Agent1(tiny_db, schema_classifier=True).run("total of each invoice with the customer first name")
    assert out["complexity"] in BUCKETS


@pytest.mark.skipif(not (ROOT / "data" / "northwind.db").exists(), reason="needs data/northwind.db")
def test_gate_ignores_function_words_and_loose_similarity():
    nw = Retriever(str(ROOT / "data" / "northwind.db"))
    # 'in' used to match UnitsInStock, so this passed the gate on Northwind (found live in the chat)
    for q in ("What is the weather in Paris?", "Tell me a joke", "best pizza recipe", "What time is it in London?"):
        assert not nw.matched(q), q
    for q in ("Which products are discontinued?", "How many orders did each employee take?",
              "List the names of all shipping companies.", "What is the total freight cost per shipping company?"):
        assert nw.matched(q), q


# ---------------------------------------------------------------- adaptive context width (width.py)
def _width_rows(n=120):
    """Synthetic sweep rows: 'simple' questions are correct only at W1 (wide context distracts), the rest only at W3."""
    import random
    from agent1_retrieval.width import FEATURES, WIDTHS
    rnd = random.Random(0)
    rows = []
    for i in range(n):
        simple = i % 2 == 0
        feats = {f: rnd.random() for f in FEATURES}
        feats["p_simple"] = 0.9 if simple else 0.1
        good = "W1" if simple else "W3"
        rows.append({"id": str(i), "db": f"db{i % 12}", "bucket": "simple" if simple else "multi-join",
                     "ok": {w: w == good for w in WIDTHS}, "runs": {w: w >= good for w in WIDTHS}, "tokens": {w: 10 * (k + 1) for k, w in enumerate(WIDTHS)},
                     "features": feats})
    return rows


def test_width_label_is_the_narrowest_correct_width():
    from agent1_retrieval.width import label
    assert label({"ok": {"W1": False, "W2": True, "W3": True, "W4": False}}) == "W2"
    assert label({"ok": {"W1": False, "W2": False, "W3": False, "W4": False}}) is None


def test_width_selector_learns_and_never_tests_on_a_training_database():
    pytest.importorskip("sklearn")
    from scripts.width_selector import make_model
    from agent1_retrieval.width import accuracy, choose_fixed, choose_oracle, choose_rule, compare, cross_fit
    rows = _width_rows()
    seen = []

    class Spy:
        def __init__(self):
            self.m = make_model()

        def fit(self, X, y):
            self.n = len(X)
            return self.m.fit(X, y)

        def predict(self, X):
            seen.append((self.n, len(X)))
            return self.m.predict(X)

    picked = cross_fit(rows, Spy, folds=4)
    assert all(a + b == len(rows) for a, b in seen)  # train and test parts never overlap
    selector = lambda r: picked[r["id"]]
    assert accuracy(rows, choose_oracle) == 1.0
    assert accuracy(rows, choose_fixed("W1")) == 0.5
    assert accuracy(rows, selector) > 0.9  # p_simple separates the two groups
    assert accuracy(rows, choose_rule()) == 0.5  # the rule sends the non-simple half to W2, which is wrong here
    c = compare(rows, selector, choose_fixed("W1"))
    assert c["wins"] > 0 and c["losses"] == 0 and c["p"] < 0.001 and c["ci"][0] > 0


def test_retry_wider_path_and_complexity_only_ablation():
    pytest.importorskip("sklearn")
    from scripts.width_selector import make_model
    from agent1_retrieval.width import COMPLEXITY_ONLY, WIDTHS, accuracy, cross_fit, retry_path
    row = {"runs": {"W1": False, "W2": False, "W3": True, "W4": True}}
    assert retry_path(row, "W1") == ["W1", "W2", "W3"]
    assert retry_path(row, "W3") == ["W3"]  # it ran: no retry, even if the answer is wrong
    never = {"runs": {w: False for w in WIDTHS}}
    assert retry_path(never, "W1") == ["W1", "W2", "W3"]  # at most 3 attempts, as in the app
    assert retry_path(never, "W4") == ["W4"]  # nothing wider than the full schema
    rows = _width_rows()
    for feats, good in ((COMPLEXITY_ONLY, True), (("q_words",), False)):  # only p_simple carries the signal
        picked = cross_fit(rows, make_model, folds=4, features=feats)
        assert (accuracy(rows, lambda r: picked[r["id"]]) > 0.9) is good


def test_width_selector_script_runs_on_sweep_rows(tmp_path, monkeypatch, capsys):
    pytest.importorskip("sklearn")
    import json
    import sys
    from scripts import width_selector
    f = tmp_path / "rows.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in _width_rows()), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["width_selector", str(f)])
    width_selector.main()
    out = capsys.readouterr().out
    for name in ("learned selector", "learned, cplx only", "W2 + retry wider", "selector + retry", "oracle (limit)"):
        assert name in out


def test_full_schema_width_holds_every_table(tmp_path):
    import sqlite3
    from agent1_retrieval.retrieval import Retriever
    from agent1_retrieval.width import width_context
    p = str(tmp_path / "w.db")
    c = sqlite3.connect(p)
    c.executescript("CREATE TABLE a (id INTEGER PRIMARY KEY, x TEXT); CREATE TABLE b (id INTEGER PRIMARY KEY, a_id INTEGER REFERENCES a(id));")
    c.close()
    ctx = width_context(Retriever(p), "how many b", "W4")
    assert set(ctx.columns) == {"a", "b"} and ctx.columns["b"] == ["id", "a_id"] and ctx.tokens > 0


def test_elbow_keeps_the_tables_before_the_drop():
    from agent1_retrieval.width import elbow_k
    assert elbow_k([0.9, 0.88, 0.2, 0.15, 0.1], alpha=1.0) == 2  # the drop is after the second table
    assert elbow_k([0.9, 0.88, 0.2, 0.15, 0.1], alpha=0.6) == 1
    assert elbow_k([0.9, 0.89, 0.88, 0.1], alpha=1.0) == 3  # three similar tables, then the drop
    assert elbow_k([0.5, 0.4]) == 2 and elbow_k([0.5, 0.5, 0.5]) == 3  # too few tables or no shape: keep all


def test_quant_split_shares_no_database():
    from scripts.make_quant_split import split
    pairs = [{"db": f"db{i % 10}", "question": f"q{i}", "sql": "SELECT a FROM t" if i % 2 else "SELECT count(*) FROM t"}
             for i in range(200)]
    s = split(pairs, {"calibration": 5, "test": 8})
    assert s["calibration"] and s["test"]
    assert not {p["db"] for p in s["calibration"]} & {p["db"] for p in s["test"]}
    assert split(pairs, {"calibration": 5, "test": 8}) == s  # same seed, same sets
