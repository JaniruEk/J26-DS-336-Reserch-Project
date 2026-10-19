"""Agent 3: what does a routing error cost HydraLoRA? (offline: saved *_scored.json files only, no GPU, no retraining)

Reads the four fixed-head runs (every question answered by ONE head), the live-classifier run, the true-label run
and the plain-LoRA run, and reports:
  1. Cost matrix: accuracy lost when a question of type X is sent to head Y instead of its own head.
  2. The live classifier's confusion matrix and how much each confusion cost in the measured run.
  3. A check that the offline method is trustworthy: the live-classifier accuracy rebuilt from the fixed-head files
     must equal the measured live-classifier accuracy (greedy decoding is deterministic).
  4. Expected accuracy as a function of routing accuracy r (simple model: a wrong route is spread evenly over the three
     wrong heads), the slope (points lost per 10 points of routing accuracy) and whether it ever breaks even with LoRA.
Pooled Spider + Chinook, execution accuracy, same questions everywhere.

Example:
  python -m agent3_finetune.routing_analysis --dir agent3_finetune/results/hydra --prefix hydra_r16_seed42 \
      --lora agent3_finetune/results/lora/lora_r16_seed42_predictions_scored.json \
      --out agent3_finetune/results/comparisons/routing_analysis.txt
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

HEADS = ("simple", "single-join", "multi-join", "aggregation")  # must match hydra.HEADS
POOLED = ("spider", "chinook")
FALLBACK = "single-join"  # what the system does with an unknown label (hydra.DEFAULT_HEAD)


def key(r):
    return (r["dataset"], r["db"], r["question"], r["sql"])


def load(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return {key(r): r for r in rows if r["dataset"] in POOLED and r["exec"] is not None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--prefix", default="hydra_r16_seed42")
    ap.add_argument("--lora", required=True)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    d = Path(a.dir)

    head = {h: load(d / f"{a.prefix}_predictions_head_{h}_scored.json") for h in HEADS}
    live = load(d / f"{a.prefix}_predictions_nl_scored.json")
    oracle = load(d / f"{a.prefix}_predictions_oracle_scored.json")
    lora = load(a.lora)
    keys = [k for k in live if all(k in head[h] for h in HEADS) and k in oracle and k in lora]
    N = len(keys)
    bucket = {k: live[k]["complexity"] for k in keys}
    n_b = Counter(bucket.values())
    share = {b: n_b[b] / N for b in HEADS}

    def acc(b, h):
        return sum(bool(head[h][k]["exec"]) for k in keys if bucket[k] == b) / n_b[b] if n_b[b] else 0.0

    A = {(b, h): acc(b, h) for b in HEADS for h in HEADS}
    L = []
    out = L.append
    out(f"Questions: {N} (pooled Spider + Chinook, execution accuracy). Per bucket: " + ", ".join(f"{b} {n_b[b]}" for b in HEADS))

    # 1. cost matrix
    out("\n1. COST MATRIX: accuracy lost when a question of the row type is answered by the column head (own head = 0)")
    out(f"{'question type':<14}" + "".join(f"{h + ' head':>17}" for h in HEADS) + f"{'own-head acc':>15}")
    for b in HEADS:
        out(f"{b:<14}" + "".join(f"{(A[(b, b)] - A[(b, h)]) * 100:>+16.0f}p" if h != b else f"{'-':>17}" for h in HEADS)
            + f"{A[(b, b)]:>15.2f}")
    out("('p' = percentage points, positive = lost). The more own-head accuracy a type has, the more it can lose.")

    # 2. live classifier confusion
    def routed(k):
        p = live[k].get("nl_complexity")
        return p if p in HEADS else FALLBACK

    conf = Counter((bucket[k], routed(k)) for k in keys)
    r_meas = sum(1 for k in keys if routed(k) == bucket[k]) / N
    out(f"\n2. LIVE CLASSIFIER: routing accuracy {r_meas:.2f} ({sum(1 for k in keys if routed(k) == bucket[k])}/{N}). "
        "Confusion matrix (rows = true type, columns = head chosen):")
    out(f"{'':<14}" + "".join(f"{h:>14}" for h in HEADS))
    for b in HEADS:
        out(f"{b:<14}" + "".join(f"{conf[(b, h)]:>14}" for h in HEADS))
    out("Cost of each confusion in the measured run (questions x accuracy lost, as points of overall accuracy):")
    contrib = []
    for b in HEADS:
        for h in HEADS:
            if h != b and conf[(b, h)]:
                contrib.append((conf[(b, h)] * (A[(b, b)] - A[(b, h)]) / N * 100, b, h, conf[(b, h)]))
    for c, b, h, n in sorted(contrib, reverse=True)[:6]:
        out(f"   {b} -> {h} head: {n} questions, about {c:.1f} points of overall accuracy")
    out("   (fix the largest ones first: that tells the classifier's owner what to improve)")

    # 3. is the offline method trustworthy?
    measured = sum(bool(live[k]["exec"]) for k in keys)
    rebuilt = sum(bool(head[routed(k)][k]["exec"]) for k in keys)
    differ = sum(1 for k in keys if bool(live[k]["exec"]) != bool(head[routed(k)][k]["exec"]))
    out(f"\n3. OFFLINE CHECK: live-classifier accuracy measured {measured}/{N} = {measured / N:.3f}; "
        f"rebuilt from the fixed-head files {rebuilt}/{N} = {rebuilt / N:.3f}; questions that differ: {differ}")
    out("   (equal or nearly equal means that any routing policy can be simulated offline from the four fixed-head files)")

    # 4. expected accuracy against routing accuracy
    t = sum(share[b] * A[(b, b)] for b in HEADS)
    w = sum(share[b] * sum(A[(b, h)] for h in HEADS if h != b) / 3 for b in HEADS)
    lora_acc = sum(bool(lora[k]["exec"]) for k in keys) / N
    oracle_acc = sum(bool(oracle[k]["exec"]) for k in keys) / N
    slope = (t - w) * 10
    out(f"\n4. EXPECTED ACCURACY vs ROUTING ACCURACY r (wrong routes spread evenly over the 3 wrong heads)")
    out(f"   true-label HydraLoRA {oracle_acc:.3f} | plain LoRA {lora_acc:.3f} | all-wrong routing {w:.3f}")
    out(f"   {'r':>6}{'expected accuracy':>20}{'vs LoRA':>12}")
    rows = []
    for r in [0.25 + 0.05 * i for i in range(16)] + [r_meas]:
        e = r * t + (1 - r) * w
        rows.append((r, e))
    for r, e in sorted(rows):
        tag = "  <- measured live classifier" if abs(r - r_meas) < 1e-9 else ""
        out(f"   {r:>6.0%}{e:>20.3f}{(e - lora_acc) * 100:>+11.1f}p{tag}")
    out(f"   Rule of thumb: about {slope:.1f} accuracy points lost for every 10 points of routing accuracy lost.")
    if t <= lora_acc:
        out(f"   No break-even: even perfect routing ({t:.3f}) stays below plain LoRA ({lora_acc:.3f}).")
    else:
        out(f"   Break-even with LoRA at routing accuracy {(lora_acc - w) / (t - w):.0%}.")
    out("   Caveat: real confusions are not spread evenly (see section 2), and each cell rests on about 31 questions.")

    text = "\n".join(L)
    print(text)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text + "\n", encoding="utf-8")
        with open(Path(a.out).with_suffix(".csv"), "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(["routing_accuracy", "expected_accuracy"])
            wr.writerows((round(r, 4), round(e, 4)) for r, e in sorted(rows))
        try:  # optional chart, only if matplotlib is installed
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            xs, ys = zip(*sorted(rows))
            plt.figure(figsize=(6, 4))
            plt.plot(xs, ys, marker="o", label="HydraLoRA (expected)")
            plt.axhline(lora_acc, color="red", linestyle="--", label=f"plain LoRA {lora_acc:.2f}")
            plt.scatter([r_meas], [measured / N], color="black", zorder=5, label="measured live classifier")
            plt.xlabel("routing accuracy")
            plt.ylabel("execution accuracy")
            plt.legend()
            plt.tight_layout()
            plt.savefig(Path(a.out).with_suffix(".png"), dpi=150)
        except ImportError:
            print("\n(matplotlib not installed: no chart; install with `pip install matplotlib` if you want a PNG)")
        print("\nwrote", a.out)


if __name__ == "__main__":
    main()
