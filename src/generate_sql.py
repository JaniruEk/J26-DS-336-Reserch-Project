import torch
from transformers import AutoTokenizer,AutoModelForCausalLM

MODEL_NAME ="microsoft/Phi-3-mini-4k-instruct"

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME
)

model =AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    device_map="auto",
    torch_dtype="auto"
)

def generate_Sql(prompt):
    message =[
        {
        "role":"user",
        "content":prompt
        }
    ]

    formatted_prompt = tokenizer.apply_chat_template(
        message,
        tokenize =False,
        add_generation_prompt =True
    )

    inputs =tokenizer(
        formatted_prompt,
        return_tensors= "pt"
    ).to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=100,
            do_sample=False
        )

    generate_tokens =outputs[0][inputs["input_ids"].shape[1]:]

    generated_text =tokenizer.decode(
        generate_tokens,
        skip_special_tokens=True
    )

    return generated_text.strip()