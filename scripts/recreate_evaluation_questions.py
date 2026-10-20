
import pandas as pd
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BASELINE_FILE = ROOT / "results" / "day4_int4_results.csv"

OUTPUT_FILE = (
    ROOT / "data" / "spider_data" /
    "spider_data" / "evaluation_question.json"
)

# Load the original baseline results
df = pd.read_csv(BASELINE_FILE)

print("Available columns:", df.columns.tolist())

# Required information
required = ["ID", "Question", "DB_ID", "Expected_SQL"]

missing = [col for col in required if col not in df.columns]

if missing:
    raise ValueError(
        f"Missing columns: {missing}. "
        "Check your baseline CSV before continuing."
    )

# Keep the original 100 questions
questions = df[required].drop_duplicates(
    subset=["ID"]
)

# Ensure all 100 questions are present
if len(questions) != 100:
    raise ValueError(
        f"Expected 100 questions, found {len(questions)}"
    )

# Convert to JSON
evaluation_questions = questions.to_dict(orient="records")

# Create output directory if necessary
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Save JSON
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(
        evaluation_questions,
        f,
        indent=4,
        ensure_ascii=False
    )

print("\nEvaluation questions recreated successfully!")
print("Total questions:", len(evaluation_questions))
print("Saved to:", OUTPUT_FILE)

