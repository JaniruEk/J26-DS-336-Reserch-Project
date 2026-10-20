
import csv
import json
import time
from pathlib import Path

import torch

from scripts.qwen_build_adaptive import load_adaptive_model
from src.prompt_builder import build_prompt
from src.schema_utils import get_schema
from src.qwen_generate import generate_sql
from src.qwen_evaluator import calculate_em,calculate_ex
from src.sql_util import clean_sql


# ============================================================
# STEP 1 - PROJECT CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATABASE_DIR = ROOT /"data/spider_data/spider_data/database"
RESULT_DIR = ROOT / "results" / "qwen"
RESULT_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = ROOT / "data" / "spider_data" / "spider_data"

EVALUATION_FILE = DATA_DIR / "evaluation_question.json"

CSV_PATH = RESULT_DIR / "adaptive_model_result.csv"

# Test only 3 questions first.
# After successful testing, change to 100.
LIMIT = 25

DEVICE = "cuda"


# ============================================================
# STEP 2 - CHECK CUDA
# ============================================================

if not torch.cuda.is_available():
    raise RuntimeError("CUDA GPU is not available!")

print("=" * 60)
print("DAY 9 - ADAPTIVE MODEL FULL EXPERIMENT")
print("=" * 60)

print("GPU:", torch.cuda.get_device_name(0))


# ============================================================
# STEP 3 - LOAD EVALUATION QUESTIONS
# ============================================================

print("\nLoading evaluation questions...")

if not EVALUATION_FILE.exists():
    raise FileNotFoundError(
        f"Evaluation file not found: {EVALUATION_FILE}"
    )

with open(EVALUATION_FILE, "r", encoding="utf-8") as f:
    questions = json.load(f)

if not isinstance(questions, list):
    raise ValueError(
        "Evaluation JSON must contain a list of questions."
    )

questions = questions[:LIMIT]

if not questions:
    raise ValueError("No evaluation questions found.")


# ============================================================
# STEP 4 - NORMALIZE QUESTION FIELDS
# ============================================================

def get_value(item, possible_keys):

    for key in possible_keys:
        if key in item and item[key] is not None:
            return item[key]

    raise KeyError(
        f"Could not find any of {possible_keys}. "
        f"Available keys: {list(item.keys())}"
    )


def prepare_question(item):

    question_id = get_value(
        item,
        ["ID", "question_id", "Question_ID", "id"]
    )

    question = get_value(
        item,
        ["Question", "question"]
    )

    db_id = get_value(
        item,
        ["DB_ID", "db_id"]
    )

    gold_sql = get_value(
        item,
        [
            "Expected_SQL",
            "reference_sql",
            "gold_sql",
            "query",
            "SQL",
            "expected_sql"
        ]
    )

    return {
        "question_id": str(question_id),
        "question": str(question),
        "db_id": str(db_id),
        "gold_sql": str(gold_sql)
    }


prepared_questions = [
    prepare_question(item) for item in questions
]

ids = [item["question_id"] for item in prepared_questions]

if len(ids) != len(set(ids)):
    raise ValueError("Duplicate question IDs found.")

print("Total questions:", len(prepared_questions))
print("Questions loaded successfully!")


# ============================================================
# STEP 5 - LOAD ADAPTIVE MIXED-PRECISION MODEL
# ============================================================

print("\nLoading QWEN adaptive model...")

model, tokenizer , metrics= load_adaptive_model()

model.eval()

print("\nAdaptive model loaded successfully!")


# ============================================================
# STEP 6 - CREATE RESULT COLUMNS
# ============================================================

fieldnames = [
    "question_id",
    "db_id",
    "question",
    "gold_sql",
    "generated_sql",
    "EM",
    "EX",
    "error_type",
    "latency",
    "peak_vram_mb"
]

results = []


# ============================================================
# STEP 7 - RUN EVALUATION
# ============================================================

