import torch
from transformers import AutoTokenizer,AutoModelForCausalLM,BitsAndBytesConfig

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

def load_qwen(precision="fp16"):
    tokenizer =AutoTokenizer.from_pretrained(MODEL_NAME)

    kwargs = {
        "device_map" :"auto",
        "torch_dtype":torch.float16
    }

    if precision == "int8":
        kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)

    elif precision == "int4":
        kwargs["quantization_config"] =BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16
        )
    elif precision != "fp16":
        raise ValueError("Unknown precision")

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        **kwargs
    )

    model.eval()

    return model,tokenizer