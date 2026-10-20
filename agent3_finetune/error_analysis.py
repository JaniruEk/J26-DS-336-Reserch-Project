"""Agent 3: why do multi-join questions fail? Error analysis with automatic pre-labelling and a manual check.

Step 1  export     writes a CSV with every WRONG multi-join answer of each model, with an automatic category.
Step 2  (by hand)  open the CSV in Excel, read the rows of your main model (about 27), and where the automatic category
                   is wrong, type the right one into the column 'manual_category'. Leave the rest empty.
Step 3  summarise  counts the categories per model (manual overrides auto), prints a table and, if matplotlib is
                   installed, saves a bar chart. It also says how often your manual check changed the automatic label.

Automatic categories (first match wins):
  truncated or incomplete | unknown column or table | other SQL error | runs but returns no rows |
  missing table(s) | extra table(s) | aggregate / GROUP BY differs | same tables, wrong columns / join key / filter
You may type any category you like by hand, for example 'wrong join key' or 'wrong filter'.

Examples:
  python -m agent3_finetune.error_analysis export --model lora=agent3_finetune/results/lora/lora_r16_seed42_predictions_scored.json \
      --model base=agent3_finetune/results/base_model/base_qwen_predictions_scored.json --out agent3_finetune/results/comparisons/multijoin_errors.csv
  python -m agent3_finetune.error_analysis summarise --csv agent3_finetune/results/comparisons/multijoin_errors.csv \
      --out agent3_finetune/results/comparisons/multijoin_error_summary.txt
"""
import argparse
import csv
import json
import re
import sqlite3
import time
from collections import Counter
from pathlib import Path

POOLED = ("spider", "chinook")
BUCKET = "multi-join"


def tables(sql):
    return {t.lower() for t in re.findall(r"\b(?:from|join)\s+([A-Za-z_][\w]*)", sql, flags=re.I)}


def has_agg(sql):
    return bool(re.search(r"\b(count|sum|avg|min|max)\s*\(", sql, flags=re.I))


def has_group(sql):
    return bool(re.search(r"\bgroup\s+by\b", sql, flags=re.I))


def truncated(sql):
    s = sql.strip()
    return (not s) or s.count("(") != s.count(")") or bool(re.search(r"(\b(and|or|on|where|join|from|select|by|having)|,|=)\s*$", s, flags=re.I))


def try_run(db, sql, timeout=10):
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        deadline = time.time() + timeout
        con.set_progress_handler(lambda: time.time() > deadline, 10000)
        try:
            rows = con.execute(sql).fetchall()
        finally:
            con.close()
        return ("ok" if rows else "empty"), ""
    except Exception as e:
        return "error", str(e)


def auto_category(pred, gold, db):
    if truncated(pred):
        return "truncated or incomplete", ""
    status, msg = try_run(db, pred)
    if status == "error":
        low = msg.lower()
        return ("unknown column or table" if ("no such column" in low or "no such table" in low) else "other SQL error"), msg
    if status == "empty":
        return "runs but returns no rows", ""
    tp, tg = tables(pred), tables(gold)
    if tg - tp:
        return "missing table(s)", ""
    if tp - tg:
        return "extra table(s)", ""
    if has_agg(pred) != has_agg(gold) or has_group(pred) != has_group(gold):
        return "aggregate / GROUP BY differs", ""
    return "same tables, wrong columns / join key / filter", ""


def cmd_export(a):
    out_rows = []
    for spec in a.model:
        name, path = spec.split("=", 1)
        rows = json.loads(Path(path).read_text(encoding="utf-8"))
        wrong = [r for r in rows if r["dataset"] in POOLED and r["complexity"] == BUCKET and r["exec"] is False]
        for i, r in enumerate(wrong[:a.max]):
            pred = r.get("pred_clean", r.get("pred", ""))
            cat, msg = auto_category(pred, r["sql"], r["db"])
            out_rows.append({"model": name, "id": i + 1, "question": r["question"], "gold_sql": r["sql"], "pred_sql": pred,
                             "db": r["db"], "auto_category": cat, "error_message": msg, "manual_category": "", "notes": ""})
        print(f"{name}: {len(wrong)} wrong multi-join answers ({min(len(wrong), a.max)} exported)")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig so Excel opens it correctly
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    print("wrote", a.out, "- open it in Excel, check the rows of your main model, fill 'manual_category' where the auto label is wrong")


def cmd_summarise(a):
    with open(a.csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    models = list(dict.fromkeys(r["model"] for r in rows))
    cats = Counter()
    per = {m: Counter() for m in models}
    changed = {m: 0 for m in models}
    checked = {m: 0 for m in models}
    for r in rows:
        manual = (r["manual_category"] or "").strip()
        cat = manual or r["auto_category"]
        per[r["model"]][cat] += 1
        cats[cat] += 1
        if manual:
            checked[r["model"]] += 1
            changed[r["model"]] += manual != r["auto_category"]
    order = [c for c, _ in cats.most_common()]
    lines = [f"Wrong multi-join answers by category (manual label if given, otherwise automatic)", ""]
    lines.append(f"{'category':<48}" + "".join(f"{m:>12}" for m in models))
    for c in order:
        lines.append(f"{c:<48}" + "".join(f"{per[m][c]:>12}" for m in models))
    lines.append(f"{'TOTAL wrong answers':<48}" + "".join(f"{sum(per[m].values()):>12}" for m in models))
    lines.append("")
    for m in models:
        lines.append(f"{m}: {checked[m]} rows had a manual label; {changed[m]} of them differ from the automatic label"
                     + ("" if checked[m] else "  (nothing checked by hand yet: automatic labels only)"))
    lines.append("Labels typed by hand are your own judgement; say in the thesis which rows you checked and which you did not.")
    text = "\n".join(lines)
    print(text)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8")
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            width = 0.8 / max(1, len(models))
            plt.figure(figsize=(9, 4.5))
            for j, m in enumerate(models):
                plt.bar([i + j * width for i in range(len(order))], [per[m][c] for c in order], width, label=m)
            plt.xticks([i + width * (len(models) - 1) / 2 for i in range(len(order))], order, rotation=30, ha="right", fontsize=8)
            plt.ylabel("wrong multi-join answers")
            plt.legend()
            plt.tight_layout()
            plt.savefig(Path(a.out).with_suffix(".png"), dpi=150)
            print("chart:", Path(a.out).with_suffix(".png"))
        except ImportError:
            print("(matplotlib not installed: no chart. `pip install matplotlib` if you want one)")
        print("wrote", a.out)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--model", action="append", required=True, help="name=path/to/scored.json (repeat; first = main model)")
    e.add_argument("--out", required=True)
    e.add_argument("--max", type=int, default=40)
    e.set_defaults(fn=cmd_export)
    s = sub.add_parser("summarise")
    s.add_argument("--csv", required=True)
    s.add_argument("--out", default="")
    s.set_defaults(fn=cmd_summarise)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
