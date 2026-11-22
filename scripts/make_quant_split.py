"""Separate question sets for Agent 4 (quantization): one to SELECT the 8-bit layers, one to TEST the result.

  python -m scripts.get_spider --width        (one time: makes eval/spider_dev_full.json)
  python -m scripts.make_quant_split

The two sets share no database, so the test score of the mixed-precision model is not helped by the layer selection.
  eval/quant_calibration.json   PER_BUCKET questions per complexity bucket, from half of the dev databases
  eval/quant_test.json          PER_BUCKET questions per complexity bucket, from the other half
"""
import json
import random
from pathlib import Path

from agent1_retrieval.complexity import BUCKETS, classify_sql

PER_BUCKET = {"calibration": 25, "test": 50}


def split(pairs, per_bucket=PER_BUCKET, seed=0):
    rnd = random.Random(seed)
    dbs = sorted({p["db"] for p in pairs})
    rnd.shuffle(dbs)
    half = {"calibration": set(dbs[::2]), "test": set(dbs[1::2])}
    out = {}
    for name, own in half.items():
        out[name] = []
        for b in BUCKETS:
            pool = sorted((p for p in pairs if p["db"] in own and classify_sql(p["sql"]) == b), key=lambda p: (p["db"], p["question"]))
            out[name] += rnd.sample(pool, min(per_bucket[name], len(pool)))
    return out


if __name__ == "__main__":
    sets = split(json.loads(Path("eval/spider_dev_full.json").read_text(encoding="utf-8")))
    assert not {p["db"] for p in sets["calibration"]} & {p["db"] for p in sets["test"]}
    for name, rows in sets.items():
        Path(f"eval/quant_{name}.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
        counts = {b: sum(classify_sql(p["sql"]) == b for p in rows) for b in BUCKETS}
        print(f"eval/quant_{name}.json: {len(rows)} questions, {len({p['db'] for p in rows})} databases, {counts}")
