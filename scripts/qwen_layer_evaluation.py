
import csv
from pathlib import Path

from src.qwen_evaluator import calculate_em, calculate_ex

ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "results/qwen/qwen_layer_predictions.csv"
OUTPUT = ROOT / "results/qwen/qwen_layer_evaluated.csv"

DATABASE_DIR = (
    ROOT / "data/spider_data/spider_data/database"
)

with open(INPUT, "r", encoding="utf-8", newline="") as f:
    predictions = list(csv.DictReader(f))

results = []

for index, row in enumerate(predictions, 1):

    db_id = row["db_id"]
    gold_sql = row["gold_sql"]
    generated_sql = row["generated_sql"]

    db_path = DATABASE_DIR / db_id / f"{db_id}.sqlite"

    em = calculate_em(gold_sql, generated_sql)

    ex = calculate_ex(
        db_path,
        gold_sql,
        generated_sql
    )

    result = dict(row)
    result["EM"] = em
    result["EX"] = ex

    results.append(result)

    if index % 25 == 0:
        print(f"Evaluated {index}/{len(predictions)}")

if not results:
    raise ValueError("No layer predictions found.")

with open(OUTPUT, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(results[0].keys())
    )
    writer.writeheader()
    writer.writerows(results)

print("Evaluation completed!")
print("Saved to:", OUTPUT)
