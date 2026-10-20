
import csv
from pathlib import Path

from src.layer_sensitive import quantize_single_layer
from scripts.day6_prepare_questions import load_fixed_examples
from src.qwen_generate import generate_sql
from src.schema_utils import get_schema
from src.prompt_builder import build_prompt
from src.sql_util import clean_sql
from src.qwen_model_loader import load_qwen

ROOT = Path(__file__).resolve().parents[1]

# Keep your requested output directory
OUTPUT = Path("results/qwen")
OUTPUT.mkdir(parents=True, exist_ok=True)

file_path = OUTPUT / "qwen_layer_predictions.csv"

FIELDNAMES = [
    "question_id",
    "db_id",
    "question",
    "gold_sql",
    "layer",
    "generated_sql"
]

results = []

# Load previous results if they exist
if file_path.exists():
    with open(file_path,"r",encoding="utf-8",newline="") as f:
        results = list(csv.DictReader(f))

    print(f"Loaded {len(results)} previous results")

else:
    print("No previous results. Starting new experiment.")


def save_results():

    with open(file_path,"w",newline="",encoding="utf-8") as f:
        writer = csv.DictWriter(f,fieldnames=FIELDNAMES)

        writer.writeheader()
        writer.writerows(results)


def run_questions(model, tokenizer, examples, layer_name):

    for example in examples:

        question_id = example["question_id"]
        db_id = example["db_id"]

        question = example["questions"]
        gold_sql = example["gold_sql"]

        # Skip already completed predictions
        already_done = any(
            str(row["layer"]) == str(layer_name)
            and str(row["question_id"]) == str(question_id)
            and str(row["db_id"]) == str(db_id)
            for row in results
        )

        if already_done:
            print(
                f"Skipping Layer {layer_name} "
                f"Question {question_id}"
            )
            continue

        db_path = (ROOT /"data/spider_data/spider_data/database" /db_id /f"{db_id}.sqlite")

        if not db_path.is_file():
            raise FileNotFoundError(
                f"Database not found: {db_path}"
            )

        schema = get_schema(db_path)
        prompt = build_prompt(schema, question)

        generated = generate_sql(
            model,
            tokenizer,
            prompt
        )

        generated = clean_sql(generated)

        results.append({
            "question_id": question_id,
            "db_id": db_id,
            "question": question,
            "gold_sql": gold_sql,
            "layer": layer_name,
            "generated_sql": generated
        })

        # Save after each prediction
        save_results()

        print(
            f"Layer {layer_name} | "
            f"Question {question_id}"
        )


def main():

    print("=" * 50)
    print("QWEN LAYER SENSITIVITY EXPERIMENT")
    print("=" * 50)

    # Sensitivity experiments use FP16 reference
    model, tokenizer = load_qwen("fp16")

    model.eval()

    examples = load_fixed_examples(limit=25)

    total_layers = len(model.model.layers)

    print("Total layers:", total_layers)
    print("Total questions:", len(examples))

    # Run the original FP16 reference once
    print("\nRunning FP16 baseline...")

    run_questions(
        model,
        tokenizer,
        examples,
        "baseline"
    )

    # First test only 5 layers
    # After successful testing, use range(total_layers)
    for layer_id in range(len(model.model.layers)):

        print(f"\nTesting Layer {layer_id}")

        with quantize_single_layer(model, layer_id):

            run_questions(
                model,
                tokenizer,
                examples,
                layer_id
            )

        print(f"Layer {layer_id} restored")

    print("\nLayer experiments completed!")
    print("Results saved to:", file_path)


if __name__ == "__main__":
    main()
