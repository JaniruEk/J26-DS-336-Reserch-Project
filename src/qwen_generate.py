import torch

def generate_sql(model,tokenizer,prompt):
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert SQLite SQL generator. "
                "Generate one SELECT query using the supplied "
                "database schema. Return only SQL."
            )
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    inputs = tokenizer.apply_chat_template(
        messages,
        tokenizer=True,
        add_generation_prompt = True,
        return_dict=True,
        return_tensors="pt"
    )

    device = model.get_input_embeddings().weight.device

    inputs = inputs.to(device)

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens = 100,
            do_sample =False,
            pad_token_id = tokenizer.eos_token_id
        )

    generated = output[0][inputs["input_ids"].shape[-1]:]

    sql = tokenizer.decode(generated,skip_special_tokens=True)

    return sql.strip()