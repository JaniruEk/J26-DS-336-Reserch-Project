"""Evaluation harness: token count, latency and schema-linking precision/recall for each
retrieval mode, stratified by complexity bucket.
Usage: python -m agent1_retrieval.evaluate --db data/chinook.db --pairs eval/chinook_pairs.json
(Downstream SQL execution accuracy needs Agent 3's generator and is not measured here.)"""
import argparse
import json
import re
from collections import defaultdict
from statistics import mean

from .complexity import BUCKETS, classify_sql
from .execution import exec_match, ollama_generate
from .retrieval import MODES, Retriever
from .stats import bootstrap_ci, mcnemar_exact

SQL_KW = {"where", "on", "group", "order", "inner", "left", "right", "join", "limit", "having", "using", "union"}


def gold_links(tables, sql):
    """Gold (tables, columns) read from the SQL by name/alias matching.
    ponytail: regex, not a SQL parser — no subquery/CTE scoping; swap in sqlglot if gold extraction gets wrong."""
    lower = {n.lower(): n for n in tables}
    alias = {}
    for t, a in re.findall(r"\b(?:from|join)\s+(\w+)(?:\s+(?:as\s+)?(\w+))?", sql, re.I):
        if t.lower() in lower:
            alias[t.lower()] = lower[t.lower()]
            if a and a.lower() not in SQL_KW:
                alias[a.lower()] = lower[t.lower()]
    gt = set(alias.values())
    has = lambda t, c: c.lower() in {x.lower() for x, _, _ in tables[t].columns}
    gc = set()
    for q, c in re.findall(r"\b(\w+)\.(\w+)\b", sql):
        t = alias.get(q.lower())
        if t and has(t, c):
            gc.add((t, next(x for x, _, _ in tables[t].columns if x.lower() == c.lower())))
    for w in set(re.findall(r"\w+", re.sub(r"\b\w+\.\w+\b", " ", sql).lower())):  # unqualified -> every gold table having it
        gc |= {(t, x) for t in gt for x, _, _ in tables[t].columns if x.lower() == w}
    return gt, gc


def prf(pred, gold):
    hit = len(pred & gold)
    return (hit / len(pred) if pred else 0.0), (hit / len(gold) if gold else 1.0)


def run(db, pairs, modes=MODES, quiet=False, generate=None, **kw):
    """Rows per (mode, bucket|ALL): (tokens, ms, tblP, tblR, colP, colR, exec_ok|None).
    generate(question, ddl) -> sql enables execution accuracy (needs a DB with data)."""
    retrievers = {}  # pairs may carry their own "db" (Spider spans many); `db` is the fallback
    rows = defaultdict(list)
    for p in pairs:
        path = p.get("db", db)
        if path not in retrievers:
            retrievers[path] = Retriever(path, **kw)
        r = retrievers[path]
        gt, gc = gold_links(r.tables, p["sql"])
        bucket = classify_sql(p["sql"])
        for mode in modes:
            ctx = r.retrieve(p["question"], mode)
            pt, rt = prf(set(ctx.columns), gt)
            pc, rc = prf({(t, c) for t, cs in ctx.columns.items() for c in cs}, gc)
            ex = None
            if generate:
                try:
                    ex = exec_match(path, generate(p["question"], ctx.text), p["sql"])
                except Exception as e:  # model/connection failure counts as a miss but is reported
                    print("generate failed:", type(e).__name__, e)
                    ex = False
            rows[(mode, bucket)].append((ctx.tokens, ctx.ms, pt, rt, pc, rc, ex))
            rows[(mode, "ALL")].append(rows[(mode, bucket)][-1])
    if quiet:
        return rows
    print(f"{'mode':<14}{'bucket':<13}{'n':>3}{'tokens':>8}{'ms':>8}{'tblP':>6}{'tblR':>6}{'colP':>6}{'colR':>6}{'exec':>6}")
    for b in (*BUCKETS, "ALL"):
        for mode in modes:
            if (mode, b) in rows:
                v = rows[(mode, b)]
                ex = [x[6] for x in v if x[6] is not None]
                print(f"{mode:<14}{b:<13}{len(v):>3}" + f"{mean(x[0] for x in v):>8.0f}{mean(x[1] for x in v):>8.0f}"
                      + "".join(f"{mean(x[i] for x in v):>6.2f}" for i in range(2, 6))
                      + (f"{mean(ex):>6.2f}" if ex else f"{'-':>6}"))
    if {"hybrid", "hybrid_pruned"} <= set(modes):
        paired(rows, "hybrid_pruned", "hybrid")
    return rows


def paired(rows, a, b):
    """Per-query paired comparison a vs b over ALL pairs (rows are aligned by pair order)."""
    va, vb = rows[(a, "ALL")], rows[(b, "ALL")]
    print(f"\npaired {a} - {b} (n={len(va)}, mean [95% bootstrap CI])")
    for name, i in (("tokens", 0), ("colP", 4), ("colR", 5)):
        m, lo, hi = bootstrap_ci([x[i] - y[i] for x, y in zip(va, vb)])
        print(f"  d{name:<7}{m:>8.2f} [{lo:.2f}, {hi:.2f}]")
    ok = [(x[6], y[6]) for x, y in zip(va, vb) if x[6] is not None]
    if ok:
        oa, ob = sum(1 for x, y in ok if x and not y), sum(1 for x, y in ok if y and not x)
        print(f"  exec: {a} {mean(x for x, _ in ok):.2f} vs {b} {mean(y for _, y in ok):.2f}; "
              f"only-{a} {oa}, only-{b} {ob}, McNemar exact p={mcnemar_exact(oa, ob):.3f} (n={len(ok)})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db")  # fallback for pairs without their own "db"
    ap.add_argument("--pairs", nargs="+", required=True)
    ap.add_argument("--depth", type=int, default=1)
    ap.add_argument("--threshold", type=float, default=0.6)
    ap.add_argument("--modes", nargs="+", default=list(MODES), choices=MODES)
    ap.add_argument("--labels", action="store_true")
    ap.add_argument("--adaptive", action="store_true")
    ap.add_argument("--anchors", type=int, default=0, help="multi_anchors k")
    ap.add_argument("--min-cols", type=int, default=0, help="leave tables with <= N columns unpruned")
    ap.add_argument("--ungated", action="store_true", help="apply multi-anchor to every question, not only predicted multi-join")
    ap.add_argument("--exec", metavar="MODEL", help="execution accuracy with this Ollama model (e.g. phi3)")
    a = ap.parse_args()
    run(a.db, [p for f in a.pairs for p in json.load(open(f, encoding="utf-8"))], generate=(lambda q, ddl: ollama_generate(q, ddl, a.exec)) if a.exec else None,
        modes=tuple(a.modes), depth=a.depth, threshold=a.threshold, labels=a.labels, adaptive=a.adaptive,
        multi_anchors=a.anchors, gate=not a.ungated, min_cols=a.min_cols)
