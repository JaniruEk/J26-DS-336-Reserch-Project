
import csv
from pathlib import Path

from src.layer_sensitive import quantize_single_layer
from src.model_loader import load_fp16_model
from scripts.day6_prepare_questions import load_fixed_examples
from src.generateSqlWIthoutSeprateModel_tokenizer import generate_Sql
from src.schema_utils import get_schema
from src.prompt_builder import build_prompt
from src.sql_util import clean_sql

OUTPUT = Path("results/day6")
OUTPUT.mkdir(parents=True, exist_ok=True)

ROOT = Path(__file__).resolve().parents[1]

results = []

file_path = OUTPUT / "layer_predictions.csv"

if file_path.exists():
                with open(file_path, "r", encoding="utf-8", newline="") as f:
                    results = list(csv.DictReader(f))
else:
                raise FileNotFoundError(
                    "Previous Day 6 results not found!"
                )


def save_results():
    if not results:
        return

    
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                  "question_id",
                "db_id",
                "question",
                "gold_sql",
                "layer",
                "generated_sql"
            ]
        )

        writer.writeheader()
        writer.writerows(results)

    

def run_questions(model, tokenizer, examples, layer_name):

    for example in examples:

        question_id = example["question_id"]
        db_id = example["db_id"]
        question = example["questions"]
        gold_sql = example["gold_sql"]

        db_path = (ROOT / "data/spider_data/spider_data/database"/ db_id / f"{db_id}.sqlite")

        if not db_path.is_file():
            raise FileNotFoundError(
                f"Database not found: {db_path}"
            )

        schema = get_schema(db_path)
        prompt = build_prompt(schema,question)

        generated = generate_Sql(
            prompt,
            model,
            tokenizer
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

        print(f"Layer {layer_name} | Question {question_id}")

    save_results()


def main():

    model, tokenizer = load_fp16_model()
    model.eval()

    examples = load_fixed_examples(limit=25)

    print("Total layers:", len(model.model.layers))
    print("Total questions:", len(examples))

    # 1. Original FP16 baseline
    # print("\nRunning FP16 baseline...")

    # run_questions(
    #     model, tokenizer, examples, "baseline"
    # )

    # 2. Layer-by-layer experiments
    # for layer_id in range(len(model.model.layers)):
    for layer_id in range(25,32):

        print(f"\nTesting layer: {layer_id}")

        with quantize_single_layer(model, layer_id):
            run_questions(
                model, tokenizer, examples, layer_id
            )

        print(f"Layer {layer_id} restored")

    print("\nLayer experiments completed!")


if __name__ == "__main__":
    main()
