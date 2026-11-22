"""Context width: how much schema the SQL model sees for one question (Agent 1, adaptive-width study).

Four widths, narrow to wide, all built from the existing retrieval modes:
  W1  the anchor table only, all columns          (mode 'semantic')
  W2  anchor tables + FK tables, columns pruned   (mode 'hybrid_pruned')
  W3  anchor tables + FK tables, all columns      (mode 'hybrid')
  W4  the full schema
Use a Retriever made with RECOMMENDED (and narrow_simple unset), so W2 and W3 are the settings of the earlier results.

features(): the inputs of the width selector. Everything in it is known BEFORE the SQL model runs.
labels(), choose_*(), evaluate(): pure functions on sweep rows (scripts/width_sweep.py), no model needed.
"""
import time
from statistics import mean

from .complexity import BUCKETS, SCHEMA_MODEL_PATH, _model, schema_features
from .retrieval import Context, _enc
from .schema import render
from .stats import bootstrap_ci, mcnemar_exact

WIDTHS = ("W1", "W2", "W3", "W4")
_MODE = {"W1": "semantic", "W2": "hybrid_pruned", "W3": "hybrid"}


def width_context(r, question, width):
    """The schema context at one width. r: a Retriever."""
    assert width in WIDTHS, width
    if width in _MODE:
        return r.retrieve(question, _MODE[width])
    t0 = time.perf_counter()
    cols = {n: [c for c, _, _ in t.columns] for n, t in r.tables.items()}
    text = "\n\n".join(render(r.tables[n], cols[n], r._notes(n)) for n in r.tables)
    return Context("full", None, cols, text, len(_enc().encode(text)), (time.perf_counter() - t0) * 1000)


def elbow_k(sims, alpha=0.6):
    """How many tables to keep, from the shape of the similarity scores (best first): the rank with the largest
    distance from the straight line between the first score and the last (the 'elbow'), scaled by alpha.
    A simplified form of the adaptive elbow of Picariello et al. (arXiv 2611.20979): no smoothing, no training."""
    n = len(sims)
    if n < 3 or sims[0] == sims[-1]:
        return n
    gap = [sims[0] + (sims[-1] - sims[0]) * i / (n - 1) - s for i, s in enumerate(sims)]
    knee = max(range(n), key=lambda i: abs(gap[i]))
    head = knee if gap[knee] > 0 else knee + 1  # below the line: the first tail table; above it: the last head table
    return max(1, min(n, round(alpha * head)))


def elbow_context(r, question, alpha=0.6):
    """Baseline 'E': the tables above the elbow, plus the tables on the FK paths between them, all columns."""
    t0 = time.perf_counter()
    res = r._index().query(query_texts=[question], n_results=len(r.tables))
    ids, sims = res["ids"][0], [1 - d for d in res["distances"][0]]
    keep = ids[:elbow_k(sims, alpha)]
    names = list(dict.fromkeys(keep + [t for o in keep[1:] for t in r._path(keep[0], o)]))
    cols = {n: [c for c, _, _ in r.tables[n].columns] for n in names}
    text = "\n\n".join(render(r.tables[n], cols[n], r._notes(n)) for n in names)
    return Context("elbow", keep[0], cols, text, len(_enc().encode(text)), (time.perf_counter() - t0) * 1000)


FEATURES = (*(f"p_{b}" for b in BUCKETS), "sim1", "sim2", "sim3", "sim_gap", "n_tables", "n_columns",
            "named", "touched", "span", "cover", "tok_W1", "tok_W2", "tok_W3", "tok_W4", "q_words")
# Ablation: the same learned selector with complexity and question length only (an Adaptive-RAG-style router,
# Jeong et al. NAACL 2024). If the full selector does not beat it, the schema/retrieval features add nothing.
COMPLEXITY_ONLY = (*(f"p_{b}" for b in BUCKETS), "q_words")


