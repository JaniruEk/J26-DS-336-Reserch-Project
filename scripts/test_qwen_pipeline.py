from src.qwen_generate import generate_sql
from src.qwen_model_loader import load_qwen

model, tokenizer = load_qwen("fp16")

prompt = """
    Database schema:
    CREATE TABLE singer (
        Singer_ID INTEGER,
        Name TEXT,
        Country TEXT,
        Age INTEGER
    );

    Question: How many singers are there?
"""

sql = generate_sql(model, tokenizer, prompt)

print("Generated SQL:", sql)

