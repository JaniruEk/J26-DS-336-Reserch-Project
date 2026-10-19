import torch
import json
import time
import os
import csv
import sqlite3
import gc

from src.prompt_builder import build_prompt
from src.schema_utils import get_schema
from transformers import AutoTokenizer,AutoModelForCausalLM
from src.sql_util import clean_sql


QUESTION_PATH = "data/spider_data/spider_data/evaluation_question.json"
DB_PATH="data/spider_data/spider_data/database/concert_singer/concert_singer.sqlite"
RESULT_PATH = "results/baseline_results.csv"

with open(QUESTION_PATH,"r",encoding="utf-8") as f:
    questions = json.load(f)

print(f"Loaded {len(questions)} evalution questions")

# =============================
# SQL EXECUTION FUNCTION
# =============================
def execute_sql(sql):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(sql)
        result = cursor.fetchall()
        return True, result
    except Exception as e:
        return False, str (e)
    finally:
        conn.close()


# =======================
# SQL NORMALIZATION
# =======================
def normalize_sql(sql):
    return "".join(
        sql.lower()
        .replace(";","")
        .split()
    )


# ===============================================================
# SQL SAFETY CHECKING
#         prevent execute dangerous functions like "DELETE"
# ===============================================================
def is_safe_sql(sql):
    sql = sql.strip().lower()

    return (
        sql.startswith("select")
        or sql.startswith("with")
    )

schema = get_schema(DB_PATH)

# =================
# LOAD MODEL
# ==================
MODEL_NAME ="microsoft/Phi-3-mini-4k-instruct"

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME
)

model =AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    device_map="auto",
    torch_dtype="auto"
)

model_memory_bytes =sum(
    p.numel()*p.element_size()
    for p in model.parameters()
)

model_memory_mb = model_memory_bytes/(1024**2)

print(f"Model Parameter memory : {model_memory_mb:.2f}MB")

results = []

for item in questions[90:100]:
    question_id = item["id"]
    difficulty = item["difficulty"]
    sql_type = item["sql_type"]
    question=item["question"]
    expected_sql=item["expected_sql"]

    print("\n"+"="*20)
    print(f"Question ID : {question_id}")
    print("Difficulty :",difficulty)
    print(f"SQL Type : {sql_type}")
    print("Question :",question)
    print(f"Expected SQL : {expected_sql}")


    prompt = build_prompt(schema,question)

    messages =[
        {
            "role":"user",
            "content":prompt
        }
    ]

    formatted_prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(formatted_prompt,return_tensors="pt").to(model.device)

    torch.cuda.empty_cache()

    torch.cuda.reset_peak_memory_stats()

    torch.cuda.synchronize()
    start_time = time.perf_counter()

    with torch.no_grad():
        outputs =model.generate(
            **inputs,
            max_new_tokens=100,
            do_sample=False
        )

    torch.cuda.synchronize()
    end_time =time.perf_counter()
    latency =end_time-start_time

    peak_vram_mb = (
        torch.cuda.max_memory_allocated()/(1024**2)
    )

    generate_tokens =outputs[0][inputs["input_ids"].shape[1]:]

    generated_text =tokenizer.decode(
            generate_tokens,
            skip_special_tokens=True
        )

    generated_text =generated_text.strip()
    generated_Sql = clean_sql(generated_text)

    print(f"Generated : {generated_Sql}")

    sql_exact_match =int(
        normalize_sql(generated_Sql)
        ==
        normalize_sql(expected_sql)
    )


    expected_success,expected_result = execute_sql(expected_sql)

    if is_safe_sql (generated_Sql):
        generated_success,generated_result  = execute_sql(generated_Sql)

    else:
        generated_success=False
        generated_result='Unsafe SQL'


    execution_correct =int(
        expected_success 
        and generated_success
        and expected_result == generated_result
    )

    print(f"Ëxpected Result : {expected_result}")
    print(f"Generate Result : {generated_result}")
    print(f"SQL Exact Match : {sql_exact_match}")
    print(f"Execution Correct : {execution_correct}")
    print(f"Latency : {latency:.4f} seconds")
    print(f"Peak VRAM : {peak_vram_mb:.2f} MB")

    results.append({
        "ID": question_id,
        "Question": question,
        "Difficulty": difficulty,
        "SQL_Type": sql_type,
        "Expected_SQL": expected_sql,
        "Generated_SQL": generated_Sql,
        "SQL_Exact_Match": sql_exact_match,
        "Execution_Correct": execution_correct,
        "Latency_Seconds": round(latency, 4),
        "Peak_VRAM_MB": round(peak_vram_mb, 2)
    })

    del inputs
    del outputs
    del generate_tokens

    gc.collect()
    torch.cuda.empty_cache()


os.makedirs(
    "result",
    exist_ok=True
)

fieldnames=[
    "ID",
    "Question",
    "Difficulty",
    "SQL_Type",
    "Expected_SQL",
    "Generated_SQL",
    "SQL_Exact_Match",
    "Execution_Correct",
    "Latency_Seconds",
    "Peak_VRAM_MB"
]

with open(RESULT_PATH,"a",newline="",encoding="utf-8") as f:
    writer = csv.DictWriter(f,fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)


print("\nBaseline results saved to:")
print(RESULT_PATH)