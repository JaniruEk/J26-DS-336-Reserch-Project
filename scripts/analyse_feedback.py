
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]

feedback_path = (
    ROOT / "results" / "day5" / "execution_feedback.json"
)

with open(feedback_path, "r", encoding="utf-8") as f:
    results = json.load(f)

valid_results = [
    r for r in results if r["gold_executed"]
]

error_counts = Counter(
    r["error_type"] for r in valid_results
)

print("\n--- SQL ERROR DISTRIBUTION ---")

for error_type, count in error_counts.most_common():
    print(f"{error_type}: {count}")

summary_path = (
    ROOT / "results" / "day5" / "error_summary.json"
)

with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(
        dict(error_counts),
        f,
        indent=4
    )

print(f"\nSaved summary: {summary_path}")
