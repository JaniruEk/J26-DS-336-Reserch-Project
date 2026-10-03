"""Agent 1: four switchable retrieval modes built from three sub-agents
(anchor selection -> FK traversal -> column pruning)."""
import hashlib
import tempfile
import time
from dataclasses import dataclass
from functools import lru_cache

from .complexity import classify_query
from .pruning import keep_columns, lemma, query_terms, split_ident
from .schema import adjacency, reflect, render

MODES = ("semantic", "structural", "hybrid", "hybrid_pruned")


@dataclass
class Context:
    mode: str
    anchor: str | None
    columns: dict  # table -> kept column names
    text: str
    tokens: int
    ms: float


@lru_cache(maxsize=1)
def _enc():
    import tiktoken
    return tiktoken.get_encoding("cl100k_base")  # ponytail: proxy tokenizer, swap for the SLM's own once Agent 2 picks the base model


class Retriever:
    def __init__(self, db_path, depth=1, threshold=0.6, labels=False, adaptive=False, multi_anchors=0, gate=True, min_cols=0, chroma_path=None):
        # adaptive: +1 FK hop for questions predicted multi-join. multi_anchors=k: for those questions also take the top-k
        # semantic tables and connect them to the main anchor along shortest FK paths (bridge tables included).
        self.db_path, self.depth, self.threshold, self.labels, self.adaptive = db_path, depth, threshold, labels, adaptive
        self.multi_anchors, self.gate, self.min_cols, self.chroma_path = multi_anchors, gate, min_cols, chroma_path
        self.tables = reflect(db_path)
        self.adj = adjacency(self.tables)
        self._col = None  # vector index is built lazily so structural mode needs no embeddings

    # --- sub-agent 1: anchor selection ---
    def _index(self):
        if self._col is None:
            import chromadb
            # own on-disk client per Retriever: the shared in-process EphemeralClient intermittently returned no results across many collections
            client = chromadb.PersistentClient(self.chroma_path or tempfile.mkdtemp())
            self._col = client.get_or_create_collection("schema_" + hashlib.md5(self.db_path.encode()).hexdigest()[:12])
            if self._col.count() != len(self.tables):
                self._col.upsert(ids=list(self.tables), documents=[render(t) for t in self.tables.values()])
        return self._col

    def _semantic_anchors(self, query, k=1):
        return self._index().query(query_texts=[query], n_results=min(k, len(self.tables)))["ids"][0]

    def _semantic_anchor(self, query):
        ids = self._semantic_anchors(query)
        return ids[0] if ids else None

    def _path(self, a, b):
        """Shortest FK path a..b (inclusive); [b] if disconnected (missing FKs must not fail retrieval)."""
        prev, queue = {a: None}, [a]
        for n in queue:
            for m in sorted(self.adj[n]):
                if m not in prev:
                    prev[m] = n
                    queue.append(m)
        if b not in prev:
            return [b]
        path = []
        while b is not None:
            path.append(b)
            b = prev[b]
        return path[::-1]

    def _structural_anchor(self, query):
        qlem = {t.lemma_.lower() for t in query_terms(query)}
        def score(t):  # table-name match outweighs column-name match
            return (2 * sum(lemma(w) in qlem for w in split_ident(t.name))
                    + sum(lemma(w) in qlem for c, _, _ in t.columns for w in split_ident(c)))
        best = max(self.tables.values(), key=score, default=None)
        return best.name if best and score(best) > 0 else None

    # --- sub-agent 2: FK traversal ---
    def _traverse(self, anchor, depth=None):
        seen, frontier = [anchor], [anchor]
        for _ in range(self.depth if depth is None else depth):  # ponytail: BFS both FK directions; depth=1 default, raise if multi-join recall is low
            frontier = [n for f in frontier for n in sorted(self.adj[f]) if n not in seen]
            seen += [n for n in dict.fromkeys(frontier)]
        return seen

    def retrieve(self, query, mode="hybrid_pruned"):
        assert mode in MODES, mode
        t0 = time.perf_counter()
        multi = mode.startswith("hybrid") and (self.adaptive or self.multi_anchors) and (not self.gate or classify_query(query) == "multi-join")
        anchors = ([self._structural_anchor(query)] if mode == "structural"
                   else self._semantic_anchors(query, self.multi_anchors if multi and self.multi_anchors else 1))
        anchor = anchors[0] if anchors and anchors[0] else None
        if anchor is None:
            names = []
        elif mode.startswith("hybrid"):
            names = self._traverse(anchor, self.depth + (1 if multi and self.adaptive else 0))
            names = list(dict.fromkeys(names + [t for o in anchors[1:] for t in self._path(anchor, o)]))
        else:
            names = [anchor]
        # --- sub-agent 3: pruning (hybrid_pruned only) ---
        terms = query_terms(query) if mode == "hybrid_pruned" else None
        cols = {n: keep_columns(self.tables[n], terms, self.threshold, self.labels)
                if terms is not None and len(self.tables[n].columns) > self.min_cols  # min_cols: leave narrow tables whole
                else [c for c, _, _ in self.tables[n].columns] for n in names}
        text = "\n\n".join(render(self.tables[n], cols[n]) for n in names)
        return Context(mode, anchor, cols, text, len(_enc().encode(text)), (time.perf_counter() - t0) * 1000)
