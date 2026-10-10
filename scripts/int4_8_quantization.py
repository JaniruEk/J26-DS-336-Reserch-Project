
import json
import csv
import argparse
import os
import sqlite3
import time
from pathlib import Path

from src.prompt_builder import build_prompt
from src.schema_utils import get_schema
from src.sql_util import clean_sql

from src.model_loader import load_quantized_model
from src.quantizsed_generate import generated_quantized_sql


# =====================================
# STEP 1 - ARGUMENTS
# =====================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--precision",
    choices=["int8", "int4"],
    required=True
)

args = parser.parse_args()

precision = args.precision


# =====================================
# STEP 2 - FILE PATHS
# =====================================

QUESTION_PATH = (
    "data/spider_data/spider_data/evaluation_question.json"
)

DATABASE_DIR = Path(
    "data/spider_data/spider_data/database"
)

DEFAULT_DB_ID = "concert_singer"

RESULT_PATH = f"results/day4_{precision}_results.csv"


# =====================================
# STEP 3 - SQL EXECUTION FUNCTION
# =====================================

def execute_sql(sql, db_path):

    # Open the database in read-only mode.
    connection = sqlite3.connect(
        Path(db_path).resolve().as_uri() + "?mode=ro",
        uri=True
    )

    try:
        connection.execute("PRAGMA query_only = ON")

        # Stop queries that exceed 10 seconds.
        deadline = time.monotonic() + 10

        connection.set_progress_handler(
            lambda: int(time.monotonic() > deadline),
            1000
        )

        cursor = connection.execute(sql)
        result = cursor.fetchall()

        return True, result

    except Exception as e:
        return False, str(e)

    finally:
        connection.close()


# =====================================
# STEP 4 - SQL NORMALIZATION
# =====================================

def normalize_sql(sql):

    return "".join(
        sql.lower()
        .replace(";", "")
        .split()
    )


# =====================================
# STEP 5 - BASIC SQL SAFETY CHECK
# =====================================

def is_safe_sql(sql):

    sql = sql.strip().lower()

    return (
        sql.startswith("select ")
        or sql.startswith("select\n")
        or sql.startswith("with ")
        or sql.startswith("with\n")
    )


# =====================================
# STEP 6 - LOAD EVALUATION QUESTIONS
# =====================================

with open(
    QUESTION_PATH,
    "r",
    encoding="utf-8"
) as f:

    data = json.load(f)

print(f"\nLoaded {len(data)} evaluation questions")

if len(data) != 100:
    print("Warning: Evaluation dataset does not contain exactly 100 questions.")


# =====================================
# STEP 7 - LOAD QUANTIZED MODEL
# =====================================

model, tokenizer = load_quantized_model(precision)


# =====================================
# STEP 8 - WARM UP THE MODEL
# =====================================

print("\nWarming up the model...")

warmup_prompt = build_prompt(
    "Table: singer(singer_id, name)",
    "Show all singers"
)

generated_quantized_sql(
    model,
    tokenizer,
    warmup_prompt
)

print("Warm-up completed!")


# =====================================
# STEP 9 - PREPARE RESULTS
# =====================================

os.makedirs("results", exist_ok=True)

fieldnames = [
    "ID",
    "DB_ID",
    "Question",
    "Difficulty",
    "SQL_Type",
    "Expected_SQL",
    "Generated_SQL",
    "SQL_Exact_Match",
    "Execution_Correct",
    "Expected_Execution_Success",
    "Generated_Execution_Success",
    "Execution_Error",
    "Latency_Seconds",
    "Peak_VRAM_MB",
    "Precision"
]

results = []


# =====================================
# STEP 10 - EVALUATE 100 QUESTIONS
# =====================================

