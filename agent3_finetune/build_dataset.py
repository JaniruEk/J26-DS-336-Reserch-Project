"""Agent 3, Phase 1: build the labelled Text-to-SQL training set from Spider *train*.

- Reads data/spider.zip (already downloaded by scripts/get_spider.py).
- Skips nested/compound queries (same rule as the rest of the repo).
- Labels each query with the shared classify_sql (simple / single-join / multi-join / aggregation).
- Attaches the database schema (CREATE TABLE text) as context.
- Splits by DATABASE (train/val), so validation uses schemas the model never saw.
- Removes any question that also appears in eval/*.json (no leakage).
Output: agent3_finetune/data/train.jsonl and val.jsonl
"""
import json
import random
import re
import sqlite3
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

from agent1_retrieval.complexity import BUCKETS, classify_sql

ZIP = "data/spider.zip"
OUT_DIR = Path("agent3_finetune/data")
SEED = 42
VAL_FRACTION = 0.1
NESTED = re.compile(r"\bSELECT\b.*\bSELECT\b|\bINTERSECT\b|\bUNION\b|\bEXCEPT\b", re.I | re.S)


def read_ddl(zf, db_id, cache):
    """Return the CREATE TABLE statements of one Spider database."""
    if db_id in cache:
        return cache[db_id]
    raw = zf.read(f"spider_data/database/{db_id}/{db_id}.sqlite")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"{db_id}.sqlite"
        path.write_bytes(raw)
        con = sqlite3.connect(path)
        con.text_factory = lambda b: b.decode("utf-8", errors="replace")
        rows = con.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        con.close()
    cache[db_id] = ";\n".join(r[0] for r in rows) + ";"
    return cache[db_id]


def eval_questions():
    """All questions used for evaluation; these must never appear in training."""
    qs = set()
    for name in ("spider", "chinook", "tpch"):
        with open(f"eval/{name}_pairs.json", encoding="utf-8") as f:
            qs.update(p["question"].strip().lower() for p in json.load(f))
    return qs


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main():
    zf = zipfile.ZipFile(ZIP)
    raw = json.loads(zf.read("spider_data/train_spider.json"))
    print("Spider train examples:", len(raw))

    flat = [d for d in raw if not NESTED.search(d["query"])]
    print("After removing nested/compound:", len(flat))

    banned = eval_questions()
    flat = [d for d in flat if d["question"].strip().lower() not in banned]
    print("After removing eval questions:", len(flat))

    cache = {}
    rows = []
    for d in flat:
        rows.append({
            "db_id": d["db_id"],
            "question": d["question"],
            "sql": d["query"],
            "complexity": classify_sql(d["query"]),
            "ddl": read_ddl(zf, d["db_id"], cache),
        })

    db_ids = sorted({r["db_id"] for r in rows})
    random.Random(SEED).shuffle(db_ids)
    n_val = max(1, int(len(db_ids) * VAL_FRACTION))
    val_dbs = set(db_ids[:n_val])
    train = [r for r in rows if r["db_id"] not in val_dbs]
    val = [r for r in rows if r["db_id"] in val_dbs]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUT_DIR / "train.jsonl", train)
    write_jsonl(OUT_DIR / "val.jsonl", val)

    print(f"\nDatabases: {len(db_ids)} total, {len(val_dbs)} held out for validation")
    for name, part in (("train", train), ("val", val)):
        counts = Counter(r["complexity"] for r in part)
        print(f"{name}: {len(part)} examples")
        for b in BUCKETS:
            print(f"   {b:15s} {counts.get(b, 0)}")
    print("\nSaved to", OUT_DIR)


if __name__ == "__main__":
    main()