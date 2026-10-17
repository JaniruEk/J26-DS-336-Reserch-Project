import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE =ROOT/"results/baseline_results.csv"
OUTPUT_FILE = ROOT / "results/day5/baseline_predictions.json"

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

predictions=[]

with open(INPUT_FILE,"r",encoding="utf-8-sig",newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:
        predictions.append({
            "question_id":int(row["ID"]),
            "db_id":"concert_singer" , #Hard Code
            "question":row["Question"],
            "gold_sql":row["Expected_SQL"] ,
            "generated_sql":row["Generated_SQL"]
        })

with open(OUTPUT_FILE,"w",encoding="utf-8")as f:
    json.dump(predictions,f,indent=4, ensure_ascii=False)

print(f"Converted {len(predictions)} questions.")
print(f"Saved to: {OUTPUT_FILE}")