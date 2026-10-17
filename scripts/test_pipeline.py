import json
import csv

from src.prompt_builder import build_prompt
from src.generate_sql import generate_Sql
from src.schema_utils import get_schema
from src.sql_util import clean_sql

SPIDER_FILE = "data/spider_data/spider_data/dev.json"

with open(SPIDER_FILE,"r",encoding="utf-8") as f:
    data=json.load(f)

result = []

for question_number,example in enumerate(data[:20],start=1):
    
    db_id = example["db_id"]
    question = example["question"]
    expected_sql = example["query"]

    db_path = f"data/spider_data/spider_data/database/{db_id}/{db_id}.sqlite"

    schema = get_schema(db_path)

    prompt = build_prompt(schema,question)


    generated_Sql = generate_Sql(prompt)
    generated_Sql = clean_sql(generated_Sql)

    result.append({
        "question_number":question_number,
        "db_id":db_id,
        "question":question,
        "schema":schema,
        "expected_sql":expected_sql,
        "generated_Sql":generated_Sql
    })

    print("\nQuestion Number : ",question_number)
    print("="*50)
    print("\nDatabase : ",db_id)

    print("\nQuestion : ",question)

    print("\nSchema : ",schema)

    print("\nExpected SQL : ",expected_sql)

    print("="*50)

    print("Generated SQL :")
    print(generated_Sql)

    print("="*50)

with open ("results/20_queries_results.csv","w",newline ="",encoding="utf-8") as file:
    fieldnames=["question_number","db_id","question","schema","expected_sql","generated_Sql"]

    writer = csv.DictWriter(file,fieldnames=fieldnames)

    writer.writeheader()

    writer.writerows(result)

    print("\nResults saved to results/20_queries_results.csv")

