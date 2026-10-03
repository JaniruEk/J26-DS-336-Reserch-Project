"""Phase 7 variants of hybrid_pruned vs the hybrid reference (retrieval metrics only; add --exec via evaluate for accuracy)."""
import json
from statistics import mean

from agent1_retrieval.evaluate import run

pairs = [p for f in ("chinook", "spider", "tpch") for p in json.load(open(f"eval/{f}_pairs.json", encoding="utf-8"))]
VARIANTS = {
    "hybrid (ref)": ("hybrid", {}),
    "pruned": ("hybrid_pruned", {}),
    "pruned+labels": ("hybrid_pruned", {"labels": True}),
    "pruned+adaptive": ("hybrid_pruned", {"adaptive": True}),
    "pruned+labels+adaptive": ("hybrid_pruned", {"labels": True, "adaptive": True}),
    "pruned+anchors2": ("hybrid_pruned", {"multi_anchors": 2}),
    "pruned+anchors3": ("hybrid_pruned", {"multi_anchors": 3}),
    "pruned+anchors3+adaptive": ("hybrid_pruned", {"multi_anchors": 3, "adaptive": True}),
}
print(f"{'variant':<24}{'bucket':<13}{'tokens':>7}{'tblR':>6}{'colP':>6}{'colR':>6}")
for name, (mode, kw) in VARIANTS.items():
    rows = run(None, pairs, modes=(mode,), quiet=True, **kw)
    for b in ("multi-join", "ALL"):
        v = rows[(mode, b)]
        print(f"{name:<24}{b:<13}{mean(x[0] for x in v):>7.0f}" + "".join(f"{mean(x[i] for x in v):>6.2f}" for i in (3, 4, 5)))
