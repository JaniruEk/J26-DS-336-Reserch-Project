import json
from pathlib import Path

ROOT =Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "results/day5/baseline_predictions.json"

def load_fixed_examples(limit=100):
    with open(INPUT_FILE,"r",encoding="utf-8") as f:
        questions = json.load(f)

    examples =[]

    for row in questions[:limit]:
        examples.append({
            "question_id":row["question_id"],
            "db_id":row["db_id"],
            "questions":row["question"],
            "gold_sql":row["gold_sql"]
        })

    return examples

if __name__ =="__main__":
    examples = load_fixed_examples(limit=100)
    print(f"Loaded {len(examples)} questions")
    print(examples[0])