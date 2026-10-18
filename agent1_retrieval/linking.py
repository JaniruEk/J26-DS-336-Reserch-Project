"""Extra schema-linking signals for the pruning sub-agent (opt-in: `Retriever(..., rich=True)`).

Lemma overlap and word vectors cannot read three things that real schemas and questions contain:
1. run-together / abbreviated column names - TPC-H `c_acctbal`, `l_extendedprice`, `o_totalprice`
   (`identifier_words` splits them with the spaCy vocabulary and a short abbreviation list);
2. everyday paraphrase - "spent" for `Total`, "expensive" for `UnitPrice`, "sold" for `Quantity`
   (`SYNONYMS`, a small hand-written business vocabulary, reported as its own reason);
3. data values - "customers from Canada" never says "country" (`ValueLinker` checks the DB, read-only).
Every kept column carries the name of the signal that kept it, so a decision can always be explained.
"""
import re
import time
from functools import lru_cache

from .db import DBError, is_url, quote, session
from .pruning import lemma, nlp, split_ident

ABBREV = {
    "acct": "account", "bal": "balance", "amt": "amount", "qty": "quantity", "num": "number", "no": "number",
    "addr": "address", "desc": "description", "cust": "customer", "prod": "product", "dept": "department",
    "emp": "employee", "mgr": "manager", "org": "organization", "tel": "telephone", "ph": "phone", "dob": "birth",
    "yr": "year", "pct": "percent", "avg": "average", "inv": "invoice", "txn": "transaction", "supp": "supplier",
    "mfgr": "manufacturer", "mkt": "market", "cnt": "count", "nbr": "number", "loc": "location", "ctry": "country",
}

_GROUPS = [
    {"customer", "client", "buyer", "consumer", "shopper"},
    {"employee", "staff", "worker", "representative", "rep", "agent", "clerk"},
    {"supplier", "vendor", "provider"},
    {"product", "item", "goods", "merchandise"},
    {"order", "purchase", "sale", "invoice", "transaction"},
    {"amount", "price", "cost", "value", "total", "balance", "payment", "revenue", "salary", "fee", "charge",
     "spend", "spent", "pay", "paid", "expensive", "cheap", "costly", "dollar", "money", "sale", "sales", "earn"},
    {"quantity", "sell", "sold", "unit", "units"},
    {"department", "division"},
    {"address", "located", "live", "city", "country"},
    {"phone", "telephone", "mobile"},
    {"mail", "email"},
    {"birth", "born", "birthday", "age"},
    {"hire", "hired", "join", "joined"},
    {"status", "state"},
    {"length", "long", "longer", "short", "shorter", "duration", "millisecond", "milliseconds", "minute", "second"},
    {"genre", "category", "kind", "type"},
    {"ship", "shipped", "shipping", "deliver", "delivered", "delivery", "shipper", "freight"},
]
_NO_TRIGGER = {"total", "amount", "value", "type", "kind", "state", "unit", "join", "item", "agent", "second", "age"}
SYNONYMS = {}
for _g in _GROUPS:
    for _w in _g - _NO_TRIGGER:
        SYNONYMS.setdefault(_w, set()).update(_g - {_w})

LABEL_WORDS = {"name", "title", "first", "last"}


def _known(w):
    return w in ABBREV or nlp().vocab.has_vector(w)


@lru_cache(maxsize=None)
def segment(word):
    """'totalprice' -> ['total', 'price']; 'acctbal' -> ['acct', 'bal']; known words are left alone."""
    if len(word) < 6 or not word.isalpha() or _known(word):
        return [word]
    for i in range(3, len(word) - 2):
        if _known(word[:i]) and _known(word[i:]):
            return [word[:i], word[i:]]
    for i in range(3, len(word) - 5):
        rest = segment(word[i:])
        if _known(word[:i]) and len(rest) == 2:
            return [word[:i], *rest]
    return [word]


@lru_cache(maxsize=None)
def identifier_words(name, prefix=None):
    """Lemmas a column name stands for: split, de-prefixed, de-compounded, abbreviations expanded."""
    raw = [w for w in split_ident(name) if w != prefix] or split_ident(name)
    out = set()
    for w in raw:
        for part in segment(w):
            out.add(part)
            out.add(ABBREV.get(part, part))
    return frozenset(lemma(w) for w in out if len(w) > 1 and w not in {"id", "key"})


