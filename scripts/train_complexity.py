"""Train the natural-language complexity classifier (question text -> simple/single-join/multi-join/aggregation).
Labels come from classify_sql on Spider *train* gold SQL (nested/compound skipped); evaluated on the disjoint
Spider dev pairs plus Chinook/TPC-H (out-of-domain). Needs data/spider.zip (python scripts/get_spider.py)."""
import json
import re
import zipfile
from collections import Counter

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.pipeline import make_pipeline

from agent1_retrieval.complexity import BUCKETS, MODEL_PATH, classify_sql

nested = re.compile(r"\bSELECT\b.*\bSELECT\b|\bINTERSECT\b|\bUNION\b|\bEXCEPT\b", re.I | re.S)
train = json.loads(zipfile.ZipFile("data/spider.zip").read("spider_data/train_spider.json"))
train = [d for d in train if not nested.search(d["query"])]
X, y = [d["question"] for d in train], [classify_sql(d["query"]) for d in train]
print("train", len(X), Counter(y))

model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2),
                      LogisticRegression(max_iter=2000, class_weight="balanced"))
model.fit(X, y)

for name in ("spider", "chinook", "tpch"):
    pairs = json.load(open(f"eval/{name}_pairs.json", encoding="utf-8"))
    gold = [classify_sql(p["sql"]) for p in pairs]
    pred = list(model.predict([p["question"] for p in pairs]))
    acc = sum(a == b for a, b in zip(gold, pred)) / len(gold)
    print(f"\n{name}: accuracy {acc:.2f} (n={len(gold)}, majority-baseline {Counter(gold).most_common(1)[0][1] / len(gold):.2f})")
    print("rows=gold cols=pred", BUCKETS)
    print(confusion_matrix(gold, pred, labels=BUCKETS))

joblib.dump(model, MODEL_PATH)
print("\nsaved", MODEL_PATH)
