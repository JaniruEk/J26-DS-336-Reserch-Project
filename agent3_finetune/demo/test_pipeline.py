"""Tests for the demo pipeline logic (no torch, no Gradio).
    python -m pytest agent3_finetune/demo/test_pipeline.py -v
"""
import sqlite3

import pytest

from agent3_finetune.demo.pipeline import AUTO, MANUAL, list_databases, resolve_label, run_all

HEADS = ("simple", "single-join", "multi-join", "aggregation")


class FakeEngine:
    def __init__(self, answers):
        self.answers, self.seen = answers, None

    def answer(self, question, db_path, label):
        self.seen = (question, db_path, label)
        return self.answers

    def head_for(self, label):
        return label if label in HEADS else "single-join"


class FakeClassifier:
    def __init__(self, label):
        self.label = label

    def predict(self, q):
        return self.label


@pytest.fixture()
def dbs(tmp_path):
    p = tmp_path / "shop" / "shop.sqlite"
    p.parent.mkdir()
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE t (id INTEGER)")
    con.executemany("INSERT INTO t VALUES (?)", [(i,) for i in range(5)])
    con.commit()
    con.close()
    (tmp_path / "notes.txt").write_text("not a database")
    return list_databases(tmp_path)


def test_list_databases_finds_only_sqlite(dbs):
    assert list(dbs) == ["shop"]


def test_list_databases_missing_folder(tmp_path):
    assert list_databases(tmp_path / "nope") == {}


def test_label_auto_manual_and_fallbacks():
    assert resolve_label("q", AUTO, "simple", FakeClassifier("multi-join"))[0] == "multi-join"
    assert resolve_label("q", MANUAL, "aggregation", FakeClassifier("multi-join"))[0] == "aggregation"
    assert resolve_label("q", AUTO, "simple", None)[0] is None
    assert resolve_label("q", AUTO, "simple", FakeClassifier(None))[0] is None
    label, note = resolve_label("q", AUTO, "simple", FakeClassifier("weird"))
    assert label is None and "unknown label" in note


def test_run_all_three_modes(dbs):
    eng = FakeEngine({
        "base": {"sql": "SELECT count(*) FROM t", "seconds": 0.5, "head": None},
        "lora": {"sql": "DELETE FROM t", "seconds": 0.4, "head": None},          # must be refused
        "hydra": {"error": "RuntimeError: boom", "seconds": None},               # must not crash
    })
    out = run_all(eng, FakeClassifier("simple"), dbs, "how many rows?", "shop", AUTO, "simple")
    assert out["label"] == "simple" and out["routed_head"] == "simple"
    assert out["modes"]["base"]["ok"] and out["modes"]["base"]["rows"] == [[5]]
    assert not out["modes"]["lora"]["ok"] and out["modes"]["lora"]["status"].startswith("Not run")
    assert out["modes"]["hydra"]["status"] == "Failed: RuntimeError: boom"
    assert eng.seen[2] == "simple"
    # the table must still have its 5 rows after the refused DELETE
    ok = run_all(FakeEngine({m: {"sql": "SELECT count(*) FROM t", "seconds": 0, "head": None}
                             for m in ("base", "lora", "hydra")}),
                 None, dbs, "q", "shop", MANUAL, "multi-join")
    assert ok["modes"]["base"]["rows"] == [[5]] and ok["routed_head"] == "multi-join"


def test_wrong_manual_label_is_passed_to_the_engine(dbs):
    eng = FakeEngine({m: {"sql": "SELECT 1", "seconds": 0, "head": None} for m in ("base", "lora", "hydra")})
    run_all(eng, FakeClassifier("simple"), dbs, "q", "shop", MANUAL, "aggregation")
    assert eng.seen[2] == "aggregation"


@pytest.mark.parametrize("q,db", [("", "shop"), ("   ", "shop"), ("hi", "no_such_db")])
def test_bad_input_gives_message_not_crash(dbs, q, db):
    out = run_all(FakeEngine({}), None, dbs, q, db, AUTO, "simple")
    assert "error" in out
