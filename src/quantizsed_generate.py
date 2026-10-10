import time
import torch

def generated_quantized_sql(model,tokenizer,prompt):
    messages =[
        {
            "role":"user",
            "content":prompt
        }
    ]

    formatted_promt =tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs =tokenizer(
        formatted_promt,
        return_tensors ="pt"
    ).to("cuda:0")

    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()

    start_time = time.perf_counter()

    with torch.inference_mode():
        outputs =model.generate(
            **inputs,
            max_new_tokens=128,
            do_sample=False,
            pad_token_id =tokenizer.eos_token_id
        )

    torch.cuda.synchronize()

    latency = time.perf_counter()-start_time

    input_length =inputs["input_ids"].shape[1]

    generated_tokens =outputs[0][input_length:]

    generated_sql =tokenizer.decode(
        generated_tokens,
        skip_special_token=True
    )

    peak_memory =(
        torch.cuda.max_memory_allocated()/(1024**2)
    )

    return generated_sql,latency,peak_memory