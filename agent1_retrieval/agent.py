"""Agent 1 handoff contract (the dict below is what Agent 3 receives, per query; JSON-serialisable)."""
from .complexity import classify_query
from .retrieval import Retriever


class Agent1:
    def __init__(self, db_path, mode="hybrid_pruned", **kw):
        self.mode, self.retriever = mode, Retriever(db_path, **kw)

    def run(self, query):
        c = self.retriever.retrieve(query, self.mode)
        return {
            "query": query,
            # simple | single-join | multi-join | aggregation -> Agent 3 head routing
            "complexity": classify_query(query, self.retriever.classifier_input()),
            "mode": c.mode,
            "anchor": c.anchor,  # table the retrieval started from (None = nothing matched; ddl is then empty)
            "matched": self.retriever.matched(query),  # False = no question word matches the schema -> pipeline should decline
            "tables": c.columns,  # table -> kept column names
            "ddl": c.text,  # pruned schema, ready to paste into the SLM prompt
            "tokens": c.tokens,
            "latency_ms": round(c.ms, 1),
            # explanation for the explorer / logs: why each table is there, why each column was kept or pruned
            "trace": {"roles": c.roles or {}, "reasons": c.reasons or {}},
        }
