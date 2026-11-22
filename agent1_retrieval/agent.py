"""Agent 1 handoff contract (the dict below is what Agent 3 receives, per query; JSON-serialisable)."""
import time
from dataclasses import replace

from .complexity import classify_query
from .retrieval import Retriever


class Agent1:
    def __init__(self, db_path, mode="hybrid_pruned", width_selector=None, **kw):
        """width_selector: a file made by scripts/width_selector.py --save. With it (and mode hybrid_pruned) the
        selector decides how much schema each question gets (W1..W4, agent1_retrieval/width.py). None = as before."""
        self.mode, self.retriever = mode, Retriever(db_path, **kw)
        self.selector = None
        if width_selector and mode == "hybrid_pruned":
            import joblib
            self.selector = joblib.load(width_selector)  # our own file (joblib = pickle: never load an untrusted one)

    def _select(self, query, width):
        """(Context, width). width given = that width (the retry asks for a wider one); else the selector decides."""
        from .width import WIDTHS, features, width_context
        if width:
            return width_context(self.retriever, query, width), width
        ctx = {w: width_context(self.retriever, query, w) for w in WIDTHS}
        f = features(self.retriever, query, ctx)
        w = str(self.selector["model"].predict([[f[k] for k in self.selector["features"]]])[0])
        return ctx[w], w

    def wider(self, width):
        """The next wider width, or None at the widest (or when no selector is in use)."""
        from .width import WIDTHS
        i = WIDTHS.index(width) if width in WIDTHS else len(WIDTHS)
        return WIDTHS[i + 1] if self.selector and i + 1 < len(WIDTHS) else None

    def run(self, query, width=None):
        t0 = time.perf_counter()
        c, w = self._select(query, width) if self.selector else (self.retriever.retrieve(query, self.mode), None)
        if w:  # the time of the whole selection (all four contexts + features), not of one context
            c = replace(c, ms=(time.perf_counter() - t0) * 1000)
        return {
            "query": query,
            # simple | single-join | multi-join | aggregation -> Agent 3 head routing
            "complexity": classify_query(query, self.retriever.classifier_input()),
            "mode": c.mode,
            "width": w,  # W1..W4 when the width selector is in use, else None
            "anchor": c.anchor,  # table the retrieval started from (None = nothing matched; ddl is then empty)
            "matched": self.retriever.matched(query),  # False = no question word matches the schema -> pipeline should decline
            "tables": c.columns,  # table -> kept column names
            "ddl": c.text,  # pruned schema, ready to paste into the SLM prompt
            "tokens": c.tokens,
            "latency_ms": round(c.ms, 1),
            # explanation for the explorer / logs: why each table is there, why each column was kept or pruned
            "trace": {"roles": c.roles or {}, "reasons": c.reasons or {}},
        }
