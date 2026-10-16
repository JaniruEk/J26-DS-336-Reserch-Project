"""Tests for Agent 3 (dataset builder, evaluation and scoring, recorded non-functional evidence).

Run from the project root:  python -m pytest tests/test_agent3.py
Tests that need generated files (train.jsonl, results/*.json) skip themselves if those files do not exist yet.
HydraLoRA tests need PyTorch and live in tests/test_hydra.py (run in Colab).
"""
import argparse
import json
import sqlite3
from pathlib import Path

import pytest

from agent1_retrieval.complexity import BUCKETS, classify_sql
from agent3_finetune import evaluate as ev

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "agent3_finetune" / "data"
RESULTS = ROOT / "agent3_finetune" / "results"
VRAM_CAP_GB = 8.0  # project hardware budget (RTX 3070 Ti class)


# ---------------------------------------------------------------- functional: output cleaning and metrics
def test_clean_sql_removes_code_fence():
    assert ev.clean_sql("```sql\nSELECT 1\n```") == "SELECT 1"


def test_clean_sql_cuts_after_first_semicolon_and_explanations():
    assert ev.clean_sql("SELECT a FROM t; this is extra") == "SELECT a FROM t"
    assert ev.clean_sql("```sql\nSELECT a FROM t;\n```\nThis counts rows.") == "SELECT a FROM t"


def test_normalise_ignores_case_spacing_and_semicolon():
    assert ev.normalise("SELECT  Name FROM T ;") == ev.normalise("select name from t")
    assert ev.normalise("SELECT a FROM t WHERE x >= 1") == ev.normalise("select a from t where x>=1")


def test_normalise_still_distinguishes_different_queries():
    assert ev.normalise("SELECT a FROM t") != ev.normalise("SELECT b FROM t")


def test_wilson_interval_is_sane():
    lo, hi = ev.wilson(0, 10)
    assert lo <= 1e-9 and 0 < hi < 0.4
    lo, hi = ev.wilson(5, 10)
    assert lo < 0.5 < hi and abs((lo + hi) / 2 - 0.5) < 0.01
    assert ev.wilson(0, 0) == (0.0, 0.0)


def _make_db(path):
    con = sqlite3.connect(path)
    con.execute("create table t (id integer primary key, name text)")
    con.executemany("insert into t values (?, ?)", [(1, "a"), (2, "b")])
    con.execute("create table empty_t (id integer)")
    con.commit()
    con.close()


def _pair(sql, pred, db="x.sqlite"):
    return {"dataset": "spider", "db": db, "question": "q", "sql": sql, "complexity": classify_sql(sql),
            "pred": pred, "prompt_tokens": 5}


def test_score_pipeline_end_to_end(tmp_path, monkeypatch):
    """Predictions -> scored rows: fenced correct SQL counts as correct, wrong SQL as wrong, no-row gold is excluded."""
    monkeypatch.chdir(tmp_path)
    _make_db("x.sqlite")
    preds = [
        _pair("SELECT name FROM t", "```sql\nSELECT name FROM t\n```"),   # correct, with code fence
        _pair("SELECT name FROM t", "SELECT id FROM t"),                  # runs but wrong result
        _pair("SELECT name FROM t", "SELECT nonsense FROM nowhere"),      # invalid SQL must score False, not crash
        _pair("SELECT id FROM empty_t", "SELECT id FROM empty_t"),        # gold returns no rows: not scorable
    ]
    Path("preds.json").write_text(json.dumps({"meta": {"n_prompt_too_long": 0}, "predictions": preds}))
    ev.cmd_score(argparse.Namespace(predictions="preds.json", out="scored.json"))
    rows = json.loads(Path("scored.json").read_text())
    assert [r["exec"] for r in rows] == [True, False, False, None]
    assert rows[0]["exact"] is True and rows[1]["exact"] is False


# ---------------------------------------------------------------- functional: dataset builder output
@pytest.fixture(scope="module")
def splits():
    tr, va = DATA / "train.jsonl", DATA / "val.jsonl"
    if not (tr.exists() and va.exists()):
        pytest.skip("run `python -m agent3_finetune.build_dataset` first")

    def load(p):
        return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    return load(tr), load(va)


def test_split_is_by_database(splits):
    train, val = splits
    assert not ({r["db_id"] for r in train} & {r["db_id"] for r in val}), "validation must use unseen databases"


def test_every_row_has_valid_label_and_schema(splits):
    for part in splits:
        for r in part:
            assert r["complexity"] in BUCKETS
            assert "CREATE TABLE" in r["ddl"].upper()
            assert r["question"].strip() and r["sql"].strip()


def test_labels_match_shared_classifier(splits):
    train, _ = splits
    for r in train[::25]:  # sample of the training rows
        assert classify_sql(r["sql"]) == r["complexity"]


def test_all_buckets_present_in_training(splits):
    train, _ = splits
    assert {r["complexity"] for r in train} == set(BUCKETS)


def test_no_evaluation_question_leaks_into_training(splits):
    banned = set()
    for name in ("spider", "chinook", "tpch"):
        for p in json.loads((ROOT / "eval" / f"{name}_pairs.json").read_text(encoding="utf-8")):
            banned.add(p["question"].strip().lower())
    for part in splits:
        assert not [r for r in part if r["question"].strip().lower() in banned], "evaluation question found in training data"


# ---------------------------------------------------------------- non-functional: evidence recorded in results/
def _recorded_runs():
    out = []
    for p in sorted(RESULTS.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            out.append((p.name, data))
    return out


def test_recorded_peak_memory_is_within_the_8gb_budget():
    seen = 0
    for name, data in _recorded_runs():
        peak = data.get("peak_vram_gb") or data.get("meta", {}).get("peak_vram_gb")
        if peak is not None:
            seen += 1
            assert peak <= VRAM_CAP_GB, f"{name}: peak {peak} GB exceeds the {VRAM_CAP_GB} GB budget"
    if not seen:
        pytest.skip("no run results recorded yet")


def test_training_runs_record_seed_and_configuration():
    seen = 0
    for name, data in _recorded_runs():
        if "trainable_params" in data:
            seen += 1
            for key in ("seed", "rank", "lr", "epochs", "model", "train_examples"):
                assert key in data, f"{name} does not record {key} (reproducibility)"
    if not seen:
        pytest.skip("no training run recorded yet")
