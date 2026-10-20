
import gc
import json
import time
import re
from pathlib import Path

import pandas as pd
import torch
import torch.nn as nn
import bitsandbytes as bnb

from transformers import AutoModelForCausalLM, AutoTokenizer


# ============================================================
# STEP 1 - PROJECT CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "results" / "day7" / "precision_allocation.csv"
OUTPUT_DIR = ROOT / "results" / "day8"

MODEL_ID = "microsoft/Phi-3-mini-4k-instruct"

DEVICE = "cuda"
TOTAL_LAYERS = 32

# Must match Day 4 configuration
INT4_TYPE = "nf4"
INT8_THRESHOLD = 6.0

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# NEW - REUSABLE ADAPTIVE MODEL LOADER
# ============================================================

def load_adaptive_model():

    # ========================================================
    # STEP 2 - CHECK CUDA
    # ========================================================

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is not available!")

    print("=" * 60)
    print("DAY 8 - ADAPTIVE MIXED-PRECISION MODEL")
    print("=" * 60)

    print("GPU:", torch.cuda.get_device_name(0))

    free_memory, total_memory = torch.cuda.mem_get_info()

    print(
        f"Free GPU memory: {free_memory / 1024**2:.2f} MB"
    )

    print(
        f"Total GPU memory: {total_memory / 1024**2:.2f} MB"
    )

    # ========================================================
    # STEP 3 - LOAD AND VALIDATE DAY 7 ALLOCATION
    # ========================================================

    print("\nLoading Day 7 precision allocation...")

    if not INPUT.exists():
        raise FileNotFoundError(
            f"Allocation file not found: {INPUT}"
        )

    df = pd.read_csv(INPUT)

    required_columns = {"layer", "precision"}

    if not required_columns.issubset(df.columns):
        raise ValueError(
            f"Expected columns: {required_columns}. "
            f"Found: {list(df.columns)}"
        )

    df["layer"] = df["layer"].astype(int)

    df["precision"] = (
        df["precision"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    if len(df) != TOTAL_LAYERS:
        raise ValueError("Expected exactly 32 layers")

    if df["layer"].duplicated().any():
        raise ValueError("Duplicate layer IDs found")

    if set(df["layer"]) != set(range(TOTAL_LAYERS)):
        raise ValueError("Layer IDs must be 0 to 31")

    if not df["precision"].isin(["INT4", "INT8"]).all():
        raise ValueError("Only INT4 and INT8 are allowed")

    precision_map = dict(
        zip(df["layer"], df["precision"])
    )

    print("\nPrecision Allocation:")

    for layer_id, precision in sorted(precision_map.items()):
        print(f"Layer {layer_id:02d} -> {precision}")

    print("\nAllocation Summary:")
    print(df["precision"].value_counts())

    int4_layers = sum(
        1 for p in precision_map.values()
        if p == "INT4"
    )

    int8_layers = sum(
        1 for p in precision_map.values()
        if p == "INT8"
    )

    print("Total INT4 layers:", int4_layers)
    print("Total INT8 layers:", int8_layers)

    # ========================================================
    # STEP 4 - FUNCTION TO QUANTIZE A LINEAR MODULE
    # ========================================================

    def convert_linear_module(original, bits):
        """
        Convert an FP16 linear module into
        bitsandbytes INT4 or INT8.
        """

        if not isinstance(original, nn.Linear):
            raise TypeError(
                f"Expected nn.Linear, got {type(original)}"
            )

        in_features = original.in_features
        out_features = original.out_features
        has_bias = original.bias is not None

        if bits == 4:

            quantized = bnb.nn.Linear4bit(
                in_features,
                out_features,
                bias=has_bias,
                compute_dtype=torch.float16,
                quant_type=INT4_TYPE,
                compress_statistics=True,
            )

        elif bits == 8:

            quantized = bnb.nn.Linear8bitLt(
                in_features,
                out_features,
                bias=has_bias,
                has_fp16_weights=False,
                threshold=INT8_THRESHOLD,
            )

        else:
            raise ValueError(
                f"Unsupported precision: {bits}"
            )

        # Prepare FP16 module
        quantized = quantized.half()

        # Copy pretrained weights
        quantized.load_state_dict(
            original.state_dict()
        )

        # Moving to CUDA performs quantization
        quantized = quantized.to(DEVICE)

        quantized.requires_grad_(False)

        # Verify INT4
        if bits == 4:
            if quantized.weight.quant_state is None:
                raise RuntimeError(
                    "INT4 quantization failed"
                )

        # Verify INT8
        elif bits == 8:
            if quantized.weight.dtype != torch.int8:
                raise RuntimeError(
                    "INT8 quantization failed"
                )

        return quantized

    # ========================================================
    # STEP 5 - LOAD ORIGINAL PHI-3 MODEL ON CPU
    # ========================================================

    print("\nLoading original Phi-3 Mini on CPU...")

    start_time = time.time()

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        dtype=torch.float16,
        low_cpu_mem_usage=True,
        trust_remote_code=False,
        attn_implementation="eager",
    )

    model.eval()

    load_time = time.time() - start_time

    print("\nModel loaded successfully!")
    print("Loading time:", round(load_time, 2), "seconds")

    print(
        "Number of transformer layers:",
        len(model.model.layers)
    )

    if len(model.model.layers) != TOTAL_LAYERS:
        raise ValueError(
            "Unexpected number of transformer layers"
        )

    for parameter in model.parameters():
        if parameter.device.type != "cpu":
            raise RuntimeError(
                "Original model must be loaded on CPU"
            )

    # ========================================================
    # STEP 6 - CONVERT THE 32 TRANSFORMER LAYERS
    # ========================================================

    print("\nStarting adaptive mixed-precision conversion...")

    module_names = [
        ("self_attn", "qkv_proj"),
        ("self_attn", "o_proj"),
        ("mlp", "gate_up_proj"),
        ("mlp", "down_proj"),
    ]

    conversion_report = []

    conversion_start = time.time()

    torch.cuda.reset_peak_memory_stats()

    for layer_id in range(TOTAL_LAYERS):

        precision = precision_map[layer_id]

        bits = 8 if precision == "INT8" else 4

        layer = model.model.layers[layer_id]

        print(
            f"\nConverting Layer {layer_id:02d} -> {precision}",
            flush=True
        )

        for parent_name, module_name in module_names:

            parent_module = getattr(
                layer,
                parent_name
            )

            original = getattr(
                parent_module,
                module_name
            )

            quantized = convert_linear_module(
                original,
                bits
            )

            # Replace original module
            setattr(
                parent_module,
                module_name,
                quantized
            )

            conversion_report.append({
                "layer": layer_id,
                "module": f"{parent_name}.{module_name}",
                "precision": precision,
                "weight_dtype": str(quantized.weight.dtype),
                "module_type": type(quantized).__name__,
            })

            del original, quantized

        # Move normalization modules to GPU
        layer.input_layernorm.to(DEVICE)
        layer.post_attention_layernorm.to(DEVICE)

        gc.collect()

        allocated = (
            torch.cuda.memory_allocated() / 1024**2
        )

        print(
            f"Layer {layer_id:02d} converted! "
            f"GPU memory: {allocated:.2f} MB",
            flush=True
        )

    conversion_time = time.time() - conversion_start

    print("\nAll 32 transformer layers converted!")

    print(
        f"Conversion time: {conversion_time:.2f} seconds"
    )

    # ========================================================
    # STEP 7 - MOVE REMAINING MODULES TO GPU
    # ========================================================

    print("\nMoving remaining modules to GPU...")

    model.model.embed_tokens.to(DEVICE)
    model.model.norm.to(DEVICE)
    model.lm_head.to(DEVICE)

    if hasattr(model.model, "rotary_emb"):
        if model.model.rotary_emb is not None:
            model.model.rotary_emb.to(DEVICE)

    model.eval()

    cpu_parameters = [
        name
        for name, parameter in model.named_parameters()
        if parameter.device.type != "cuda"
    ]

    if cpu_parameters:
        raise RuntimeError(
            "Some parameters are still on CPU: "
            + str(cpu_parameters[:10])
        )

    print("Remaining modules moved successfully!")

    # ========================================================
    # STEP 8 - VERIFY REAL QUANTIZATION
    # ========================================================

    print("\nVerifying quantized modules...")

    count_4bit = 0
    count_8bit = 0

    for module in model.modules():

        if isinstance(module, bnb.nn.Linear4bit):

            if module.weight.quant_state is None:
                raise RuntimeError(
                    "Found unquantized INT4 module"
                )

            count_4bit += 1

        elif isinstance(module, bnb.nn.Linear8bitLt):

            if module.weight.dtype != torch.int8:
                raise RuntimeError(
                    "Found unquantized INT8 module"
                )

            count_8bit += 1

    expected_4bit = int4_layers * len(module_names)
    expected_8bit = int8_layers * len(module_names)

    if count_4bit != expected_4bit:
        raise RuntimeError(
            f"INT4 module mismatch: "
            f"{count_4bit} vs {expected_4bit}"
        )

    if count_8bit != expected_8bit:
        raise RuntimeError(
            f"INT8 module mismatch: "
            f"{count_8bit} vs {expected_8bit}"
        )

    print("\nQuantization verification successful!")

    print("INT4 layers:", int4_layers)
    print("INT8 layers:", int8_layers)

    print("INT4 linear modules:", count_4bit)
    print("INT8 linear modules:", count_8bit)

    model_memory_mb = (
        torch.cuda.memory_allocated() / 1024**2
    )

    conversion_peak_mb = (
        torch.cuda.max_memory_allocated() / 1024**2
    )

    print(
        f"Allocated GPU memory: {model_memory_mb:.2f} MB"
    )

    print(
        f"Peak conversion GPU memory: "
        f"{conversion_peak_mb:.2f} MB"
    )

    # ========================================================
    # NEW - STORE METRICS FOR DAY 8 TEST
    # ========================================================

    model._day8_metrics = {
        "int4_layers": int4_layers,
        "int8_layers": int8_layers,
        "count_4bit": count_4bit,
        "count_8bit": count_8bit,
        "conversion_time": conversion_time,
        "model_memory_mb": model_memory_mb,
        "conversion_peak_mb": conversion_peak_mb,
        "conversion_report": conversion_report,
        "precision_map": precision_map,
    }

    # ========================================================
    # NEW - RETURN MODEL FOR DAY 9
    # ========================================================

    return model, tokenizer


# ============================================================
# ORIGINAL DAY 8 TEST
# Runs only when executing this file directly
# ============================================================

if __name__ == "__main__":

    model, tokenizer = load_adaptive_model()

    metrics = model._day8_metrics

    int4_layers = metrics["int4_layers"]
    int8_layers = metrics["int8_layers"]

    count_4bit = metrics["count_4bit"]
    count_8bit = metrics["count_8bit"]

    conversion_time = metrics["conversion_time"]
    model_memory_mb = metrics["model_memory_mb"]
    conversion_peak_mb = metrics["conversion_peak_mb"]

    conversion_report = metrics["conversion_report"]
    precision_map = metrics["precision_map"]

    # ========================================================
    # STEP 9 - TEST SQL GENERATION
    # ========================================================

    print("\nTesting mixed-precision SQL generation...")

    question = "How many singers are there?"

    schema = """
    CREATE TABLE singer (
        Singer_ID INTEGER,
        Name TEXT,
        Age INTEGER
    );
    """

    prompt = f"""You are a Text-to-SQL assistant.

    Given the database schema and question,
    generate only the SQL query.

    Schema:
    {schema}

    Question:
    {question}

    SQL:
    """

    inputs = tokenizer(
        prompt,
        return_tensors="pt"
    ).to(DEVICE)

    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()

    start = time.perf_counter()

    with torch.inference_mode():

        outputs = model.generate(
            **inputs,
            max_new_tokens=64,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
            use_cache=True,
        )

    torch.cuda.synchronize()

    latency = time.perf_counter() - start

    # Decode new tokens only
    input_length = inputs["input_ids"].shape[1]

    generated_tokens = outputs[0][input_length:]

    generated_text = tokenizer.decode(
        generated_tokens,
        skip_special_tokens=True
    ).strip()

    # Extract the SQL statement
    match = re.search(
        r"\bSELECT\b[\s\S]*?;",
        generated_text,
        flags=re.IGNORECASE
    )

    if match:
        generated_sql = match.group(0).strip()
    else:
        generated_sql = generated_text.strip()

    print("Extracted SQL:", generated_sql)

    print("\n" + "=" * 60)
    print("SQL GENERATION RESULT")
    print("=" * 60)

    print("QUESTION:", question)
    print("GENERATED SQL:", generated_sql)

    print(f"Latency: {latency:.2f} seconds")

    inference_peak_mb = (
        torch.cuda.max_memory_allocated() / 1024**2
    )

    print(
        f"Peak inference GPU memory: "
        f"{inference_peak_mb:.2f} MB"
    )

    # ========================================================
    # STEP 10 - SAVE DAY 8 RESULTS
    # ========================================================

    print("\nSaving Day 8 results...")

    report_df = pd.DataFrame(conversion_report)

    report_df.to_csv(
        OUTPUT_DIR / "module_quantization_report.csv",
        index=False
    )

    config = {
        "model": MODEL_ID,
        "method": "sensitivity_based_mixed_precision",
        "total_layers": TOTAL_LAYERS,
        "backend": "bitsandbytes",
        "int4_type": INT4_TYPE,
        "int8_threshold": INT8_THRESHOLD,
        "precision_allocation": {
            str(layer): precision
            for layer, precision in precision_map.items()
        },
        "int4_layer_count": int4_layers,
        "int8_layer_count": int8_layers,
        "int4_module_count": count_4bit,
        "int8_module_count": count_8bit,
    }

    with open(
        OUTPUT_DIR / "mixed_precision_config.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(config, f, indent=4)

    results = {
        "question": question,
        "generated_sql": generated_sql,
        "latency_seconds": round(latency, 4),
        "model_gpu_allocated_mb": round(model_memory_mb, 2),
        "conversion_peak_vram_mb": round(conversion_peak_mb, 2),
        "inference_peak_vram_mb": round(inference_peak_mb, 2),
        "conversion_time_seconds": round(conversion_time, 2),
    }

    with open(
        OUTPUT_DIR / "smoke_test_results.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(results, f, indent=4)

    # ========================================================
    # STEP 11 - FINAL SUMMARY
    # ========================================================

    print("\n" + "=" * 60)
    print("DAY 8 - FINAL SUMMARY")
    print("=" * 60)

    print("Model:", MODEL_ID)
    print("Total layers:", TOTAL_LAYERS)

    print("INT4 layers:", int4_layers)
    print("INT8 layers:", int8_layers)

    print("INT4 modules:", count_4bit)
    print("INT8 modules:", count_8bit)

    print(f"Conversion time: {conversion_time:.2f} s")
    print(f"SQL latency: {latency:.2f} s")

    print(
        f"Peak inference VRAM: "
        f"{inference_peak_mb:.2f} MB"
    )

    print("Generated SQL:", generated_sql)

    print("\nResults saved to:", OUTPUT_DIR)
    print("\nDAY 8 COMPLETED SUCCESSFULLY!")
