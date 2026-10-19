"""Agent 3: does each HydraLoRA head specialise? Table of execution accuracy.

Rows    = true complexity bucket of the question
Columns = the head that answered ALL questions (fixed-head runs), plus true-label routing, live-classifier routing
          and (optionally) plain LoRA for reference.
A '*' marks the best fixed head in each row. If the heads specialised, the best head would sit on the diagonal
(simple question -> simple head, ...). Pooled Spider + Chinook, execution accuracy, same questions in every column.
Needs only the *_scored.json files written by `evaluate.py score`. No GPU and no repo imports.

Example:
  python -m agent3_finetune.head_matrix --dir agent3_finetune/results/hydra --prefix hydra_r16_seed42 \
      --lora agent3_finetune/results/lora/lora_r16_seed42_predictions_scored.json \
      --out agent3_finetune/results/comparisons/head_matrix.txt
"""
import argparse
import json
from pathlib import Path

HEADS = ("simple", "single-join", "multi-join", "aggregation")  # must match hydra.HEADS
POOLED = ("spider", "chinook")


def load(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return [r for r in rows if r["dataset"] in POOLED and r["exec"] is not None]


def cell(rows, bucket):
    sub = [r for r in rows if bucket == "ALL" or r["complexity"] == bucket]
    k = sum(bool(r["exec"]) for r in sub)
    return k, len(sub)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="folder with the HydraLoRA *_scored.json files")
    ap.add_argument("--prefix", default="hydra_r16_seed42")
    ap.add_argument("--lora", default="", help="optional scored file of the plain LoRA run, for reference")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    d = Path(a.dir)
    cols = []  # (title, rows, is_fixed_head)
    for h in HEADS:
        cols.append((f"{h} head", load(d / f"{a.prefix}_predictions_head_{h}_scored.json"), True))
    for title, name in (("true label", "oracle"), ("live classifier", "nl")):
        path = d / f"{a.prefix}_predictions_{name}_scored.json"
        if path.exists():
            cols.append((title, load(path), False))
    if a.lora:
        cols.append(("plain LoRA", load(a.lora), False))

    lines = ["Execution accuracy (pooled Spider + Chinook). Rows: true question bucket. "
             "Columns: head used for ALL questions; '*' = best fixed head in the row.", ""]
    head = f"{'question bucket':<16}" + "".join(f"{t:>19}" for t, _, _ in cols)
    lines.append(head)
    for bucket in list(HEADS) + ["ALL"]:
        fixed = [cell(r, bucket) for _, r, is_fixed in cols if is_fixed]
        best = max(k / n if n else 0 for k, n in fixed)
        row = f"{bucket:<16}"
        for _, r, is_fixed in cols:
            k, n = cell(r, bucket)
            mark = "*" if is_fixed and n and bucket != "ALL" and abs(k / n - best) < 1e-9 else " "
            row += f"{(f'{k / n:.2f} ({k}/{n})' if n else 'n/a') + mark:>19}"
        lines.append(row)
    lines += ["", "Reading: with about 30 questions per row, one answer moves a cell by about 3 points; only large",
              "differences between heads mean anything. Diagonal best (simple row -> simple head, ...) = specialised."]
    text = "\n".join(lines)
    print(text)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text + "\n", encoding="utf-8")
        print("\nwrote", a.out)


if __name__ == "__main__":
    main()
