"""Demo (Agent 3): find REAL examples where sending a question to the wrong head makes the answer fail.

Uses your saved, scored results (no GPU, no model): for each evaluation question on a demo database it looks for
  - the true-label (oracle) HydraLoRA answer was CORRECT, and
  - one or more other heads (the fixed-head runs) were WRONG on the same question.
Those are the questions to use for the "wrong label on purpose" demonstration.

Run from the project root on the laptop (venv):
  python -m agent3_finetune.demo.find_wrong_head_examples
It finds the scored files in agent3_finetune/results/hydra by name and prints which file it used for each head,
so check that list. Options: --dir, --dbs (comma list of database names), --top.

In the live app: choose that database, type the question, set Complexity label = Manual, and try the true label
(the answer should be right) and then a wrong label (the answer should fail). Greedy decoding gave identical
output in the Colab check, but confirm it live before you rely on it.
"""
import argparse
import json
from pathlib import Path

HEADS = ("simple", "single-join", "multi-join", "aggregation")
DEFAULT_DBS = "chinook,car_1,world_1,concert_singer"


def norm(name):
    return name.lower().replace("_", "-")


def discover(folder):
    """Return (oracle_path, {head: path}). Raises SystemExit with a clear message if it is not unambiguous."""
    files = sorted(p for p in Path(folder).glob("*scored.json"))
    oracle = [p for p in files if "oracle" in norm(p.stem)]
    if len(oracle) != 1:
        raise SystemExit(f"expected exactly one scored 'oracle' file in {folder}, found: {[p.name for p in oracle]}")
    fixed = {}
    for h in HEADS:
        hits = [p for p in files if h in norm(p.stem) and "oracle" not in norm(p.stem) and "-nl-" not in norm(p.stem)]
        if len(hits) != 1:
            raise SystemExit(f"expected exactly one scored file for head '{h}' in {folder}, found: {[p.name for p in hits]}"
                             "\nTell me the file names and I will give you the exact command.")
        fixed[h] = hits[0]
    return oracle[0], fixed


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_examples(oracle_rows, fixed_rows, dbs):
    """List of dicts, best first. fixed_rows: {head: rows}. All files must list the same questions in the same order."""
    for h, rows in fixed_rows.items():
        if len(rows) != len(oracle_rows) or any(a["question"] != b["question"] for a, b in zip(rows, oracle_rows)):
            raise SystemExit(f"the '{h}' file does not list the same questions as the oracle file")
    found = []
    for i, row in enumerate(oracle_rows):
        if Path(row["db"]).stem not in dbs or row.get("exec") is not True and row.get("exec") != 1:
            continue
        true = row["complexity"]
        bad = {h: fixed_rows[h][i] for h in HEADS
               if h != true and fixed_rows[h][i].get("exec") is not None and not fixed_rows[h][i]["exec"]}
        if bad:
            found.append({"db": Path(row["db"]).stem, "question": row["question"], "true_label": true,
                          "right_sql": row.get("pred_clean", row.get("pred", "")),
                          "wrong": {h: r.get("pred_clean", r.get("pred", "")) for h, r in bad.items()}})
    found.sort(key=lambda e: (-len(e["wrong"]), e["db"]))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="agent3_finetune/results/hydra")
    ap.add_argument("--dbs", default=DEFAULT_DBS)
    ap.add_argument("--top", type=int, default=8)
    a = ap.parse_args()
    oracle, fixed = discover(a.dir)
    print("oracle file :", oracle.name)
    for h in HEADS:
        print(f"{h:12s}:", fixed[h].name)
    found = find_examples(load(oracle), {h: load(p) for h, p in fixed.items()}, set(a.dbs.split(",")))
    print(f"\n{len(found)} question(s) on {a.dbs} where the true head is right and another head is wrong\n")
    for e in found[:a.top]:
        print(f"[{e['db']}] true label: {e['true_label']}\n  Q: {e['question']}\n  right ({e['true_label']} head): {e['right_sql']}")
        for h, s in e["wrong"].items():
            print(f"  WRONG ({h} head): {s}")
        print()


if __name__ == "__main__":
    main()
