import csv
import json
from pathlib import  Path

from src.sql_evaluator import comapre_sql
from src.error_classifier import classify_error

ROOT =Path(__file__).resolve().parents[1]

SPIDER_DB =(ROOT/"data"/"spider_data"/"spider_data"/"database")

INPUT_FILE =(ROOT/"results"/"day5"/"baseline_predictions.json")

OUTPUT_DIR = ROOT/"results"/"day5"
OUTPUT_DIR.mkdir(parents=True,exist_ok=True)

def main():
    with open(INPUT_FILE,"r",encoding="utf-8") as f:
        predictions =json.load(f)

    results =[]

    for index,item in enumerate(predictions,start=1):
        question_id =item.get("question_id",index)
        db_id = item["db_id"]

        db_path = (SPIDER_DB/db_id/f"{db_id}.sqlite")

        if not db_path.is_file():
            print(f"Missing database : {db_path}")
            continue

        evaluation =comapre_sql(
            db_path,
            item["gold_sql"],
            item["generated_sql"]
        )

        error_type = classify_error(
            item["gold_sql"],
            item["generated_sql"],
            evaluation["execution_error"],
            evaluation["executed"],
            evaluation["execution_match"]
        )

        result = {
            "question_id": question_id,
            "db_id": db_id,
            "question": item["question"],
            "difficulty": item.get("difficulty", "unknown"),
            "gold_sql": item["gold_sql"],
            "generated_sql": item["generated_sql"],
            **evaluation,
            "error_type": error_type
        }

        results.append(result)

        print(
            f"Question {question_id} : "
            f"Match={evaluation['execution_match']} | "
            f"Error={error_type}"
        )

    if not results:
        print("No question were evaluated.")
        return

    json_path =OUTPUT_DIR/"execution_feedback.json"

    with open(json_path,"w",encoding="utf-8") as f:
        json.dump(results,f,indent=4,ensure_ascii=False)

    csv_path =OUTPUT_DIR/"execution_feedback.csv"

    with open(csv_path,"w",newline="",encoding="utf-8") as f:
        writer =csv.DictWriter(f,fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    valid= [r for r in results if r["gold_executed"]]

    matched =sum(r["execution_match"] for r in valid)
    executed =sum(r["executed"] for r in valid)

    total = len(valid)

    if total:
        accuracy = 100 * matched/total
        exection_rate =100*executed/total

    else:
        accuracy=0
        exection_rate=0

    print("\n======= Day 5 Evaluation Summary =======")
    print(f"Total evaluated : {len(results)}")
    print(f"Valid gold  queries : {total}")
    print(f"Execution Rate : {exection_rate:.2f}%")
    print(f"Execution accuracy: {accuracy:.2f}%")
    print(f"JSON saved : {json_path}")
    print(f"CSV saved : {csv_path}")

if __name__=="__main__":
    main()


