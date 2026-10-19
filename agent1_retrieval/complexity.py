"""Shared query-complexity taxonomy, derived from ground-truth SQL structure (used by Agents 1, 3, 4)."""
import re
from functools import lru_cache
from itertools import combinations
from pathlib import Path

BUCKETS = ("simple", "single-join", "multi-join", "aggregation")
MODEL_PATH = Path(__file__).with_name("complexity_nl.joblib")  # question text only
SCHEMA_MODEL_PATH = Path(__file__).with_name("complexity_schema.joblib")  # question text + schema features


@lru_cache(maxsize=2)
def _model(path=MODEL_PATH):
    import joblib
    return joblib.load(path)  # our own committed file from scripts/train_complexity.py (joblib = pickle: never load an untrusted one)


def schema_features(r, question):
    """Schema-name signals for the join count, which wording alone can't tell (it depends on the database).
    r: a Retriever. Reads table/column names and FKs only, never data values. Small capped ints (one-hot encoded)."""
    from .pruning import lemma, query_terms, split_ident
    qlem = {t.lemma_.lower() for t in query_terms(question)}  # stop words kept: spaCy calls 'name', 'first', 'last' stop words
    hit = lambda name: any(lemma(w) in qlem for w in split_ident(name) if w != "id")
    named = [n for n in r.tables if hit(n)]  # tables the question names
    touched = list(dict.fromkeys(named + [n for n, t in r.tables.items() if any(hit(c) for c, _, _ in t.columns)]))
    # cover: fewest tables whose names/columns contain every question word some (but not most) tables contain,
    # a greedy set-cover estimate of how many tables the SQL must join. Words in most tables (e.g. 'name') say nothing.
    names = {n: {lemma(w) for x in [n] + [c for c, _, _ in t.columns] for w in split_ident(x) if w != "id"} for n, t in r.tables.items()}
    words = {w for w in qlem if 0 < sum(w in s for s in names.values()) <= max(1, len(names) // 2)}
    cover = []
    while words:
        best = max(names, key=lambda n: len(words & names[n]))
        if not words & names[best]:
            break
        cover.append(best)
        words -= names[best]

    def hops(a, b):  # FK distance; 4 = not connected
        p = r._path(a, b)
        return len(p) - 1 if p[0] == a else 4
    span = max((hops(a, b) for a, b in combinations(named or touched, 2)), default=0)
    anchors = r._semantic_anchors(question, 3)
    sem = [hops(anchors[0], b) for b in anchors[1:]] + [0, 0]
    cover_span = max((hops(a, b) for a, b in combinations(cover, 2)), default=0)
    return [min(len(named), 4), min(len(touched), 6), min(span, 4), min(sem[0], 4), min(sem[1], 4),
            min(len(cover), 4), min(cover_span, 4)]


def _texts(X):  # model input rows are (question, schema_features); module-level so the pipeline pickles
    return [x[0] for x in X]


def _schemas(X):
    return [x[1] for x in X]


def _predict(question, retriever, how):
    if retriever is not None:
        return getattr(_model(SCHEMA_MODEL_PATH), how)([(question, schema_features(retriever, question))])[0], _model(SCHEMA_MODEL_PATH)
    return getattr(_model(), how)([question])[0], _model()


def classify_query(question, retriever=None):
    """Live, pre-generation label (classify_sql needs gold SQL, which doesn't exist at query time).
    retriever=None: question text only (the original model); a Retriever: text + schema features (better on joins)."""
    return str(_predict(question, retriever, "predict")[0])


def p_simple(question, retriever=None):
    """Classifier probability that the question is 'simple' (no join, no aggregate): used to decide context width."""
    p, m = _predict(question, retriever, "predict_proba")
    return float(p[list(m.classes_).index("simple")])


def classify_sql(sql):
    if re.search(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\(|\bGROUP\s+BY\b", sql, re.I):
        return "aggregation"
    joins = len(re.findall(r"\bJOIN\b", sql, re.I))
    return "simple" if joins == 0 else "single-join" if joins == 1 else "multi-join"
