
import sys
import json
import csv
import time
import torch

from pathlib import Path

from src.qwen_model_loader import load_qwen
from src.qwen_generate import generate_sql
from src.schema_utils import get_schema
from src.prompt_builder import build_prompt
from src.sql_util import clean_sql
from src.qwen_evaluator import calculate_em, calculate_ex

ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "data/spider_data/spider_data/evaluation_question.json"

DATABASE_DIR = ROOT / "data/spider_data/spider_data/database"

OUTPUT_DIR = ROOT / "results/qwen"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

QUESTION_LIMIT = 100

with open(INPUT, "r", encoding="utf-8") as f:
    questions = json.load(f)

precision = sys.argv[1].lower()

if precision not in ("fp16", "int8", "int4"):
    raise ValueError("Precision must be fp16, int8 or int4")

model, tokenizer = load_qwen(precision)

results = []

for index, item in enumerate(questions[:QUESTION_LIMIT], 1):

    question_id = item["ID"]
    question = item["Question"]
    db_id = item["DB_ID"]
    expected_sql = item["Expected_SQL"]

    db_path = DATABASE_DIR / db_id / f"{db_id}.sqlite"

    schema = get_schema(db_path)

    prompt = build_prompt(schema, question)

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()

    start = time.perf_counter()

    generated_sql = generate_sql(
        model, tokenizer, prompt
    )

    if torch.cuda.is_available():
        torch.cuda.synchronize()

    latency = time.perf_counter() - start

    peak_vram_mb = (
        torch.cuda.max_memory_allocated() / 1024**2
        if torch.cuda.is_available() else 0
    )

    generated_sql = clean_sql(generated_sql)

    em = calculate_em(expected_sql, generated_sql)

    ex = calculate_ex(
        db_path,
        expected_sql,
        generated_sql
    )

    results.append({
    "question_id": question_id,
    "db_id": db_id,
    "question": question,
    "gold_sql": expected_sql,
    "generated_sql": generated_sql,
    "EM": em,
    "EX": ex,
    "latency": round(latency, 4),
    "peak_vram_mb": round(peak_vram_mb, 2)
})

    print(
    f"[{index}/{QUESTION_LIMIT}] "
    f"Question {question_id} | "
    f"EM: {em} | "
    f"EX: {ex} | "
    f"Latency: {latency:.2f}s"
    )

output_file = OUTPUT_DIR / f"{precision}_results.csv"

with open(output_file, "w", newline="", encoding="utf-8") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=results[0].keys()
    )

    writer.writeheader()
    writer.writerows(results)

print(f"\nResults saved to: {output_file}")

total = len(results)

avg_em = sum(r["EM"] for r in results) / total
avg_ex = sum(r["EX"] for r in results) / total
avg_latency = sum(r["latency"] for r in results) / total

print("\n========== QWEN RESULTS ==========")
print(f"Precision: {precision}")
print(f"Total Questions: {total}")
print(f"EM: {avg_em * 100:.2f}%")
print(f"EX: {avg_ex * 100:.2f}%")
print(f"Average Latency: {avg_latency:.2f}s")
print("==================================")
