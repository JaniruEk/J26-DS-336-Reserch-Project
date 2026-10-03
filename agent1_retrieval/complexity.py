"""Shared query-complexity taxonomy, derived from ground-truth SQL structure (used by Agents 1, 3, 4)."""
import re
from functools import lru_cache
from pathlib import Path

BUCKETS = ("simple", "single-join", "multi-join", "aggregation")
MODEL_PATH = Path(__file__).with_name("complexity_nl.joblib")


@lru_cache(maxsize=1)
def _model():
    import joblib
    return joblib.load(MODEL_PATH)  # trained by scripts/train_complexity.py


def classify_query(question):
    """Live, pre-retrieval label from the question text alone (classify_sql needs gold SQL, which doesn't exist at query time)."""
    return str(_model().predict([question])[0])


def classify_sql(sql):
    if re.search(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\(|\bGROUP\s+BY\b", sql, re.I):
        return "aggregation"
    joins = len(re.findall(r"\bJOIN\b", sql, re.I))
    return "simple" if joins == 0 else "single-join" if joins == 1 else "multi-join"
