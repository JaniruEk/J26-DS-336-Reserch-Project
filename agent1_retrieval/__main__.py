"""python -m agent1_retrieval "question" --db data/chinook.db --mode hybrid_pruned [--json]"""
import argparse
import json

from .agent import Agent1
from .retrieval import MODES

ap = argparse.ArgumentParser()
ap.add_argument("query")
ap.add_argument("--db", default="data/chinook.db")
ap.add_argument("--mode", default="hybrid_pruned", choices=MODES)
ap.add_argument("--json", action="store_true", help="print the full Agent 3 handoff payload")
a = ap.parse_args()
out = Agent1(a.db, a.mode).run(a.query)
print(json.dumps(out, indent=2) if a.json else f"-- {out['complexity']} anchor={out['anchor']} tokens={out['tokens']} ms={out['latency_ms']}\n{out['ddl']}")
