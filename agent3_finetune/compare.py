"""Agent 3: paired comparison of two scored runs (A vs B) on the same evaluation questions.

Input: two *_predictions_scored.json files written by `evaluate.py score`.
For every complexity bucket (pooled Spider + Chinook by default) it reports accuracy of A and B, the paired
difference A - B with a 95% bootstrap CI, how many questions only A / only B got right, and the exact McNemar p-value.
Uses the shared agent1_retrieval.stats helpers so results are comparable across agents.

Example:
  python -m agent3_finetune.compare --a agent3_finetune/results/lora_seed42_predictions_scored.json \\
      --b agent3_finetune/results/base_qwen_predictions_scored.json
Later the same command compares LoRA with HydraLoRA.
"""
import argparse
import json
import re
from pathlib import Path


def load(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return {(r["dataset"], r["db"], r["question"], r["sql"]): r for r in rows}


def default_name(path):
    return re.sub(r"_predictions_scored$", "", Path(path).stem)


def main():
    from agent1_retrieval.complexity import BUCKETS
    from agent1_retrieval.stats import bootstrap_ci, mcnemar_exact

    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--name_a", default="")
    ap.add_argument("--name_b", default="")
    ap.add_argument("--datasets", nargs="+", default=["spider", "chinook"])
    ap.add_argument("--out", default="", help="optional text file to save the report")
    a = ap.parse_args()

    name_a, name_b = a.name_a or default_name(a.a), a.name_b or default_name(a.b)
    A, B = load(a.a), load(a.b)
    keys = [k for k in A if k in B and k[0] in a.datasets]
    missing = sum(1 for k in A if k[0] in a.datasets and k not in B)
    lines = [f"A = {name_a}   B = {name_b}   datasets: {', '.join(a.datasets)}   paired questions: {len(keys)}"
             + (f"   (WARNING: {missing} questions of A not found in B)" if missing else "")]

    for metric in ("exec", "exact"):
        lines += ["", f"=== {metric} ({'execution accuracy' if metric == 'exec' else 'normalised exact match'}) ===",
                  f"{'bucket':<13}{'n':>4}  {name_a[:14]:>14} {name_b[:14]:>14}   {'diff A-B [95% CI]':<24}{'only A / only B':<17}McNemar p"]
        for bucket in list(BUCKETS) + ["ALL"]:
            va, vb = [], []
            for k in keys:
                ra, rb = A[k], B[k]
                if bucket != "ALL" and ra["complexity"] != bucket:
                    continue
                if metric == "exec" and (ra["exec"] is None or rb["exec"] is None):
                    continue  # gold query returns no rows: not scorable
                va.append(int(bool(ra[metric])))
                vb.append(int(bool(rb[metric])))
            n = len(va)
            if n == 0:
                continue
            only_a = sum(1 for x, y in zip(va, vb) if x and not y)
            only_b = sum(1 for x, y in zip(va, vb) if y and not x)
            d, lo, hi = bootstrap_ci([x - y for x, y in zip(va, vb)])
            lines.append(f"{bucket:<13}{n:>4}  {sum(va) / n:>14.2f} {sum(vb) / n:>14.2f}   "
                         f"{d:+.2f} [{lo:+.2f}, {hi:+.2f}]".ljust(13 + 4 + 2 + 29 + 24 + 2)
                         + f"{only_a} / {only_b}".ljust(17) + f"{mcnemar_exact(only_a, only_b):.3f}")

    lines += ["", "Note: 5 buckets are tested per metric, so a single p just under 0.05 is weak evidence;",
              "state effect sizes with their CIs rather than relying on p-values alone."]
    text = "\n".join(lines)
    print(text)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8")
        print("\nwrote", a.out)


if __name__ == "__main__":
    main()
