"""Demo (Agent 3): Colab check that the single-model weight swap reproduces your saved results.

For the first N evaluation questions it generates with each mode and compares the SQL with the predictions
saved earlier by `evaluate.py generate` (same greedy decoding). Run on Colab, from the project root:

  python -m agent3_finetune.demo.check_engine \
      --lora /content/drive/MyDrive/agent3/runs/lora_r16_seed42/adapter \
      --hydra /content/drive/MyDrive/agent3/runs/hydra_r16_seed42/adapter \
      --inputs /content/drive/MyDrive/agent3/eval_inputs.json \
      --lora-preds agent3_finetune/results/lora/lora_r16_seed42_predictions.json \
      --hydra-preds agent3_finetune/results/hydra/hydra_r16_seed42_predictions_oracle.json \
      --n 20

Expect most questions to match exactly. A few may differ in tiny details because evaluate.py generated 4
questions at a time (padding) and the demo generates one at a time (fp16 rounding): that is not a bug.
Many mismatches (below about 80%) would mean the swap is wrong: do not use the demo, tell me the numbers.
"""
import argparse
import json
from pathlib import Path

from agent3_finetune.evaluate import clean_sql, normalise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lora", required=True)
    ap.add_argument("--hydra", required=True)
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--lora-preds", default="")
    ap.add_argument("--hydra-preds", default="")
    ap.add_argument("--base-preds", default="")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--stride", type=int, default=1, help="take every STRIDE-th question (spreads the check over buckets)")
    a = ap.parse_args()

    from agent3_finetune.demo.engine import Engine

    items = json.loads(Path(a.inputs).read_text(encoding="utf-8"))
    saved = {}
    for mode, path in (("lora", a.lora_preds), ("hydra", a.hydra_preds), ("base", a.base_preds)):
        if path:
            saved[mode] = json.loads(Path(path).read_text(encoding="utf-8"))["predictions"]
    if not saved:
        raise SystemExit("give at least one of --lora-preds, --hydra-preds, --base-preds")

    eng = Engine(a.lora, a.hydra)
    print("device:", eng.gpu, "| model:", eng.model_name)
    same = {m: 0 for m in saved}
    total = {m: 0 for m in saved}
    secs = {m: [] for m in saved}
    shown = 0
    picked = list(range(0, len(items), max(1, a.stride)))[:a.n]  # e.g. --stride 6 spreads over all buckets
    for k, i in enumerate(picked):
        it = items[i]
        # the schema text is stored in eval_inputs.json, so the database files are not needed here
        prompt = eng.template.format(ddl=it["ddl"], question=it["question"])
        for m in saved:
            ref = saved[m][i]["pred"]
            if not ref.strip():
                continue  # was too long in evaluate.py
            raw, s = eng.generate(m, prompt, it.get("complexity"))
            secs[m].append(s)
            ok = normalise(clean_sql(raw)) == normalise(clean_sql(ref))
            same[m] += ok
            total[m] += 1
            if not ok and shown < 5:
                shown += 1
                print(f"\n[{m}] item {i} differs\n  now  : {clean_sql(raw)}\n  saved: {clean_sql(ref)}")
        print(f"{k + 1}/{len(picked)}", flush=True)
    print("\n=== RESULT ===")
    for m in saved:
        avg = sum(secs[m]) / len(secs[m]) if secs[m] else 0
        print(f"{m:6s}: {same[m]}/{total[m]} identical to the saved evaluation output | {avg:.1f} s per question")
    print("peak GPU memory (GB):", eng.peak_vram_gb())


if __name__ == "__main__":
    main()
