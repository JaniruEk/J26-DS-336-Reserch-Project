
import gc
import re
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import torch

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)


# ============================================================
# STEP 1 - PROJECT CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.prompt_builder import build_prompt
from src.sql_util import clean_sql
from scripts.quantizayion_demo_adaptive_adapter import load_adaptive


MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"

MODEL_TYPES = [
    "FP16",
    "INT8",
    "INT4",
    "Adaptive",
]


# ============================================================
# STEP 2 - STREAMLIT CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Adaptive Quantization Demo",
    layout="wide"
)

st.title("Adaptive Mixed-Precision Quantization")

st.subheader("Live Text-to-SQL Model Comparison")

st.write(
    "Compare FP16, INT8, INT4 and Adaptive models "
    "using SQL accuracy, inference time and GPU memory."
)

if torch.cuda.is_available():
    st.success(
        f"GPU: {torch.cuda.get_device_name(0)}"
    )
else:
    st.warning(
        "CUDA is not available. Quantized models "
        "may not run in this environment."
    )


# ============================================================
# STEP 3 - LOAD MODELS
# ============================================================

def load_model(model_type):

    if model_type == "Adaptive":
        return load_adaptive(MODEL_ID)

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID
    )

    kwargs = {
        "device_map": "auto",
        "dtype": torch.float16,
        "low_cpu_mem_usage": True,
    }

    if model_type == "INT8":

        kwargs["quantization_config"] = (
            BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_threshold=6.0,
            )
        )

    elif model_type == "INT4":

        kwargs["quantization_config"] = (
            BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
        )

    elif model_type != "FP16":
        raise ValueError(
            f"Unsupported model type: {model_type}"
        )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        **kwargs
    )

    model.eval()

    return model, tokenizer


# ============================================================
# STEP 4 - GENERATE SQL
# ============================================================

def generate_sql_live(
    model,
    tokenizer,
    prompt,
    max_new_tokens
):

    inputs = tokenizer(
        prompt,
        return_tensors="pt"
    )

    # Use the device of the embedding layer.
    # This also supports models using device_map="auto".
    device = model.get_input_embeddings().weight.device

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    try:
        with torch.inference_mode():

            output = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
                use_cache=True
            )

        input_length = inputs["input_ids"].shape[1]

        generated_tokens = output[0][input_length:]

        generated_text = tokenizer.decode(
            generated_tokens,
            skip_special_tokens=True
        )

        return clean_sql(generated_text)

    finally:
        if "output" in locals():
            del output

        del inputs


# ============================================================
# STEP 5 - EVALUATE EACH MODEL
# ============================================================

def evaluate_model(
    model_type,
    schema,
    question,
    max_new_tokens
):

    model = None
    tokenizer = None

    result = {
        "Model": model_type,
        "Generated SQL": "",
        "Inference Time (s)": None,
        "Peak GPU Memory (MB)": None,
        "EX": None,
        "EM": None,
        "Error": "",
    }

    try:

        # Clear unused GPU memory before loading
        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # --------------------------------------------
        # Load model
        # --------------------------------------------

        model, tokenizer = load_model(model_type)

        # Use the same research prompt builder
        prompt = build_prompt(
            schema,
            question
        )

        # --------------------------------------------
        # Reset memory statistics
        # --------------------------------------------

        if torch.cuda.is_available():

            torch.cuda.synchronize()

            torch.cuda.reset_peak_memory_stats()

        # --------------------------------------------
        # Start inference timer
        # --------------------------------------------

        start_time = time.perf_counter()

        generated_sql = generate_sql_live(
            model,
            tokenizer,
            prompt,
            max_new_tokens
        )

        if torch.cuda.is_available():
            torch.cuda.synchronize()

        end_time = time.perf_counter()

        # --------------------------------------------
        # Save SQL and time
        # --------------------------------------------

        result["Generated SQL"] = generated_sql

        result["Inference Time (s)"] = round(
            end_time - start_time,
            3
        )

        # --------------------------------------------
        # Measure peak GPU memory
        # --------------------------------------------

        if torch.cuda.is_available():

            peak_memory = (
                torch.cuda.max_memory_allocated()
                / (1024 ** 2)
            )

            result["Peak GPU Memory (MB)"] = round(
                peak_memory,
                2
            )

    except Exception as error:

        result["Error"] = (
            f"{type(error).__name__}: {error}"
        )

    finally:

        # Unload the current model
        # before loading the next model
        del model
        del tokenizer

        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    return result


