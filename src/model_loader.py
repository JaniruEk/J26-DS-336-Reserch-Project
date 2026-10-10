import torch
from transformers import AutoModelForCausalLM,BitsAndBytesConfig,AutoTokenizer

MODEL_ID = "microsoft/Phi-3-mini-4k-instruct"

def load_quantized_model(precision='int8'):
    if precision =="int8":
        config = BitsAndBytesConfig(
            load_in_8bit=True
        )
    elif precision == "int4":
        config =BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=False
        )
    else:
        raise ValueError(
            "Precision must be int8 or int4"
        )

    print(f"Loading {precision} model...")

    model =AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=config,
        device_map={"":0},
        torch_dtype=torch.float16
    )

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID
    )

    model.eval()

    print(f"{precision} model loaded successfully")

    return model,tokenizer