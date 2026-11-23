"""Agent 1 latency with and without the width selector (queue step 8): warm, LIVE config, 148 routing questions.

  python -m scripts.width_latency
"""
import json, time, statistics as st
from collections import defaultdict
from agent1_retrieval import LIVE, Agent1
pairs = [p for f in ("eval/chinook_pairs.json", "eval/spider_pairs.json", "eval/tpch_pairs.json") for p in json.load(open(f))]
by = defaultdict(list)
for p in pairs: by[p["db"]].append(p["question"])
sel_ms, run_ms, base_ms = [], [], []
for db, qs in by.items():
    a = Agent1(db, width_selector="agent1_retrieval/width_selector.joblib", **LIVE)
    b = Agent1(db, **LIVE)
    a.run(qs[0]); b.run(qs[0])  # warm-up
    for q in qs:
        t = time.perf_counter(); out = a.run(q); run_ms.append((time.perf_counter() - t) * 1000); sel_ms.append(out["latency_ms"])
        t = time.perf_counter(); b.run(q); base_ms.append((time.perf_counter() - t) * 1000)
p95 = lambda x: sorted(x)[int(0.95 * len(x)) - 1]
for name, x in (("selector: selection only (latency_ms)", sel_ms), ("selector: whole Agent1.run", run_ms), ("no selector: whole Agent1.run", base_ms)):
    print(f"{name:40s} n={len(x)} median {st.median(x):.0f} ms  p95 {p95(x):.0f}  max {max(x):.0f}")
