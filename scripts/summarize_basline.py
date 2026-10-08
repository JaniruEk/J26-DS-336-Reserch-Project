import csv

result_path = "results/baseline_results.csv"

rows =[]

with open(result_path,"r",encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:
        rows.append(row)

total_question = len(rows)

exact_mach_count = sum(
    int(row["SQL_Exact_Match"])
    for row in rows
)

execution_correct_count = sum(
    int(row["Execution_Correct"])
    for row in rows
)

avg_latency =sum(
    float(row["Latency_Seconds"])
    for row in rows
)/total_question

maximum_vram = max(
    float(row["Peak_VRAM_MB"])
    for row in rows
)



exact_match_accuracy=(
    exact_mach_count/total_question
)*100

execution_accuracy =(
    execution_correct_count / total_question
)*100

print("="*60)
print("Unquantized baseline summary")
print("="*60)

print(f"Total Question : {total_question}")

print(f"SQL Exact Match :"
      f"{exact_match_accuracy:.2f}%")

print(f"Execution Accuracy : {execution_accuracy:.2f}%")

print(f"AVG Latency : {avg_latency:.4f} seconds")

print(f"Maximum Peak VRAM : {maximum_vram:.2f} MB")