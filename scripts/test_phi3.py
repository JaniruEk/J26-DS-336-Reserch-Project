import torch
from transformers import AutoModelForCausalLM,AutoTokenizer
import time

MODEL_NAME = "microsoft/Phi-3-mini-4k-instruct"

print("Loading tokenizer...........")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

print("Tokenizer loaded successfullly.............")
print("Loading Phi-3 Mini.............")

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    dtype=torch.float16,
    device_map="auto",
    attn_implementation="eager"
)

print("Model loaded successfullly.............")

print("Model devices : ",model.device)
print("Model dtype : ",model.dtype)

if torch.cuda.is_available():
    print("VRAM allocated : ",round(torch.cuda.memory_allocated()/1024**3,2),"GB")


messages =[
    {
        "role":"user",
        "content":"""
        You are a Text-to-SQL assitant.

        Databse Schema:

        Employee(
            emp_id Integer,
            name text,
            department text,
            salary real
        )

        convert the following question into SQL.

        Question: 
                What is the total salry of employees in each departmnet?

        Return only SQL.

        """
    }
]

prompt = tokenizer.apply_chat_template(
    messages,
    tokenize = False,
    add_generation_prompt =True
)


inputs = tokenizer(
    prompt,
    return_tensors="pt"
)

inputs = {
    key: value.to(model.device)
    for key, value in inputs.items()
}

# ---------------------------------------------
# REST PEAK WRAM BEFORE GENRATION
# ----------------------------------------------

if torch.cuda.is_available():
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()


# -----------------------------------------------
# START TIME
# -----------------------------------------------
torch.cuda.synchronize()
start_time=time.perf_counter()



# ----------------------------------------------
# GENERATE SQL
# ----------------------------------------------

with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=100,
        do_sample=False
    )



# ------------------------------------------------
# INFERENCE_TIME = END_TIME-START_TIME
# -------------------------------------------------
torch.cuda.synchronize()
end_time = time.perf_counter()

inference_time = end_time - start_time
print("Inference Time : ",round(inference_time,2),"Seconds")



# ------------------------------------------------
# MEASURE PEAK VRAM AFTER GENERATION
# ------------------------------------------------

if torch.cuda.is_available():
    peak_vram =torch.cuda.max_memory_allocated()/1024**3
    print("-"*70)
    print("Peak VRAM during generation :",round(peak_vram,2),"GB")
    print("-"*70)


generated = outputs[0][inputs["input_ids"].shape[-1]:]

sql = tokenizer.decode(
    generated,
    skip_special_tokens =True
)

print("Genrated SQL: ")
print(sql)
