import json
import sqlite3

db_path = "data/spider_data/spider_data/database/concert_singer/concert_singer.sqlite"

question_path = "data/spider_data/spider_data/evaluation_question.json"


with open(question_path,"r",encoding="utf-8") as f:
    questions = json.load(f)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

for items in questions[50:100]:
        question_id = items["id"]
        question = items["question"]
        expected_Sql = items["expected_sql"]

        print("\n"+"="*60)
        print(f"Question {question_id}")
        print(f"Question : {question}")
        print(f"Expected SQL : {expected_Sql}")

        try:
              cursor.execute(expected_Sql)
              result = cursor.fetchall()

              print("Status Valid")
              print("Result : ",result)

        except Exception as e:
              print("Status Error")
              print("Error : ",e)


conn.close()             
