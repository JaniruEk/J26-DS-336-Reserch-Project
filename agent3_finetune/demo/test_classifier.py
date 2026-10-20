"""Tests for the demo's classifier loader (needs scikit-learn and joblib, which are already in the project).
    python -m pytest agent3_finetune/demo/test_classifier.py -v
"""
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from agent3_finetune.demo.classifier import LiveClassifier


def _tiny_model(path):
    texts = ["how many singers are there", "list all concerts", "show singers with their concerts",
             "which singer performed in the most concerts per country"]
    labels = ["aggregation", "simple", "single-join", "multi-join"]
    joblib.dump(make_pipeline(TfidfVectorizer(), LogisticRegression(max_iter=200)).fit(texts, labels), path)


def test_loads_and_predicts_a_string(tmp_path):
    p = tmp_path / "c.joblib"
    _tiny_model(p)
    c = LiveClassifier(p)
    assert c.available and c.error is None
    assert isinstance(c.predict("how many singers are there"), str)


def test_missing_file_is_not_a_crash(tmp_path):
    c = LiveClassifier(tmp_path / "nope.joblib")
    assert not c.available and c.error
    assert c.predict("anything") is None


def test_corrupt_file_is_not_a_crash(tmp_path):
    p = tmp_path / "bad.joblib"
    p.write_bytes(b"not a joblib file")
    c = LiveClassifier(p)
    assert not c.available and c.predict("x") is None
