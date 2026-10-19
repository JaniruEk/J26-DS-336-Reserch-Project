"""Train the schema-aware complexity classifier: question text (TF-IDF) + schema features from Agent 1's retriever
(complexity.schema_features: tables named/touched by the question, their FK distance, distance between the top-3
semantic anchors). Same labels and splits as scripts/train_complexity.py (Spider *train* gold SQL via classify_sql,
nested/compound skipped; Spider train and dev databases are disjoint), compared with the text-only model.
Extracts the Spider train databases from data/spider.zip into data/spider_train/ (schema is all that is read).
Usage: python -m scripts.train_complexity_schema"""
import json
import re
import zipfile
from collections import Counter
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.pipeline import FunctionTransformer, make_pipeline, make_union
from sklearn.preprocessing import OneHotEncoder

from agent1_retrieval.complexity import BUCKETS, SCHEMA_MODEL_PATH, _model, _schemas, _texts, classify_sql, schema_features
from agent1_retrieval.retrieval import Retriever

ZIP, OUT = zipfile.ZipFile("data/spider.zip"), Path("data/spider_train")
nested = re.compile(r"\bSELECT\b.*\bSELECT\b|\bINTERSECT\b|\bUNION\b|\bEXCEPT\b", re.I | re.S)
train = [d for d in json.loads(ZIP.read("spider_data/train_spider.json")) if not nested.search(d["query"])]

retrievers = {}


def retriever(path):
    if path not in retrievers:
        retrievers[path] = Retriever(path, chroma_path=str(Path(path).parent / "_chroma"))
    return retrievers[path]


def train_db(name):
    p = OUT / name / f"{name}.sqlite"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(ZIP.read(f"spider_data/database/{name}/{name}.sqlite"))
    return str(p)


X = [(d["question"], schema_features(retriever(train_db(d["db_id"])), d["question"])) for d in train]
y = [classify_sql(d["query"]) for d in train]
print("train", len(X), Counter(y), "databases", len(retrievers))

onehot = OneHotEncoder(handle_unknown="ignore")
model = make_pipeline(
    make_union(make_pipeline(FunctionTransformer(_texts), TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2)),
               make_pipeline(FunctionTransformer(_schemas), onehot)),
    LogisticRegression(max_iter=3000, class_weight="balanced"))
model.fit(X, y)

text_model = _model()  # the original text-only classifier, for comparison
everything = []
for name in ("spider", "chinook", "tpch"):
    pairs = json.load(open(f"eval/{name}_pairs.json", encoding="utf-8"))
    gold = [classify_sql(p["sql"]) for p in pairs]
    old = list(text_model.predict([p["question"] for p in pairs]))
    new = list(model.predict([(p["question"], schema_features(retriever(p["db"]), p["question"])) for p in pairs]))
    everything += list(zip(gold, old, new))
    for p, g, o, n in zip(pairs, gold, old, new):  # per-question evidence: what the schema features fixed / broke
        if (g == o) != (g == n):
            print(f"{'FIXED' if g == n else 'BROKE'}  {name:<8} true={g:<12} text={o:<12} text+schema={n:<12} {p['question']}")
    acc = lambda pred: sum(a == b for a, b in zip(gold, pred)) / len(gold)
    print(f"\n{name} (n={len(gold)}): text-only {acc(old):.2f} -> text+schema {acc(new):.2f}")
    print("text+schema, rows=gold cols=pred", BUCKETS)
    print(confusion_matrix(gold, new, labels=BUCKETS))
g, o, n = zip(*everything)
print(f"\nALL eval pairs (n={len(g)}, the routing set Agent 3 uses): text-only {sum(a == b for a, b in zip(g, o)) / len(g):.3f}"
      f" -> text+schema {sum(a == b for a, b in zip(g, n)) / len(g):.3f}")
print("text-only confusion\n", confusion_matrix(g, o, labels=BUCKETS))
print("text+schema confusion\n", confusion_matrix(g, n, labels=BUCKETS))

joblib.dump(model, SCHEMA_MODEL_PATH)
print("\nsaved", SCHEMA_MODEL_PATH)