def question_lemmas(terms):
    return {t.lemma_.lower() for t in terms} | {t.text.lower() for t in terms}


def synonyms_of(lemmas):
    return set().union(*(SYNONYMS.get(w, set()) for w in lemmas)) - set(lemmas) if lemmas else set()


class ValueLinker:
    """Which columns hold a literal mentioned in the question ("Canada", "Rock", "Speedy Express").
    Read-only. Categorical columns (<= max_distinct values) are cached once; other text columns of the
    *selected* tables get an equality probe for capitalised / quoted / digit-bearing phrases, under a time budget.
    Only column names leave this class - never the values."""

    def __init__(self, db_path, tables, max_distinct=60, budget_ms=150, max_probes=80):
        self.db_path, self.tables = db_path, tables
        self.max_distinct, self.budget_ms, self.max_probes = max_distinct, budget_ms, max_probes
        self._cat = None

    @staticmethod
    def _text(typ):
        return not typ or any(k in typ.lower() for k in ("char", "text", "clob", "string"))

    def _text_cols(self, t):
        keys = {c for c, _, pk in t.columns if pk} | {c for c, _, _ in t.fks}
        return [c for c, typ, _ in t.columns if c not in keys and self._text(typ)]

    def _categorical(self):
        if self._cat is None:
            self._cat = {}
            db = self.db_path
            with session(db) as run:
                for t in self.tables.values():
                    for c in self._text_cols(t):
                        qc, qt = quote(db, c), quote(db, t.name)
                        try:
                            _, vals = run(f"SELECT DISTINCT {qc} FROM {qt} WHERE {qc} IS NOT NULL LIMIT {self.max_distinct + 1}")
                        except DBError:
                            continue
                        if 0 < len(vals) <= self.max_distinct:
                            self._cat[(t.name, c)] = {_norm(str(v)) for (v,) in vals if isinstance(v, str)}
        return self._cat

    def link(self, query, names):
        hits = {}
        q = f" {_norm(query)} "
        for (t, c), vals in self._categorical().items():
            if t in names and any(len(v) >= 3 and f" {v} " in q for v in vals):
                hits.setdefault(t, set()).add(c)
        cands = literals(query)
        if cands:
            db, t0, n = self.db_path, time.perf_counter(), 0
            with session(db) as run:
                for t in names:
                    for c in self._text_cols(self.tables[t]):
                        if c in hits.get(t, ()):
                            continue
                        qc = quote(db, c)
                        # same case-insensitive equality either way; SQLite keeps its original NOCASE form
                        cond = f"{qc} = :v COLLATE NOCASE" if not is_url(db) else f"LOWER({qc}) = LOWER(:v)"
                        for lit in cands:
                            n += 1
                            if n > self.max_probes or (time.perf_counter() - t0) * 1000 > self.budget_ms:
                                return hits
                            try:
                                if run(f"SELECT 1 FROM {quote(db, t)} WHERE {cond} LIMIT 1", {"v": lit})[1]:
                                    hits.setdefault(t, set()).add(c)
                                    break
                            except DBError:
                                break
        return hits


def _norm(s):
    return " ".join(re.sub(r"[^a-z0-9#/&'+ ]+", " ", s.lower()).split())


_STARTERS = {"what", "which", "who", "whom", "how", "list", "show", "find", "give", "tell", "when", "where", "return", "count"}


def literals(query):
    """Phrases that look like data values: quoted text, Capitalised runs (not the first word), tokens with digits."""
    out = [a or b for a, b in re.findall(r'"([^"]+)"|\'([^\']+)\'', query)]
    toks = re.findall(r"[A-Za-z0-9#/&'.\-]+", query)
    run = []
    for i, tok in enumerate(toks + [""]):
        tok = tok.strip(".'")
        cap = bool(tok) and tok[0].isupper() and i > 0 and tok.lower() not in _STARTERS
        digit = any(ch.isdigit() for ch in tok) and any(ch.isalpha() or ch == "#" for ch in tok)
        if cap or digit:
            run.append(tok)
        else:
            if run:
                out.append(" ".join(run))
                if len(run) > 1:
                    out.extend(run)
            run = []
    seen, res = set(), []
    for c in out:
        c = re.sub(r"'s$", "", c.strip())
        if len(c) >= 2 and c.lower() not in seen:
            seen.add(c.lower())
            res.append(c)
    return res
