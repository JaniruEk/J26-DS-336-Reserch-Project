import re
import csv
import sqlite3
from collections import Counter
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT/"results/day6/layer_predictions.csv"
OUTPUT = ROOT / "results/day6/layer_evaluated.csv"

DB_ROOT = (ROOT /  "data/spider_data/spider_data/database")

def normalize_Sql(sql):
    sql = str(sql).strip().rstrip(";")
    sql = re.sub(r"\s+"," ",sql)
    return sql.lower()

def execute_sql(sql,db_path):
    sql = str(sql).strip()

    if not re.match(r"^(SELECT|WITH)\b",sql,re.I):
        return None , "Invalid_SQL"

    conn =None

    try:
        conn = sqlite3.connect(db_path.resolve().as_uri()+"?mode=ro",uri=True)

        import time
        deadline = time.monotonic() + 5

        conn.set_progress_handler(
            lambda:int(time.monotonic()>deadline),
            1000
        )

        cursor = conn.cursor()
        cursor.execute(sql)

        rows = cursor.fetchall()
        return rows,None

    except sqlite3.Error as e:
        message = str(e).lower()

        if "syntax" in message or "incomplete" in message:
            return None,"syntax_error"

        return None , "executio_error"

    finally:
        if conn is not None:
            conn.close()


def evalute_row(row):
    db_id = row["db_id"]

    db_path = DB_ROOT /db_id /f"{db_id}.sqlite"

    if not db_path.is_file():
        raise FileNotFoundError(db_path)

    gold_sql = str(row["gold_sql"])
    generated_sql = str(row["generated_sql"])

    em = int(
        normalize_Sql(gold_sql) ==  normalize_Sql(generated_sql)
    )

    gold_result,gold_error = execute_sql(gold_sql,db_path)
    pred_result,pred_error = execute_sql(generated_sql,db_path)

    if gold_error:
        raise ValueError(f"Gold SQL failed for question {row['question_id']}:"
                         f"{gold_sql}")


    if pred_error:
        ex=0
        error_type = pred_error

    else:
        if re.search(r"\border\s+by\b",gold_sql,re.I):
            equivalent = gold_result == pred_result

        else:
            equivalent =(Counter(gold_result) == Counter(pred_result))

        ex = int(equivalent)
        error_type ="none" if equivalent else "wrong_result"

    return em,ex,error_type

def main():
    df = pd.read_csv(INPUT,keep_default_na=False)

    records =[]

    for i,row in df.iterrows():
        em,ex,error_type = evalute_row(row)

        record = row.to_dict()

        record["EM"] =em
        record["EX"] =ex
        record["error_type"]=error_type


        records.append(record)

        print(
            f"Evaluated {i+1}/{len(df)} | "
            f"Layer {row['layer']} | "
            f"EM={em} EX={ex}"
        )

    result_df = pd.DataFrame(records)
    result_df.to_csv(OUTPUT,index=False)

    print("\nEvalaution completed!!!!")
    print("Saved to : ",OUTPUT)


if __name__ =="__main__":
    main()