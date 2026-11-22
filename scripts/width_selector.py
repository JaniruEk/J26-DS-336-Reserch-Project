"""Train and test the width selector on the rows of scripts/width_sweep.py.

  python -m scripts.width_selector results/width/qwen2.5_1.5b-instruct.jsonl
  python -m scripts.width_selector <train rows> --test <test rows> --save agent1_retrieval/width_selector.joblib

One file: 5-fold test where every question is predicted by a selector that never saw its database.
With --test: train on the first file, test on the second (for example Spider train -> Spider dev).
Compared: fixed W1..W4, the complexity rule (the app today), the adaptive elbow (if swept), the learned selector,
the same selector with complexity features only (Adaptive-RAG-style ablation), retry with the next wider width
(if the rows have "runs"; tokens count every width tried), and the oracle (upper limit).
"""
import argparse
import json
from pathlib import Path
from statistics import mean

from agent1_retrieval.complexity import BUCKETS
from agent1_retrieval.width import (COMPLEXITY_ONLY, FEATURES, WIDTHS, accuracy, choose_elbow, choose_fixed,
                                    choose_oracle, choose_rule, compare, cross_fit, label, retry_path)


def make_model():
    from sklearn.ensemble import GradientBoostingClassifier
    return GradientBoostingClassifier(n_estimators=150, max_depth=3, learning_rate=0.05, subsample=0.8, random_state=0)


def read(path):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rows")
    ap.add_argument("--test")
    ap.add_argument("--save", help="write the selector trained on all rows of the first file (joblib)")
    a = ap.parse_args()
    train = read(a.rows)
    rows = read(a.test) if a.test else train
    labelled = [r for r in train if label(r)]

    def pick(feats):
        """{row id: width} for the test rows, from a selector that uses only `feats`."""
        if not a.test:
            return cross_fit(rows, make_model, features=feats)
        x = lambda r: [r["features"][f] for f in feats]
        model = make_model().fit([x(r) for r in labelled], [label(r) for r in labelled])
        return {r["id"]: str(w) for r, w in zip(rows, model.predict([x(r) for r in rows]))}

    picked, picked_c = pick(FEATURES), pick(COMPLEXITY_ONLY)
    selector = lambda r: picked[r["id"]]
    complexity_only = lambda r: picked_c[r["id"]]
    systems = {**{f"fixed {w}": choose_fixed(w) for w in WIDTHS}, "complexity rule": choose_rule(),
               **({"adaptive elbow": choose_elbow} if all("E" in r["ok"] for r in rows) else {}),
               "learned selector": selector, "learned, cplx only": complexity_only}
    cost = {}  # systems whose tokens are not just the final width's
    if all("runs" in r for r in rows):
        for name, first in (("W2 + retry wider", choose_fixed("W2")), ("selector + retry", selector)):
            systems[name] = lambda r, f=first: retry_path(r, f(r))[-1]
            cost[name] = lambda r, f=first: sum(r["tokens"][w] for w in retry_path(r, f(r)))
    systems["oracle (limit)"] = choose_oracle
    best_fixed = max(WIDTHS, key=lambda w: accuracy(rows, choose_fixed(w)))

    counts = {w: sum(label(r) == w for r in train) for w in WIDTHS}
    print(f"training labels (narrowest correct width): {counts}, no correct width: {sum(label(r) is None for r in train)}")
    print(f"\n{len(rows)} test questions. Execution accuracy, mean prompt tokens, and each system against the best "
          f"fixed width ({best_fixed}):")
    print(f"{'system':<18}" + "".join(f"{b:>13}" for b in (*BUCKETS, "ALL")) + f"{'tokens':>8}{'diff':>8}{'95% CI':>18}{'+/-':>8}{'p':>7}")
    for name, ch in systems.items():
        groups = [[r for r in rows if b in (r["bucket"], "ALL")] for b in (*BUCKETS, "ALL")]
        acc = "".join(f"{accuracy(v, ch):>13.2f}" if v else " " * 12 + "-" for v in groups)
        c = compare(rows, ch, choose_fixed(best_fixed))
        wl = f"{c['wins']}/{c['losses']}"
        ci = "[{:+.3f}, {:+.3f}]".format(*c["ci"])
        tok = mean(cost[name](r) if name in cost else r["tokens"][ch(r)] for r in rows)
        print(f"{name:<18}{acc}{tok:>8.0f}{c['diff']:>+8.3f}{ci:>18}{wl:>8}{c['p']:>7.3f}")
    for other, ch in (("the complexity rule", choose_rule()), ("the complexity-only selector", complexity_only)):
        c = compare(rows, selector, ch)
        print(f"\nlearned selector against {other}: {c['diff']:+.3f} [{c['ci'][0]:+.3f}, {c['ci'][1]:+.3f}], "
              f"{c['wins']}/{c['losses']}, McNemar p = {c['p']:.3f}")
    print("widths the selector picked:", {w: sum(picked[r["id"]] == w for r in rows) for w in WIDTHS})
    print("Hypothesis 3 (fixed in advance): the learned selector beats every fixed width and the complexity rule at "
          "p < 0.0125 (0.05 / 4). The other rows (elbow, complexity only, retry) are secondary.")
    if cost:
        print("Retry rows are an offline approximation: the retry sees a wider schema but no error hint.")
    if a.save:
        import joblib
        x = lambda r: [r["features"][f] for f in FEATURES]
        joblib.dump({"model": make_model().fit([x(r) for r in labelled], [label(r) for r in labelled]),
                     "features": FEATURES, "trained_on": a.rows, "n": len(labelled)}, a.save)
        print("saved", a.save)


if __name__ == "__main__":
    main()
