"""Tests for the cached-answers module (no torch, no Gradio).
    python -m pytest agent3_finetune/demo/test_cache.py -v
"""
import json
import sqlite3

import pytest

from agent3_finetune.demo.cache import EXAMPLES, build_cache, load_cache, save_cache

HEADS = ("simple", "single-join", "multi-join", "aggregation")


class FakeEngine:
    def answer(self, question, db_path, label):
        return {m: {"sql": "SELECT count(*) FROM t", "seconds": 0.1, "head": None} for m in ("base", "lora", "hydra")}

    def head_for(self, label):
        return label if label in HEADS else "single-join"


@pytest.fixture()
def dbs(tmp_path):
    out = {}
    for name in sorted({e["db"] for e in EXAMPLES}):
        p = tmp_path / f"{name}.sqlite"
        con = sqlite3.connect(p)
        con.execute("CREATE TABLE t (id INTEGER)")
        con.execute("INSERT INTO t VALUES (1)")
        con.commit()
        con.close()
        out[name] = str(p)
    return out


def test_every_example_has_what_the_pipeline_needs():
    for e in EXAMPLES:
        assert e["title"] and e["question"].strip() and e["db"]
        if "label_mode" in e:
            assert e.get("manual_label") in HEADS


def test_build_save_load_roundtrip(dbs, tmp_path):
    cache = build_cache(FakeEngine(), None, dbs, meta={"gpu": "fake"})
    assert len(cache["examples"]) == len(EXAMPLES)
    assert all("error" not in e["result"] for e in cache["examples"])
    p = tmp_path / "sub" / "examples.json"
    save_cache(cache, p)
    back = load_cache(p)
    assert back["meta"]["gpu"] == "fake"
    assert back["examples"][0]["result"]["modes"]["base"]["rows"] == [[1]]


def test_wrong_label_example_uses_manual_label(dbs):
    cache = build_cache(FakeEngine(), None, dbs)
    wrong = [e for e in cache["examples"] if e["title"].startswith("3.")][0]["result"]
    assert wrong["label"] == "simple" and wrong["routed_head"] == "simple"


def test_missing_database_is_recorded_as_error_not_crash(dbs):
    dbs = dict(dbs)
    dbs.pop("chinook")
    cache = build_cache(FakeEngine(), None, dbs)
    assert any("error" in e["result"] for e in cache["examples"])


@pytest.mark.parametrize("content", ["[]", "{}", '{"examples": []}', '{"examples": [{"title": "x"}]}'])
def test_load_rejects_bad_files(tmp_path, content):
    p = tmp_path / "bad.json"
    p.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        load_cache(p)


def test_load_rejects_non_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_cache(p)


def test_every_manual_example_routes_to_its_manual_label(dbs):
    cache = build_cache(FakeEngine(), None, dbs)
    manual = [(ex, e["result"]) for ex, e in zip(EXAMPLES, cache["examples"]) if "label_mode" in ex]
    assert len(manual) >= 4
    for ex, res in manual:
        assert res["label"] == ex["manual_label"] and res["routed_head"] == ex["manual_label"]


def test_routing_pairs_share_a_question_but_not_a_label():
    manual = [e for e in EXAMPLES if "label_mode" in e]
    by_q = {}
    for e in manual:
        by_q.setdefault((e["db"], e["question"]), set()).add(e["manual_label"])
    assert all(len(labels) >= 2 for labels in by_q.values())  # each question appears with a right and a wrong head
