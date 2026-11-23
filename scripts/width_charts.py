"""Distraction curves: execution accuracy by width, one line per model size, one panel per complexity bucket.

  python -m scripts.width_charts [--set dev] [--out reports/agent1_width/distraction_curves.png]

Greyscale for print: sizes differ by marker and line style, not colour. Reads results/width/<set>_qwen<size>_fp16.jsonl.
"""
import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SIZES = [("0.5b", "0.5B", "o", ":", "0.55"), ("1.5b", "1.5B", "s", "--", "0.3"), ("3b", "3B", "^", "-", "0.0")]
WIDTHS = ["W1", "W2", "W3", "W4"]
PANELS = ["simple", "single-join", "multi-join", "aggregation", "ALL"]


def curves(rows):  # {bucket: ([acc per width], n)}
    out = {}
    for b in PANELS:
        sel = rows if b == "ALL" else [r for r in rows if r["bucket"] == b]
        out[b] = ([sum(bool(r["ok"][w]) for r in sel) / len(sel) for w in WIDTHS], len(sel))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="dev")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    out = a.out or f"reports/agent1_width/distraction_curves_{a.set}.png"
    data = {}
    for key, *_ in SIZES:
        with open(f"results/width/{a.set}_qwen{key}_fp16.jsonl", encoding="utf-8") as f:
            data[key] = curves([json.loads(l) for l in f])
    fig, axes = plt.subplots(1, len(PANELS), figsize=(13, 3.4), sharey=True)
    for ax, b in zip(axes, PANELS):
        ends = []
        for key, label, marker, style, grey in SIZES:
            acc, n = data[key][b]
            ax.plot(range(4), acc, color=grey, linestyle=style, marker=marker, markersize=6, linewidth=1.6, label=label)
            ends.append([acc[3], label])
        ends.sort()
        for i in range(1, len(ends)):  # push end labels apart so close lines stay readable
            ends[i][0] = max(ends[i][0], ends[i - 1][0] + 0.05)
        for y, label in ends:
            ax.annotate(label, (3.12, y), va="center", fontsize=8)
        ax.set_title(f"{b} (n = {n})", fontsize=10)
        ax.set_xticks(range(4), WIDTHS)
        ax.set_xlim(-0.3, 3.6)
        ax.set_ylim(0, 1)
        ax.grid(axis="y", color="0.88", linewidth=0.8)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("execution accuracy")
    fig.legend(*axes[0].get_legend_handles_labels(), title="Qwen2.5-Instruct FP16", loc="upper center", ncol=3,
               fontsize=8, title_fontsize=8, frameon=False, bbox_to_anchor=(0.5, 1.0))
    fig.supxlabel("schema width (W1 anchor table only ... W4 full schema)", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.savefig(out, dpi=200)
    print(out)


if __name__ == "__main__":
    main()
