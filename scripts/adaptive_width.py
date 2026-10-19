"""Complexity-adaptive context width: anchor table only when the classifier is >= tau sure the question is simple,
else the RECOMMENDED wide pruned context. Execution accuracy vs the always-wide baseline, paired per question.
Usage: python -m scripts.adaptive_width [model]   (default phi3; generations cached in data/gen_cache.json)"""
import json
import sys
from statistics import mean

from agent1_retrieval import RECOMMENDED
from agent1_retrieval.complexity import BUCKETS
from agent1_retrieval.evaluate import run
from agent1_retrieval.execution import ollama_generate
from agent1_retrieval.stats import mcnemar_exact

model = sys.argv[1] if len(sys.argv) > 1 else "phi3"
pairs = [p for f in ("chinook", "spider") for p in json.load(open(f"eval/{f}_pairs.json", encoding="utf-8"))]
gen = lambda q, ddl, **kw: ollama_generate(q, ddl, model, **kw)
VARIANTS = {"always wide (baseline)": {}, **{f"adaptive tau={t}": {"narrow_simple": t} for t in (0.5, 0.6, 0.7)},
            **{f"adaptive tau={t} schema classifier": {"narrow_simple": t, "schema_classifier": True} for t in (0.5, 0.6)},
            "adaptive oracle (gold label)": {"narrow_simple": 0.5, "oracle": True}}

results = {name: run(None, pairs, modes=("hybrid_pruned",), quiet=True, generate=gen, **RECOMMENDED, **kw)
           for name, kw in VARIANTS.items()}
base = results["always wide (baseline)"]
print(f"model {model}, n={len(pairs)}; exec accuracy per bucket, mean tokens, paired vs baseline (McNemar exact)")
print(f"{'variant':<36}" + "".join(f"{b:>13}" for b in (*BUCKETS, "ALL")) + f"{'tokens':>8}{'+/-':>9}{'p':>7}")
for name, rows in results.items():
    acc = lambda b: mean(x[6] for x in rows[("hybrid_pruned", b)] if x[6] is not None)
    ok = [(x[6], y[6]) for x, y in zip(rows[("hybrid_pruned", "ALL")], base[("hybrid_pruned", "ALL")]) if x[6] is not None]
    win, loss = sum(a and not b for a, b in ok), sum(b and not a for a, b in ok)
    print(f"{name:<36}" + "".join(f"{acc(b):>13.2f}" for b in (*BUCKETS, "ALL"))
          + f"{mean(x[0] for x in rows[('hybrid_pruned', 'ALL')]):>8.0f}{f'{win}/{loss}':>9}{mcnemar_exact(win, loss):>7.3f}")
