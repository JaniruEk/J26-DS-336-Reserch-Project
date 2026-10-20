"""Hard test: multi-table joins + aggregation (eval/hard_pairs.json, from scripts/make_hard_pairs.py).
Execution accuracy by number of joins for each Agent 1 configuration, paired vs the unpruned hybrid, plus an
automatic error label for every wrong answer (written to data/hard_eval_<model>.json for checking by hand).
Usage: python -m scripts.hard_eval [model]   (default qwen2.5-coder:1.5b-instruct; generations cached)"""
import json
import re
import sys
from statistics import mean

from agent1_retrieval import LIVE, RECOMMENDED, Retriever
from agent1_retrieval.db import DBError, query
from agent1_retrieval.evaluate import gold_links, prf
from agent1_retrieval.execution import exec_match, ollama_generate
from agent1_retrieval.stats import mcnemar_exact

model = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5-coder:1.5b-instruct"
pairs = json.load(open("eval/hard_pairs.json", encoding="utf-8"))
CONFIGS = {"hybrid (no pruning)": ("hybrid", RECOMMENDED), "hybrid_pruned": ("hybrid_pruned", RECOMMENDED),
           "hybrid_pruned + value hints (live)": ("hybrid_pruned", {k: v for k, v in LIVE.items() if k != "schema_classifier"})}
AGG = re.compile(r"\b(count|sum|avg|min|max)\s*\(", re.I)


def label(db, pred, gold, tables):
    """Why a wrong answer is wrong (first matching reason). Heuristic: check by hand before quoting."""
    try:
        query(db, pred)
    except DBError as e:
        m = str(e).lower()
        if "no such column" in m:
            col = m.split("no such column:")[-1].strip().split(".")[-1]
            return "column via wrong table/alias" if any(col == c.lower() for t in tables.values() for c, _, _ in t.columns) else "invented column"
        return "invented table" if "no such table" in m else "SQL error"
    gt, pt = gold_links(tables, gold)[0], gold_links(tables, pred)[0]
    if gt - pt:
        return "missing table"
    if pt - gt:
        return "extra table"
    if sorted(x.lower() for x in AGG.findall(gold)) != sorted(x.lower() for x in AGG.findall(pred)):
        return "wrong aggregate"
    if bool(re.search(r"\bgroup\s+by\b", gold, re.I)) != bool(re.search(r"\bgroup\s+by\b", pred, re.I)):
        return "missing/extra GROUP BY"
    return "wrong columns/filter/grouping"


retr, res = {}, {}
for name, (mode, kw) in CONFIGS.items():
    out = []
    for p in pairs:
        key = (p["db"], name)
        if key not in retr:
            retr[key] = Retriever(p["db"], **kw)
        r = retr[key]
        ctx = r.retrieve(p["question"], mode)
        sql = ollama_generate(p["question"], ctx.text, model)
        ok = exec_match(p["db"], sql, p["sql"])
        gc = gold_links(r.tables, p["sql"])[1]
        rec = prf({(t, c) for t, cs in ctx.columns.items() for c in cs}, gc)[1]
        out.append({"question": p["question"], "db": p["db"], "joins": p["joins"], "ok": bool(ok), "tokens": ctx.tokens,
                    "colR": rec, "pred": sql, "gold": p["sql"], "why": None if ok else label(p["db"], sql, p["sql"], r.tables)})
    res[name] = out

base = res["hybrid (no pruning)"]
groups = (("2 joins", lambda j: j == 2), ("3+ joins", lambda j: j >= 3), ("all", lambda j: True))
print(f"model {model}; {len(pairs)} questions (2 joins: {sum(p['joins'] == 2 for p in pairs)}, 3+: {sum(p['joins'] >= 3 for p in pairs)}); all need aggregation")
print(f"{'config':<36}" + "".join(f"{g:>10}" for g, _ in groups) + f"{'tokens':>8}{'colR':>6}{'+/- vs hybrid':>15}{'p':>7}")
for name, out in res.items():
    acc = lambda f: mean(o["ok"] for o in out if f(o["joins"]))
    win = sum(o["ok"] and not b["ok"] for o, b in zip(out, base))
    loss = sum(b["ok"] and not o["ok"] for o, b in zip(out, base))
    print(f"{name:<36}" + "".join(f"{acc(f):>10.2f}" for _, f in groups)
          + f"{mean(o['tokens'] for o in out):>8.0f}{mean(o['colR'] for o in out):>6.2f}{f'{win}/{loss}':>15}{mcnemar_exact(win, loss):>7.3f}")
for name, out in res.items():
    why = {}
    for o in out:
        if o["why"]:
            why[o["why"]] = why.get(o["why"], 0) + 1
    print(f"\nerrors, {name} ({sum(not o['ok'] for o in out)} wrong):", dict(sorted(why.items(), key=lambda kv: -kv[1])))
json.dump(res, open(f"data/hard_eval_{model.split(':')[0]}.json", "w", encoding="utf-8"), indent=1)