def features(r, question, contexts=None):
    """Selector inputs for one question, as a dict keyed by FEATURES. contexts: {width: Context} if already built."""
    sf = schema_features(r, question)
    m = _model(SCHEMA_MODEL_PATH)
    proba = dict(zip(map(str, m.classes_), m.predict_proba([(question, sf)])[0]))
    k = min(3, len(r.tables))
    dist = r._index().query(query_texts=[question], n_results=k)["distances"][0]
    sim = [1 - d for d in dist] + [0.0] * (3 - k)  # table similarity to the question, best first
    contexts = contexts or {w: width_context(r, question, w) for w in WIDTHS}
    out = {f"p_{b}": float(proba.get(b, 0.0)) for b in BUCKETS}
    out.update(sim1=sim[0], sim2=sim[1], sim3=sim[2], sim_gap=sim[0] - sim[1], n_tables=len(r.tables),
               n_columns=sum(len(t.columns) for t in r.tables.values()), named=sf[0], touched=sf[1], span=sf[2],
               cover=sf[5], q_words=len(question.split()), **{f"tok_{w}": contexts[w].tokens for w in WIDTHS})
    return out


# ---------------------------------------------------------------- sweep rows -> labels, choices, comparison
# A sweep row: {"id", "db", "bucket", "ok": {"W1": bool, ...}, "runs": {"W1": bool, ...}, "tokens": {"W1": int, ...},
#               "features": {...}}   ("runs": the SQL ran without a database error, right or wrong)

def label(row):
    """The narrowest width that gave correct SQL; None when every width failed (the question teaches nothing)."""
    return next((w for w in WIDTHS if row["ok"].get(w)), None)


def choose_fixed(width):
    return lambda row: width


def choose_rule(tau=0.5):
    """The rule in the app today: the anchor table only when the classifier is at least tau sure the question is simple."""
    return lambda row: "W1" if row["features"]["p_simple"] >= tau else "W2"


def choose_elbow(row):
    """The adaptive-elbow baseline; rows from a sweep run with --elbow carry it as width 'E'."""
    return "E"


def choose_oracle(row):
    """Upper limit: a correct width when one exists. Not usable in a real system (it needs the answer)."""
    return label(row) or "W1"


def retry_path(row, first, attempts=3):
    """The widths tried when a SQL that fails to run gets the next wider width, as /query does with a selector.
    A wrong answer that runs is not retried (as in the app). ponytail: offline approximation, the retry gets no
    error hint; the true app retry also sends the database error to the model."""
    path = [first]
    while len(path) < attempts and not row["runs"][path[-1]] and path[-1] != WIDTHS[-1]:
        path.append(WIDTHS[WIDTHS.index(path[-1]) + 1])
    return path


def accuracy(rows, choose):
    return mean(bool(r["ok"][choose(r)]) for r in rows)


def compare(rows, choose_a, choose_b):
    """Paired A against B on the same questions: difference, 95% bootstrap CI, wins/losses, exact McNemar p."""
    a = [bool(r["ok"][choose_a(r)]) for r in rows]
    b = [bool(r["ok"][choose_b(r)]) for r in rows]
    win, loss = sum(x and not y for x, y in zip(a, b)), sum(y and not x for x, y in zip(a, b))
    d, lo, hi = bootstrap_ci([x - y for x, y in zip(a, b)])
    return {"diff": d, "ci": (lo, hi), "wins": win, "losses": loss, "p": mcnemar_exact(win, loss)}


def cross_fit(rows, make_model, folds=5, seed=0, features=FEATURES):
    """Out-of-fold selector choices: every question is predicted by a model that never saw its DATABASE.
    make_model() -> object with fit(X, y) and predict(X). features: which inputs to use. Returns {row id: width}."""
    import random
    dbs = sorted({r["db"] for r in rows})
    random.Random(seed).shuffle(dbs)
    fold = {d: i % folds for i, d in enumerate(dbs)}
    x = lambda r: [r["features"][f] for f in features]
    out = {}
    for k in range(folds):
        train = [r for r in rows if fold[r["db"]] != k and label(r)]
        test = [r for r in rows if fold[r["db"]] == k]
        if not test:
            continue
        if len({label(r) for r in train}) < 2:  # nothing to learn: fall back to the most common label
            common = max(WIDTHS, key=[label(r) for r in train].count) if train else "W2"
            out.update({r["id"]: common for r in test})
            continue
        model = make_model()
        model.fit([x(r) for r in train], [label(r) for r in train])
        out.update({r["id"]: str(w) for r, w in zip(test, model.predict([x(r) for r in test]))})
    return out
