"""Width curves across model sizes (hypothesis 1). Test-set sweep files, smallest model first.

  python -m scripts.width_sizes results/width/colab/dev_qwen0.5b_fp16.jsonl ... results/width/colab/dev_qwen7b_fp16.jsonl \
      --h1 results/width/colab/dev_qwen0.5b_fp16.jsonl results/width/colab/dev_qwen7b_fp16.jsonl \
      --same results/width/dev_qwen1.5b_fp16.jsonl results/width/colab/dev_qwen1.5b_fp16.jsonl

Rules fixed in advance: reports/agent1_width/README.md, "Pre-registered rules for model sizes".
D = accuracy(W4) - accuracy(W2). H1 is supported if D(largest) - D(smallest) > 0 with the 95% CI above 0.
"""
import argparse

from agent1_retrieval.width import WIDTHS, accuracy, choose_fixed, distraction, size_effect
from scripts.width_selector import read
from scripts.width_sweep import summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--h1", nargs=2, metavar=("SMALL", "LARGE"))
    ap.add_argument("--same", nargs=2, metavar=("A", "B"), help="two runs of the SAME model (hardware check)")
    a = ap.parse_args()
    data = {f: read(f) for f in a.files}
    shared = set.intersection(*({r["id"] for r in rows} for rows in data.values()))
    print(f"{len(shared)} questions in every file (only these are compared)\n")
    for f, rows in data.items():
        rows = [r for r in rows if r["id"] in shared]
        best = max(WIDTHS, key=lambda w: accuracy(rows, choose_fixed(w)))
        print(f"== {f}: best fixed width {best}, D = {distraction(rows):+.3f}\n{summary(rows)}\n")

    def line(name, e):
        print(f"{name}: n = {e['n']}, D {e['d_small']:+.3f} -> {e['d_large']:+.3f}, "
              f"difference {e['diff']:+.3f} [{e['ci'][0]:+.3f}, {e['ci'][1]:+.3f}]")
    if a.h1:
        small, large = (read(f) for f in a.h1)
        e = size_effect(small, large)
        line("H1 (pre-registered)", e)
        print("H1", "supported" if e["diff"] > 0 and e["ci"][0] > 0 else "not supported")
    if a.same:
        x, y = (read(f) for f in a.same)
        by_id = {r["id"]: r for r in x}
        flags = [(bool(by_id[r["id"]]["ok"][w]), bool(r["ok"][w])) for r in y if r["id"] in by_id for w in WIDTHS]
        print(f"\nsame model, two runs: {sum(p == q for p, q in flags) / len(flags):.3f} of per-width flags agree")
        line("D, second run against first", size_effect(x, y))


if __name__ == "__main__":
    main()
