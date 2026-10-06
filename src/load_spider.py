import json

SPIDER_FILE = "data/spider_data/spider_data/dev.json"

with open(SPIDER_FILE,"r",encoding="utf-8") as f :
    data=json.load(f)

print("Total Examples : ",len(data))

for example in data[:5]:
    print("="*50)
    print("Database : ",example["db_id"])
    print("Question : ",example["question"])
    print("Expected SQL : ",example["query"])