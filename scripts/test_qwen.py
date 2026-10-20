import torch
from transformers import AutoTokenizer,AutoModelForCausalLM

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

print("Loading Model.....")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype =torch.float16,
    device_map = "auto"
)

print("Total layers : ",len(model.model.layers))
print("Devices : ",model.device)

messages = [
    {
        "role": "system",
        "content": "You generate SQLite SQL queries. Return only SQL."
    },
    {
        "role": "user",
        "content": (
            "Table: singer(Singer_ID, Name, Country, Age)\n"
            "Question: How many singers are there?"
        )
    }
]

inputs = tokenizer.apply_chat_template(
    messages,
    add_generation_prompt=True,
    tokenize=True,
    return_dict=True,
    return_tensors="pt"
).to(model.device)

with torch.inference_mode():
    outputs = model.generate(
        **inputs,
        max_new_tokens=100,
        do_sample=False,
        pad_token_id = tokenizer.eos_token_id
    )

generated_tokens = outputs[0][inputs["input_ids"].shape[-1]:]

sql = tokenizer.decode(
    generated_tokens,
    skip_special_tokens=True
)

print("Generated SQL : ",sql)