with open(
    CSV_PATH,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()

    for i, item in enumerate(prepared_questions, start=1):

        question_id = item["question_id"]
        question = item["question"]
        db_id = item["db_id"]
        gold_sql = item["gold_sql"]

        print("\n" + "=" * 60)
        print(f"Question {i}/{len(prepared_questions)}")
        print("=" * 60)

        print("Question ID:", question_id)
        print("Database:", db_id)
        print("Question:", question)

        # ====================================================
        # STEP 8 - GET DATABASE SCHEMA
        # ====================================================

        db_path = DATABASE_DIR / db_id / f"{db_id}.sqlite"

        if not db_path.is_file():
            raise FileNotFoundError(f"Database not found: {db_path}")
        
        schema = get_schema(db_path)

        # ====================================================
        # STEP 9 - BUILD SQL PROMPT
        # ====================================================

        prompt = build_prompt(
            schema,
            question
        )

        print("\nDATABASE SCHEMA:")
        print(schema)

        print("\nFINAL PROMPT:")
        print(prompt)

        # ====================================================
        # STEP 10 - MEASURE GENERATION LATENCY
        # ====================================================

        torch.cuda.synchronize()

        torch.cuda.reset_peak_memory_stats()

        start_time = time.perf_counter()

        generated_sql = generate_sql(
            model,
            tokenizer,
            prompt
        )

        generated_sql=clean_sql(generated_sql)
        torch.cuda.synchronize()

        latency = time.perf_counter() - start_time

        peak_vram_mb = (
            torch.cuda.max_memory_allocated() / 1024**2
        )

        print("\nGenerated SQL:", generated_sql)
        print("Expected SQL:", gold_sql)

        # ====================================================
        # STEP 11 - EVALUATE EM AND EX
        # ====================================================

        evaluation_row = {
            "question_id": question_id,
            "db_id": db_id,
            "gold_sql": gold_sql,
            "generated_sql": generated_sql
        }

        em = calculate_em(gold_sql, generated_sql)
        ex = calculate_ex(db_path, gold_sql, generated_sql)
        error_type = "none" if ex == 1 else "incorrect_result"

        # ====================================================
        # STEP 12 - STORE QUESTION RESULT
        # ====================================================

        result = {
            "question_id": question_id,
            "db_id": db_id,
            "question": question,
            "gold_sql": gold_sql,
            "generated_sql": generated_sql,
            "EM": em,
            "EX": ex,
            "error_type": error_type,
            "latency": round(latency, 4),
            "peak_vram_mb": round(peak_vram_mb, 2)
        }

        results.append(result)

        writer.writerow(result)

        # Save immediately after every question
        f.flush()

        print("\nEvaluation Results:")
        print("EM:", em)
        print("EX:", ex)
        print("Error Type:", error_type)

        print(
            f"Latency: {latency:.2f} seconds"
        )

        print(
            f"Peak VRAM: {peak_vram_mb:.2f} MB"
        )

        print(f"Question {i} completed!")


# ============================================================
# STEP 13 - CALCULATE FINAL METRICS
# ============================================================

total_questions = len(results)

if total_questions == 0:
    raise RuntimeError("No evaluation results generated.")

total_em = sum(row["EM"] for row in results)

total_ex = sum(row["EX"] for row in results)

average_em = (
    total_em / total_questions
) * 100

average_ex = (
    total_ex / total_questions
) * 100

average_latency = (
    sum(row["latency"] for row in results)
    / total_questions
)

peak_vram = max(
    row["peak_vram_mb"] for row in results
)


# ============================================================
# STEP 14 - DISPLAY FINAL SUMMARY
# ============================================================

print("\n" + "=" * 60)
print("QWEN - FINAL EVALUATION RESULTS")
print("=" * 60)

print("Model: Adaptive Mixed INT4/INT8")

print("Total Questions:", total_questions)

print(
    f"Exact Match: {average_em:.2f}%"
)

print(
    f"Execution Accuracy: {average_ex:.2f}%"
)

print(
    f"Average Latency: {average_latency:.2f} seconds"
)

print(
    f"Peak VRAM: {peak_vram:.2f} MB"
)


# ============================================================
# STEP 15 - SAVE SUMMARY JSON
# ============================================================

summary = {
    "model": "Adaptive Mixed INT4/INT8",
    "total_questions": total_questions,
    "exact_match_percent": round(average_em, 2),
    "execution_accuracy_percent": round(average_ex, 2),
    "average_latency_seconds": round(
        average_latency, 4
    ),
    "peak_vram_mb": round(peak_vram, 2)
}

summary_path = RESULT_DIR / "adaptive_summary.json"

with open(
    summary_path,
    "w",
    encoding="utf-8"
) as f:
    json.dump(summary, f, indent=4)


print("\nResults saved successfully!")

print("Question Results:", CSV_PATH)
print("Summary:", summary_path)

print("\nQWEN ADAPTIVE EVALUATION COMPLETED!")
