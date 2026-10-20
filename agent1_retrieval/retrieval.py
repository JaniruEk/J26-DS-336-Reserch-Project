"""Agent 1: four switchable retrieval modes built from three sub-agents
(anchor selection -> FK traversal -> column pruning)."""
import hashlib
import json
import tempfile
import time
from pathlib import Path
from dataclasses import dataclass, replace
from functools import lru_cache

from .complexity import classify_query, p_simple
from .pruning import explain_columns, lemma, query_terms, split_ident
from .schema import adjacency, infer_fks, reflect, render

FUNCTION_POS = {"ADP", "DET", "AUX", "PRON", "CCONJ", "SCONJ", "PART", "INTJ", "PUNCT"}  # 'in', 'the', 'is', 'what', ...

MODES = ("semantic", "structural", "hybrid", "hybrid_pruned")
# PP1 configuration (Phase 8) = Phase 7's best execution config (3 anchors joined by FK paths on every question,
# tables with <= 8 columns left whole) + the rich linking signals. Column recall, hybrid_pruned: Chinook .95,
# TPC-H .97, Spider .98 (Spider never used for tuning). Execution accuracy for this exact config still has to be
# re-run with Ollama (`evaluate --recommended --exec phi3`). Constructor defaults stay as before so Phase 1-7 reproduce.
RECOMMENDED = {"multi_anchors": 3, "gate": False, "min_cols": 8, "rich": True}
# Live app default = RECOMMENDED + code values in the schema (measured 19 Oct 2026: value-coded exec .31->.69 phi3,
# .12->.56 Qwen-Coder-1.5B; ordinary questions unharmed) + the schema-aware complexity label for Agent 3's routing
# (148 eval questions: .588 -> .676, McNemar p=.029). RECOMMENDED itself stays fixed so earlier results reproduce.
LIVE = {**RECOMMENDED, "value_hints": True, "schema_classifier": True}


@dataclass
class Context:
    mode: str
    anchor: str | None
    columns: dict  # table -> kept column names
    text: str
    tokens: int
    ms: float
    reasons: dict = None  # table -> {column: why it was kept, or 'pruned'} (hybrid_pruned only)
    roles: dict = None  # table -> 'anchor' | 'fk_neighbour' | 'bridge'


@lru_cache(maxsize=1)
def _embedder():
    """Chroma's default MiniLM, minus padding every text to 256 tokens: same vectors (checked: max diff 0.0),
    ~15x faster per question (82 ms -> 5.5 ms on a 2-core VM). This is what keeps retrieval under the 500 ms NFR."""
    from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

    class _UnpaddedMiniLM(ONNXMiniLM_L6_V2):
        def __call__(self, input):
            self.tokenizer.no_padding()
            return [super(_UnpaddedMiniLM, self).__call__([d])[0] for d in input]

    return _UnpaddedMiniLM()


@lru_cache(maxsize=1)
def _enc():
    import tiktoken
    return tiktoken.get_encoding("cl100k_base")  # ponytail: proxy tokenizer, swap for the SLM's own once Agent 2 picks the base model


