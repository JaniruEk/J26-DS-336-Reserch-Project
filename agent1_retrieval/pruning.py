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


def relevance(col_name, terms, threshold, prefix=None):
    """Why a column matches the question: 'lemma_match', 'similarity', or None."""
    words = [w for w in split_ident(col_name) if w != prefix] or split_ident(col_name)
    qlemmas = {t.lemma_.lower() for t in terms}
    if any(lemma(w) in qlemmas for w in words):
        return "lemma_match"
    phrase = nlp()(" ".join(words))
    if not phrase.has_vector:
        return None
    return "similarity" if any(t.has_vector and not t.is_stop and phrase.similarity(t) >= threshold for t in terms) else None


def is_relevant(col_name, terms, threshold, prefix=None):
    return relevance(col_name, terms, threshold, prefix) is not None


LABEL_WORDS = {"name", "title", "first", "last"}


def keep_columns(table, terms, threshold=0.6, labels=False):
    """labels=True also keeps display columns (Name/Title/FirstName/LastName) - ablation, since questions rarely name them."""
    return [c for c, why in explain_columns(table, terms, threshold, labels).items() if why != "pruned"]


def explain_columns(table, terms, threshold=0.6, labels=False, rich=False, values=(), named=False):
    """Column -> reason it was kept ('primary_key', 'join_key', 'value_match', 'lemma_match', 'synonym_match',
    'similarity', 'label_column') or 'pruned'. First rule that applies wins.
    rich=False is the original rule set (keys, optional labels, lemma, similarity); rich=True adds the
    linking.py signals - value matches, split/abbreviated names, synonyms - and keeps the display columns of a
    table the question names (or of a table where nothing else matched)."""
    pks = {c for c, _, pk in table.columns if pk}
    fks = {c for c, _, _ in table.fks}
    prefix = table_prefix(table)
    out = {}
    if rich:
        from .linking import identifier_words, question_lemmas, synonyms_of
        qlem = question_lemmas(terms)
        syn = synonyms_of(qlem)
        own = identifier_words(table.name)
    for c, _, _ in table.columns:
        if c in pks:
            out[c] = "primary_key"
        elif c in fks:
            out[c] = "join_key"
        elif not rich:
            out[c] = ("label_column" if labels and set(split_ident(c)) <= LABEL_WORDS
                      else relevance(c, terms, threshold, prefix) or "pruned")
        elif c in values:
            out[c] = "value_match"
        else:
            words = identifier_words(c, prefix) - own or identifier_words(c, prefix)
            out[c] = ("lemma_match" if words & qlem else "synonym_match" if words & syn
                      else relevance(c, terms, threshold, prefix) or "pruned")
    if rich:
        evidence = any(r in ("lemma_match", "synonym_match") and c not in values for c, r in out.items())
        if named or labels or not evidence:
            for c in out:
                # identifier_words also splits lower-case names (PostgreSQL's productname), not only ProductName
                if out[c] == "pruned" and (set(split_ident(c)) | identifier_words(c, prefix)) & {"name", "title"}:
                    out[c] = "label_column"
    return out
