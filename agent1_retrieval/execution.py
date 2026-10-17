"""Downstream execution accuracy: an SLM writes SQL from Agent 1's context, we run it and compare result sets with the gold SQL.
Agent 3's generator doesn't exist yet, so `ollama_generate` (local phi3, same stand-in the reference prototype used) is a
placeholder for the same `generate(question, ddl) -> sql` interface."""
import hashlib
import json
import re
import sqlite3
import time
import urllib.request
from pathlib import Path

CACHE = Path("data/gen_cache.json")  # generations are cached so reruns/resumes don't re-call the model
_cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


def ollama_generate(question, ddl, model="phi3", url="http://localhost:11434/api/generate", hint=None):
    prompt = (f"You are a SQLite expert. Use only these tables and columns.\n\n{ddl}\n\n"
              f"Question: {question}\n" + (f"{hint}\n" if hint else "")  # no hint -> prompt (and cache key) unchanged
              + "Return exactly one SQLite query and nothing else.")
    key = hashlib.sha1(f"{model}|{prompt}".encode()).hexdigest()
    if key not in _cache:
        req = urllib.request.Request(url, json.dumps({"model": model, "prompt": prompt, "stream": False,
                                                      "options": {"temperature": 0, "num_predict": 256}}).encode(),
                                     {"Content-Type": "application/json"})
        _cache[key] = json.load(urllib.request.urlopen(req, timeout=300))["response"]
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(json.dumps(_cache), encoding="utf-8")
    text = _cache[key]
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    return (m.group(1) if m else text).split(";")[0].strip()


def _rows(db, sql, timeout=10):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    deadline = time.time() + timeout
    con.set_progress_handler(lambda: time.time() > deadline, 10000)  # abort runaway queries
    try:
        return sorted(map(repr, con.execute(sql).fetchall()))
    finally:
        con.close()


def exec_match(db, pred_sql, gold_sql):
    """True/False, or None when the gold query returns no rows (match would be trivial, e.g. the schema-only TPC-H DB).
    ponytail: order-insensitive multiset of rows, column order must match; Spider's official EX is slightly looser."""
    gold = _rows(db, gold_sql)
    if not gold:
        return None
    try:
        return _rows(db, pred_sql) == gold
    except sqlite3.Error:
        return False
