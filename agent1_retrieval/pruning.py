"""Column-level pruning (the novel contribution): keys always kept; other columns kept on
lemma overlap with the query, else on spaCy word-vector cosine similarity >= threshold."""
import re
from functools import lru_cache

import spacy


@lru_cache(maxsize=1)
def nlp():
    return spacy.load("en_core_web_md")


def split_ident(name):
    """'BillingAddress' / 'billing_address' -> ['billing', 'address']"""
    return re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name).replace("_", " ").lower().split()


@lru_cache(maxsize=None)
def lemma(word):
    return nlp()(word)[0].lemma_.lower()


def query_terms(query):
    """All alphabetic tokens. Stop words stay: spaCy lists 'name', 'first', 'last' as stop words, which are real column words."""
    return [t for t in nlp()(query) if t.is_alpha]


def table_prefix(table):
    """TPC-H-style 'c_name'/'c_acctbal': a short token shared by every column is a table abbreviation, not a word."""
    firsts = {split_ident(c)[0] for c, _, _ in table.columns if "_" in c}
    return firsts.pop() if len(firsts) == 1 and all("_" in c for c, _, _ in table.columns) and len(next(iter(firsts))) <= 3 else None


def is_relevant(col_name, terms, threshold, prefix=None):
    words = [w for w in split_ident(col_name) if w != prefix] or split_ident(col_name)
    qlemmas = {t.lemma_.lower() for t in terms}
    if any(lemma(w) in qlemmas for w in words):
        return True
    phrase = nlp()(" ".join(words))
    if not phrase.has_vector:
        return False
    return any(t.has_vector and not t.is_stop and phrase.similarity(t) >= threshold for t in terms)


LABEL_WORDS = {"name", "title", "first", "last"}


def keep_columns(table, terms, threshold=0.6, labels=False):
    """labels=True also keeps display columns (Name/Title/FirstName/LastName) - ablation, since questions rarely name them."""
    keys = {c for c, _, pk in table.columns if pk} | {c for c, _, _ in table.fks}
    prefix = table_prefix(table)
    return [c for c, _, _ in table.columns
            if c in keys or (labels and set(split_ident(c)) <= LABEL_WORDS) or is_relevant(c, terms, threshold, prefix)]