# ============================================================
# STEP 6 - EXECUTE SQL
# ============================================================

def execute_sql(database_path, sql):

    db_file = Path(database_path).resolve()

    if not db_file.is_file():
        raise FileNotFoundError(
            f"Database not found: {db_file}"
        )

    sql = sql.strip()

    if not re.match(
        r"^(SELECT|WITH)\b",
        sql,
        flags=re.IGNORECASE
    ):
        raise ValueError(
            "Only SELECT or WITH queries are allowed"
        )

    # Open SQLite database in read-only mode
    database_uri = db_file.as_uri() + "?mode=ro"

    with sqlite3.connect(
        database_uri,
        uri=True,
        timeout=5
    ) as connection:

        connection.execute("PRAGMA query_only=ON")

        deadline = time.monotonic() + 5

        connection.set_progress_handler(
            lambda: int(time.monotonic() > deadline),
            1000
        )

        cursor = connection.execute(sql)

        rows = cursor.fetchall()

    # Order-insensitive result comparison
    return sorted(
        tuple(repr(value) for value in row)
        for row in rows
    )


# ============================================================
# STEP 7 - EXACT MATCH AND EXECUTION ACCURACY
# ============================================================

def normalize_sql(sql):

    sql = sql.strip().rstrip(";")

    sql = re.sub(
        r"\s+",
        " ",
        sql
    )

    return sql.lower()


def calculate_accuracy(
    generated_sql,
    gold_sql,
    database_path
):

    # Simplified normalized exact match
    em = int(
        normalize_sql(generated_sql)
        ==
        normalize_sql(gold_sql)
    )

    # Validate the reference SQL first
    gold_result = execute_sql(
        database_path,
        gold_sql
    )

    try:

        predicted_result = execute_sql(
            database_path,
            generated_sql
        )

        ex = int(
            predicted_result == gold_result
        )

        error = ""

    except Exception as error_obj:

        # Invalid generated SQL receives EX=0
        ex = 0

        error = (
            "Generated SQL execution failed: "
            + str(error_obj)
        )

    return em, ex, error


# ============================================================
# STEP 8 - USER INPUT
# ============================================================

st.divider()

st.header("SQL Query Input")

question = st.text_input(
    "Enter Natural Language Question",
    value="How many singers are there?"
)

schema = st.text_area(
    "Database Schema",
    value="""CREATE TABLE singer (
    Singer_ID INTEGER,
    Name TEXT,
    Country TEXT,
    Age INTEGER
);""",
    height=160
)

database_path = st.text_input(
    "SQLite Database Path",
    value=str(
        ROOT
        / "data"
        / "spider_data"
        / "spider_data"
        / "database"
        / "concert_singer"
        / "concert_singer.sqlite"
    )
)

gold_sql = st.text_input(
    "Gold SQL (Reference SQL)",
    value="SELECT COUNT(*) FROM singer;"
)

max_new_tokens = st.slider(
    "Maximum New Tokens",
    min_value=32,
    max_value=256,
    value=128,
    step=16
)


# ============================================================
# STEP 9 - RUN FOUR MODELS SEQUENTIALLY
# ============================================================

st.divider()

