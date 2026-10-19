"""Agent 3: the three PRE-REGISTERED routing policies for HydraLoRA (see POLICY_PREREGISTRATION.md).

Offline: needs only the saved *_scored.json files, the evaluation databases (data/...) and Agent 1's classifier file.
No GPU, no retraining. The thresholds below are fixed by the pre-registration; they are constants, not command-line
options, on purpose.

P1 fallback : top classifier probability < TAU  ->  FALLBACK head, else the top head          (1 head run)
P2 retry    : run the top head; if its SQL is not "ok" run the 2nd most probable head          (1 to 2 head runs)
P3 vote     : run all 4 heads; choose the result set returned by most "ok" heads               (4 head runs)
"ok" = the SQL runs without error AND returns at least one row. Policies never look at the gold answer.

Example:
  python -m agent3_finetune.policies --dir agent3_finetune/results/hydra --prefix hydra_r16_seed42 \
      --lora agent3_finetune/results/lora/lora_r16_seed42_predictions_scored.json \
      --out agent3_finetune/results/comparisons/policies.txt
"""
import argparse
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path

import json

HEADS = ("simple", "single-join", "multi-join", "aggregation")  # must match hydra.HEADS
POOLED = ("spider", "chinook")
TAU = 0.5  # pre-registered
FALLBACK = "aggregation"  # pre-registered: the head with the most training data
MODEL_PATH = "agent1_retrieval/complexity_nl.joblib"


def key(r):
    return (r["dataset"], r["db"], r["question"], r["sql"])