with open(
    RESULT_PATH,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()

    for question_number, example in enumerate(
        data[:100],
        start=1
    ):

        # Get question information
        question_id = example.get("id", question_number)

        difficulty = example.get("difficulty", "Unknown")
        sql_type = example.get("sql_type", "Unknown")

        question = example["question"]

        expected_sql = example.get(
            "expected_sql",
            example.get("query")
        )

        if expected_sql is None:
            raise KeyError(
                f"Missing expected_sql/query for question {question_id}"
            )

        db_id = example.get("db_id", DEFAULT_DB_ID)

        db_path = (
            DATABASE_DIR / db_id / f"{db_id}.sqlite"
        )

        if not db_path.exists():
            raise FileNotFoundError(
                f"Database not found: {db_path}"
            )

        # Get database schema
        schema = get_schema(str(db_path))

        # Build prompt
        prompt = build_prompt(
            schema,
            question
        )

        # Generate SQL using INT8 or INT4
        generated_sql, latency, peak_memory = (
            generated_quantized_sql(
                model,
                tokenizer,
                prompt
            )
        )

        # Clean generated SQL
        generated_sql = clean_sql(generated_sql)

        generated_sql = (
            generated_sql
            .replace("<|end|>", "")
            .replace("<|endoftext|>", "")
            .strip()
        )

        # =====================================
        # SQL EXACT MATCH
        # =====================================

        sql_exact_match = int(
            normalize_sql(generated_sql)
            ==
            normalize_sql(expected_sql)
        )

        # =====================================
        # EXECUTE EXPECTED SQL
        # =====================================

        expected_success, expected_result = execute_sql(
            expected_sql,
            db_path
        )

        # =====================================
        # EXECUTE GENERATED SQL
        # =====================================

        if is_safe_sql(generated_sql):

            generated_success, generated_result = execute_sql(
                generated_sql,
                db_path
            )

        else:
            generated_success = False
            generated_result = "Rejected by SQL safety check"

        # =====================================
        # EXECUTION CORRECTNESS
        # =====================================

        execution_correct = int(
            expected_success
            and generated_success
            and expected_result == generated_result
        )

        execution_error = ""

        if not expected_success:
            execution_error = (
                f"Reference error: {expected_result}"
            )

        elif not generated_success:
            execution_error = str(generated_result)

        # =====================================
        # SAVE INDIVIDUAL QUESTION RESULT
        # =====================================

        row = {
            "ID": question_id,
            "DB_ID": db_id,
            "Question": question,
            "Difficulty": difficulty,
            "SQL_Type": sql_type,
            "Expected_SQL": expected_sql,
            "Generated_SQL": generated_sql,
            "SQL_Exact_Match": sql_exact_match,
            "Execution_Correct": execution_correct,
            "Expected_Execution_Success": int(expected_success),
            "Generated_Execution_Success": int(generated_success),
            "Execution_Error": execution_error,
            "Latency_Seconds": round(latency, 4),
            "Peak_VRAM_MB": round(peak_memory, 2),
            "Precision": precision
        }

        results.append(row)

        writer.writerow(row)
        file.flush()

        # =====================================
        # DISPLAY QUESTION RESULTS
        # =====================================

        print("\n" + "=" * 60)
        print("Question Number:", question_number)
        print("Question ID:", question_id)
        print("Difficulty:", difficulty)
        print("SQL Type:", sql_type)
        print("Database:", db_id)

        print("\nQuestion:", question)
        print("\nExpected SQL:", expected_sql)
        print("\nGenerated SQL:", generated_sql)

        print("\nExpected Result:", expected_result)
        print("Generated Result:", generated_result)

        print("\nSQL Exact Match:", sql_exact_match)
        print("Execution Correct:", execution_correct)

        print("Latency:", round(latency, 4), "seconds")
        print("Peak GPU Memory:", round(peak_memory, 2), "MB")

        print("=" * 60)


# =====================================
# STEP 11 - CALCULATE FINAL METRICS
# =====================================

total_questions = len(results)

exact_match_count = sum(
    row["SQL_Exact_Match"]
    for row in results
)

execution_correct_count = sum(
    row["Execution_Correct"]
    for row in results
)

execution_success_count = sum(
    row["Generated_Execution_Success"]
    for row in results
)

reference_error_count = sum(
    1 for row in results
    if row["Expected_Execution_Success"] == 0
)

if total_questions == 0:
    raise ValueError("No evaluation questions processed.")

exact_match_accuracy = (
    exact_match_count / total_questions
) * 100

execution_accuracy = (
    execution_correct_count / total_questions
) * 100

execution_success_rate = (
    execution_success_count / total_questions
) * 100

avg_latency = sum(
    row["Latency_Seconds"]
    for row in results
) / total_questions

maximum_vram = max(
    row["Peak_VRAM_MB"]
    for row in results
)


# =====================================
# STEP 12 - PRINT FINAL SUMMARY
# =====================================

print("\n" + "=" * 60)
print(f"{precision.upper()} QUANTIZATION SUMMARY")
print("=" * 60)

print("Total Questions:", total_questions)

print(
    f"SQL Exact Match: {exact_match_accuracy:.2f}%"
)

print(
    f"Execution Accuracy: {execution_accuracy:.2f}%"
)

print(
    f"Execution Success Rate: {execution_success_rate:.2f}%"
)

print(
    f"Average Latency: {avg_latency:.4f} seconds"
)

print(
    f"Maximum Peak VRAM: {maximum_vram:.2f} MB"
)

print("Reference SQL Errors:", reference_error_count)

print("\nResults saved to:")
print(RESULT_PATH)