if st.button(
    "Run All Four Models",
    type="primary",
    use_container_width=True
):

    if not question.strip():
        st.error("Please enter a question")
        st.stop()

    if not schema.strip():
        st.error("Please enter a database schema")
        st.stop()

    results = []

    progress = st.progress(0)

    status = st.empty()

    for index, model_type in enumerate(MODEL_TYPES):

        status.info(
            f"Running {model_type} model..."
        )

        result = evaluate_model(
            model_type,
            schema,
            question,
            max_new_tokens
        )

        # Calculate accuracy only if reference
        # SQL and database path are provided
        if (
            not result["Error"]
            and gold_sql.strip()
            and database_path.strip()
        ):

            try:

                em, ex, sql_error = calculate_accuracy(
                    result["Generated SQL"],
                    gold_sql,
                    database_path
                )

                result["EM"] = em
                result["EX"] = ex

                if sql_error:
                    result["Error"] = sql_error

            except Exception as error:

                result["Error"] = (
                    "Accuracy evaluation failed: "
                    + str(error)
                )

        results.append(result)

        progress.progress(
            (index + 1) / len(MODEL_TYPES)
        )

    status.success(
        "Four-model comparison completed. "
        "Check individual results for errors."
    )

    st.session_state["comparison_results"] = results


# ============================================================
# STEP 10 - DISPLAY COMPARISON
# ============================================================

if "comparison_results" in st.session_state:

    results = st.session_state[
        "comparison_results"
    ]

    df = pd.DataFrame(results)

    st.divider()

    st.header("Live Quantization Comparison")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # SQL output for individual models
    # --------------------------------------------------------

    st.subheader("Generated SQL by Model")

    cols = st.columns(2)

    for index, result in enumerate(results):

        with cols[index % 2]:

            st.markdown(
                f"### {result['Model']}"
            )

            if result["Generated SQL"]:

                st.code(
                    result["Generated SQL"],
                    language="sql"
                )

            else:

                st.warning(
                    "SQL not generated"
                )

            st.write(
                "Inference Time:",
                result["Inference Time (s)"],
                "seconds"
            )

            st.write(
                "Peak GPU Memory:",
                result["Peak GPU Memory (MB)"],
                "MB"
            )

            st.write(
                "Execution Accuracy:",
                result["EX"]
            )

            st.write(
                "Exact Match:",
                result["EM"]
            )

            if result["Error"]:

                st.error(
                    result["Error"]
                )

    # --------------------------------------------------------
    # Performance comparison charts
    # --------------------------------------------------------

    st.divider()

    st.header("Performance Comparison")

    st.subheader("Inference Time (Seconds)")

    time_df = df[
        ["Model", "Inference Time (s)"]
    ].dropna()

    if not time_df.empty:

        st.bar_chart(
            time_df.set_index("Model")
        )

    st.subheader("Peak GPU Memory (MB)")

    memory_df = df[
        ["Model", "Peak GPU Memory (MB)"]
    ].dropna()

    if not memory_df.empty:

        st.bar_chart(
            memory_df.set_index("Model")
        )

    st.subheader("SQL Accuracy (EX and EM)")

    accuracy_df = df[
        ["Model", "EX", "EM"]
    ].dropna()

    if not accuracy_df.empty:

        st.bar_chart(
            accuracy_df.set_index("Model")
        )

    # --------------------------------------------------------
    # CSV download
    # --------------------------------------------------------

    st.divider()

    st.download_button(
        label="Download Comparison Results",
        data=df.to_csv(index=False),
        file_name="live_quantization_comparison.csv",
        mime="text/csv",
        use_container_width=True
    )


# ============================================================
# STEP 11 - FOOTER
# ============================================================

st.divider()

st.caption(
    "Adaptive Mixed-Precision Quantization Research | "
    "FP16 vs INT8 vs INT4 vs Adaptive"
)

st.caption(
    "Inference time excludes model loading. "
    "Peak memory represents PyTorch CUDA allocated "
    "memory, including model weights. "
    "EX and EM are single-question evaluation values."
)
