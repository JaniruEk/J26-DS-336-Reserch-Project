"""Download Spider, extract the dev databases to data/spider/, and build a stratified, reproducible
eval/spider_pairs.json (PER_BUCKET per complexity bucket). Nested/compound queries are skipped because the
regex gold-link extraction in evaluate.py is not reliable for them."""
import json
import os
import random
import re
import urllib.request
import zipfile

from agent1_retrieval.complexity import BUCKETS, classify_sql

FILE_ID = "1403EGqzIDoHMdQF4c9Bkyl7dZLZ5Wt6J"  # official Spider release on Google Drive
PER_BUCKET = 30
ZIP = "data/spider.zip"


def download():
    if os.path.exists(ZIP):
        return
    os.makedirs("data", exist_ok=True)
    page = urllib.request.urlopen(f"https://drive.google.com/uc?export=download&id={FILE_ID}").read().decode()
    uuid = re.search(r'name="uuid" value="([^"]+)"', page).group(1)  # Drive's large-file confirmation step
    urllib.request.urlretrieve(
        f"https://drive.usercontent.google.com/download?id={FILE_ID}&export=download&confirm=t&uuid={uuid}", ZIP)


def extract_and_build():
    z = zipfile.ZipFile(ZIP)
    dev = json.loads(z.read("spider_data/dev.json"))
    for db in sorted({d["db_id"] for d in dev}):
        os.makedirs(f"data/spider/{db}", exist_ok=True)
        with open(f"data/spider/{db}/{db}.sqlite", "wb") as f:
            f.write(z.read(f"spider_data/database/{db}/{db}.sqlite"))
    nested = re.compile(r"\bSELECT\b.*\bSELECT\b|\bINTERSECT\b|\bUNION\b|\bEXCEPT\b", re.I | re.S)
    ok = [d for d in dev if not nested.search(d["query"])]
    rnd = random.Random(0)
    pairs = []
    for b in BUCKETS:
        pool = sorted((d for d in ok if classify_sql(d["query"]) == b), key=lambda d: (d["db_id"], d["question"]))
        pairs += rnd.sample(pool, min(PER_BUCKET, len(pool)))
    out = [{"db": f"data/spider/{d['db_id']}/{d['db_id']}.sqlite", "question": d["question"], "sql": d["query"]}
           for d in pairs]
    json.dump(out, open("eval/spider_pairs.json", "w", encoding="utf-8"), indent=1)
    print(len(out), "pairs written to eval/spider_pairs.json")


if __name__ == "__main__":
    download()
    extract_and_build()