class Retriever:
    def __init__(self, db_path, depth=1, threshold=0.6, labels=False, adaptive=False, multi_anchors=0, gate=True, min_cols=0, chroma_path=None,
                 rich=False, infer_missing_fks=False, value_linking=True, value_hints=False, glossary=None, narrow_simple=None,
                 schema_classifier=False):
        # schema_classifier: complexity labels from question text + this database's schema (complexity_schema.joblib)
        # instead of text alone; used for the handoff label and for narrow_simple. Off = the original text-only model.
        self.schema_classifier = schema_classifier
        # narrow_simple=tau: complexity-adaptive width. If the classifier is at least tau sure the question is 'simple',
        # hybrid modes send only the anchor table (wide context distracts small models on easy questions); None = off.
        self.narrow_simple = narrow_simple
        # adaptive: +1 FK hop for questions predicted multi-join. multi_anchors=k: for those questions also take the top-k
        # semantic tables and connect them to the main anchor along shortest FK paths (bridge tables included).
        self.db_path, self.depth, self.threshold, self.labels, self.adaptive = db_path, depth, threshold, labels, adaptive
        self.multi_anchors, self.gate, self.min_cols, self.chroma_path = multi_anchors, gate, min_cols, chroma_path
        # rich: extra linking signals in pruning (linking.py). infer_missing_fks: add FKs implied by column names
        # when the schema declares none (both opt-in, so the Phase 1-7 numbers reproduce with the defaults).
        self.rich = rich
        # value_linking=False: rich linking never reads data values (switch off for databases holding personal data)
        self.value_linking = value_linking
        # value_hints: show the codes a column holds ("Discontinued TEXT /* values: '0', '1' */") so the model does not guess
        # 'yes'. Needs value_linking (it reads data). glossary: {"Table.Column": "C = closed, A = active"} or a JSON file path,
        # the bank's own data dictionary; it is configuration, not data, so it applies even with value_linking off.
        self.value_hints = value_hints and value_linking
        if isinstance(glossary, str):
            glossary = json.loads(Path(glossary).read_text(encoding="utf-8"))
        self.glossary = {k.lower(): v for k, v in (glossary or {}).items()}
        self._codes = {}
        self.tables = reflect(db_path)
        self.inferred = infer_fks(self.tables) if infer_missing_fks else []
        self.adj = adjacency(self.tables)
        self._col = None
        self._values = None  # vector index is built lazily so structural mode needs no embeddings

    # --- sub-agent 1: anchor selection ---
    def _index(self):
        if self._col is None:
            import chromadb
            # own on-disk client per Retriever: the shared in-process EphemeralClient intermittently returned no results across many collections
            client = chromadb.PersistentClient(self.chroma_path or tempfile.mkdtemp())
            self._col = client.get_or_create_collection("schema_" + hashlib.md5(str(self.db_path).encode()).hexdigest()[:12],
                                                        embedding_function=_embedder())
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

    def classifier_input(self):
        """What classify_query / p_simple get as `retriever`: self for the schema-aware model, None for text only."""
        return self if self.schema_classifier else None

    def matched(self, query):
        """Confidence gate: does a content word of the question name a table or column?
        False for gibberish / off-topic questions, which the semantic anchor would otherwise map to its nearest table anyway.
        Exact lemma matches only, on names split the way pruning splits them (linking.identifier_words: 'l_extendedprice'
        -> extended, price). Function words don't count: 'in' matched UnitsInStock, so "What is the weather in Paris?"
        passed on Northwind. Word-vector similarity doesn't count either: 'joke' was 'similar' to Name columns.
        Measured on all 224 eval questions: 0 declined (old rule: 0); 1 of 60 off-topic let through (old: most)."""
        from .linking import identifier_words
        from .pruning import table_prefix
        qlem = {t.lemma_.lower() for t in query_terms(query) if t.pos_ not in FUNCTION_POS}
        return any(qlem & identifier_words(n, table_prefix(t)) for t in self.tables.values() for n in [t.name] + [c for c, _, _ in t.columns])

    # --- sub-agent 2: FK traversal ---
    def _traverse(self, anchor, depth=None):
        seen, frontier = [anchor], [anchor]
        for _ in range(self.depth if depth is None else depth):  # ponytail: BFS both FK directions; depth=1 default, raise if multi-join recall is low
            frontier = [n for f in frontier for n in sorted(self.adj[f]) if n not in seen]
            seen += [n for n in dict.fromkeys(frontier)]
        return seen

    def retrieve(self, query, mode="hybrid_pruned", complexity=None):
        """complexity: known label (evaluation only, 'oracle' routing); None = the live classifier decides."""
        assert mode in MODES, mode
        t0 = time.perf_counter()
        if mode.startswith("hybrid") and self.narrow_simple is not None and (
                complexity == "simple" if complexity else p_simple(query, self.classifier_input()) >= self.narrow_simple):
            c = self.retrieve(query, "semantic")
            return replace(c, mode=mode, ms=(time.perf_counter() - t0) * 1000, roles={n: "anchor" for n in c.columns},
                           reasons={n: {k: "simple_question" for k in cs} for n, cs in c.columns.items()} if mode == "hybrid_pruned" else None)
        multi = mode.startswith("hybrid") and (self.adaptive or self.multi_anchors) and (not self.gate or classify_query(query, self.classifier_input()) == "multi-join")
        anchors = ([self._structural_anchor(query)] if mode == "structural"
                   else self._semantic_anchors(query, self.multi_anchors if multi and self.multi_anchors else 1))
        anchor = anchors[0] if anchors and anchors[0] else None
        bridge = set()
        anchors = [a for a in anchors if a] if anchor else []
        if anchor is None:
            names = []
        elif mode.startswith("hybrid"):
            names = self._traverse(anchor, self.depth + (1 if multi and self.adaptive else 0))
            paths = [t for o in anchors[1:] for t in self._path(anchor, o)]
            bridge = {t for t in paths if t not in names and t not in anchors}
            names = list(dict.fromkeys(names + paths))
        else:
            names = [anchor]
        roles = {n: "anchor" if n in anchors else "bridge" if n in bridge else "fk_neighbour" for n in names}
        # --- sub-agent 3: pruning (hybrid_pruned only) ---
        terms = query_terms(query) if mode == "hybrid_pruned" else None
        reasons = None
        if terms is not None:
            values = self._value_links(query, names) if self.rich and self.value_linking else {}
            qlem = {t.lemma_.lower() for t in terms}
            reasons = {n: explain_columns(self.tables[n], terms, self.threshold, self.labels, rich=self.rich,
                                          values=values.get(n, ()),
                                          named=self.rich and any(lemma(w) in qlem for w in split_ident(n)))
                       if len(self.tables[n].columns) > self.min_cols  # min_cols: leave narrow tables whole
                       else {c: "narrow_table" for c, _, _ in self.tables[n].columns} for n in names}
            if self.value_hints:  # code columns are cheap and usually what gets filtered on ("still being sold" -> Discontinued)
                for n in names:
                    self._notes(n)
                    for c in self._codes[n]:
                        if reasons[n].get(c) == "pruned":
                            reasons[n][c] = "code_column"
            cols = {n: [c for c, why in reasons[n].items() if why != "pruned"] for n in names}
        else:
            cols = {n: [c for c, _, _ in self.tables[n].columns] for n in names}
        text = "\n\n".join(render(self.tables[n], cols[n], self._notes(n)) for n in names)
        return Context(mode, anchor, cols, text, len(_enc().encode(text)), (time.perf_counter() - t0) * 1000, reasons, roles)

    def _notes(self, name):
        """Per-column comments for the schema shown to the model: glossary meaning and/or code values."""
        if not (self.value_hints or self.glossary):
            return None
        if self.value_hints and name not in self._codes:
            from .linking import code_values
            self._codes[name] = code_values(self.db_path, self.tables[name])
        notes = {}
        for c, _, _ in self.tables[name].columns:
            parts = [self.glossary[k] for k in (f"{name}.{c}".lower(),) if k in self.glossary]
            if self.value_hints and c in self._codes[name]:
                parts.append("values: " + ", ".join(repr(v) for v in self._codes[name][c]))
            if parts:
                notes[c] = "; ".join(parts)
        return notes

    def _value_links(self, query, names):
        if self._values is None:
            from .linking import ValueLinker
            self._values = ValueLinker(self.db_path, self.tables)
        return self._values.link(query, names)