def load(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return {key(r): r for r in rows if r["dataset"] in POOLED and r["exec"] is not None}


_cache = {}


def run_sql(db, sql, timeout=10):
    """('error'|'empty'|'ok', signature). Read-only; the signature is the order-free multiset of rows, as in exec_match."""
    if (db, sql) in _cache:
        return _cache[(db, sql)]
    if not sql.strip():
        res = ("error", None)
    else:
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            deadline = time.time() + timeout
            con.set_progress_handler(lambda: time.time() > deadline, 10000)
            try:
                rows = con.execute(sql).fetchall()
            finally:
                con.close()
            res = ("ok", tuple(sorted(map(repr, rows)))) if rows else ("empty", None)
        except Exception:
            res = ("error", None)
    _cache[(db, sql)] = res
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--prefix", default="hydra_r16_seed42")
    ap.add_argument("--lora", required=True)
    ap.add_argument("--model", default=MODEL_PATH)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    d = Path(a.dir)

    import joblib
    from agent1_retrieval.stats import bootstrap_ci, mcnemar_exact

    head = {h: load(d / f"{a.prefix}_predictions_head_{h}_scored.json") for h in HEADS}
    live = load(d / f"{a.prefix}_predictions_nl_scored.json")
    oracle = load(d / f"{a.prefix}_predictions_oracle_scored.json")
    lora = load(a.lora)
    keys = [k for k in live if all(k in head[h] for h in HEADS) and k in oracle and k in lora]
    N = len(keys)
    bucket = {k: live[k]["complexity"] for k in keys}

    clf = joblib.load(a.model)
    classes = list(clf.classes_)
    proba = clf.predict_proba([k[2] for k in keys])
    P = {}
    for k, row in zip(keys, proba):
        P[k] = {h: (float(row[classes.index(h)]) if h in classes else 0.0) for h in HEADS}
    mismatch = sum(1 for k in keys if max(HEADS, key=lambda h: P[k][h]) != live[k].get("nl_complexity"))

    status, sig = {}, {}
    for k in keys:
        for h in HEADS:
            status[(k, h)], sig[(k, h)] = run_sql(k[1], head[h][k].get("pred_clean", ""))

    def ranked(k):
        return sorted(HEADS, key=lambda h: -P[k][h])

    choice, cost = {"P1": {}, "P2": {}, "P3": {}}, {"P1": {}, "P2": {}, "P3": {}}
    for k in keys:
        o = ranked(k)
        top = o[0]
        choice["P1"][k], cost["P1"][k] = (FALLBACK if P[k][top] < TAU else top), 1
        second = o[1]
        if status[(k, top)] != "ok" and status[(k, second)] == "ok":
            choice["P2"][k], cost["P2"][k] = second, 2
        else:
            choice["P2"][k], cost["P2"][k] = top, (1 if status[(k, top)] == "ok" else 2)
        groups = defaultdict(list)
        for h in HEADS:
            if status[(k, h)] == "ok":
                groups[sig[(k, h)]].append(h)
        if groups:
            best = max(groups.values(), key=lambda m: (len(m), max(P[k][h] for h in m)))
            choice["P3"][k] = max(best, key=lambda h: P[k][h])
        else:
            choice["P3"][k] = top
        cost["P3"][k] = 4

    correct = {
        "plain LoRA (single pass)": {k: bool(lora[k]["exec"]) for k in keys},
        "HydraLoRA, live classifier": {k: bool(live[k]["exec"]) for k in keys},
        "HydraLoRA, true label (not deployable)": {k: bool(oracle[k]["exec"]) for k in keys},
        "best fixed head: aggregation": {k: bool(head["aggregation"][k]["exec"]) for k in keys},
        "P1 fallback (tau 0.5, aggregation)": {k: bool(head[choice["P1"][k]][k]["exec"]) for k in keys},
        "P2 retry (second head)": {k: bool(head[choice["P2"][k]][k]["exec"]) for k in keys},
        "P3 vote (4 heads)": {k: bool(head[choice["P3"][k]][k]["exec"]) for k in keys},
        "ceiling: any head correct (not deployable)": {k: any(bool(head[h][k]["exec"]) for h in HEADS) for k in keys},
    }
    mean_cost = {"P1 fallback (tau 0.5, aggregation)": cost["P1"], "P2 retry (second head)": cost["P2"],
                 "P3 vote (4 heads)": cost["P3"]}

    L = []
    out = L.append
    out(f"Pre-registered policies (POLICY_PREREGISTRATION.md). Questions: {N}. Classifier check: its top class equals the saved "
        f"live label for {N - mismatch}/{N} questions" + ("" if mismatch == 0 else "   <-- WARNING: not identical, results are approximate"))
    out("\nEXECUTION ACCURACY (overall and per bucket) and cost (heads run per question)")
    out(f"{'system':<46}{'overall':>16}" + "".join(f"{b:>13}" for b in HEADS) + f"{'cost':>7}")
    for name, c in correct.items():
        cells = []
        for b in HEADS:
            ks = [k for k in keys if bucket[k] == b]
            cells.append(f"{sum(c[k] for k in ks) / len(ks):.2f} ({sum(c[k] for k in ks)}/{len(ks)})" if ks else "n/a")
        mc = f"{sum(mean_cost[name].values()) / N:.2f}x" if name in mean_cost else "1x"
        out(f"{name:<46}{f'{sum(c.values()) / N:.3f} ({sum(c.values())}/{N})':>16}" + "".join(f"{x:>13}" for x in cells) + f"{mc:>7}")

    out("\nPAIRED COMPARISONS, overall execution accuracy (difference A - B, 95% bootstrap CI, A only / B only, exact McNemar p)")
    out("Evidence threshold for the three policies: p < 0.017 (0.05 / 3). Everything is reported either way.")
    for pol in ("P1 fallback (tau 0.5, aggregation)", "P2 retry (second head)", "P3 vote (4 heads)"):
        for ref in ("HydraLoRA, live classifier", "plain LoRA (single pass)"):
            diffs = [int(correct[pol][k]) - int(correct[ref][k]) for k in keys]
            only_a = sum(1 for x in diffs if x > 0)
            only_b = sum(1 for x in diffs if x < 0)
            m, lo, hi = bootstrap_ci(diffs)
            out(f"  {pol[:2]} vs {ref:<28} {m:+.3f} [{lo:+.3f}, {hi:+.3f}]   {only_a} / {only_b}   p = {mcnemar_exact(only_a, only_b):.3f}")

    best_pol = max(("P1 fallback (tau 0.5, aggregation)", "P2 retry (second head)", "P3 vote (4 heads)"),
                   key=lambda n: sum(correct[n].values()))
    beats = sum(correct[best_pol].values()) > sum(correct["plain LoRA (single pass)"].values())
    out("\nREADING GUIDE")
    out(f"  Highest-scoring policy: {best_pol[:2]}. It {'beats' if beats else 'does NOT beat'} single-pass plain LoRA "
        f"({sum(correct[best_pol].values())} vs {sum(correct['plain LoRA (single pass)'].values())} of {N}).")
    out("  Decision rule 2: a policy may be called better than LoRA only if its paired CI against LoRA excludes 0 AND it beats an")
    out("  equal-cost LoRA baseline (P2 costs up to 2x, P3 costs 4x). If no policy beats single-pass LoRA, no extra run is needed.")
    out("  The ceiling row is the most any choice among the four heads could reach.")

    text = "\n".join(L)
    print(text)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text + "\n", encoding="utf-8")
        print("\nwrote", a.out)


if __name__ == "__main__":
    main()
