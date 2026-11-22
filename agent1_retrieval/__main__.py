"""python -m agent1_retrieval "question" --db data/chinook.db --mode hybrid_pruned [--json]"""
import argparse
import json

from .agent import Agent1
from .retrieval import LIVE, MODES, RECOMMENDED

ap = argparse.ArgumentParser()
ap.add_argument("query")
ap.add_argument("--db", default="data/chinook.db")
ap.add_argument("--mode", default="hybrid_pruned", choices=MODES)
ap.add_argument("--json", action="store_true", help="print the full Agent 3 handoff payload")
config_group = ap.add_mutually_exclusive_group()
config_group.add_argument("--plain", action="store_true",
                          help="original Phase 1-7 settings instead of the recommended PP1 config")
config_group.add_argument("--live", action="store_true",
                          help="the application configuration, including value hints and schema-aware routing")
ap.add_argument("--infer-fks", action="store_true", help="infer FKs from column names when the schema declares none")
ap.add_argument("--schema-classifier", action="store_true",
                help="use the schema-aware complexity classifier for the handoff label")
ap.add_argument("--narrow-simple", type=float, metavar="TAU",
                help="send only the anchor table when P(simple) >= TAU")
ap.add_argument("--value-hints", action="store_true",
                help="show low-cardinality code values in the schema")
ap.add_argument("--glossary", help="JSON file with Table.Column meanings to add to the schema")
a = ap.parse_args()
config = {} if a.plain else dict(LIVE if a.live else RECOMMENDED)
if a.schema_classifier:
    config["schema_classifier"] = True
if a.narrow_simple is not None:
    if not 0 <= a.narrow_simple <= 1:
        ap.error("--narrow-simple must be between 0 and 1")
    config["narrow_simple"] = a.narrow_simple
if a.value_hints:
    config["value_hints"] = True
if a.glossary:
    config["glossary"] = a.glossary
out = Agent1(a.db, a.mode, **config, infer_missing_fks=a.infer_fks).run(a.query)
print(json.dumps(out, indent=2) if a.json else f"-- {out['complexity']} anchor={out['anchor']} tokens={out['tokens']} ms={out['latency_ms']}\n{out['ddl']}")
