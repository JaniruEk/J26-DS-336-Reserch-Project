import pandas as pd
from pathlib import Path

path = Path("results/day6/layer_evaluated.csv")
df = pd.read_csv(path)

baseline = df[df["layer"]=="baseline"]

base_ex = baseline["EX"].mean()
base_em = baseline["EM"].mean()

print("base_EX: ",base_ex)

results=[]

for layer in range(32):
    rows =df[df["layer"] == str(layer)]

    if rows.empty:
        raise ValueError(f"Missing results for layer {layer}")

    ex = rows["EX"].mean()
    em = rows["EM"].mean()

    delta_ex = base_ex - ex
    delta_em = base_em - em

    score = 0.6 * delta_ex + 0.4 * delta_em

    results.append({
        "layer":layer,
        "EX":ex,
        "EM":em,
        "delta_EX":delta_ex,
        "delta_EM":delta_em,
        "sensitivity_score":score
    })

result_df = pd.DataFrame(results)

result_df.to_csv(
    "results/day6/layer_sensitivity_scores.csv",
    index=False
)

print(result_df.sort_values("sensitivity_score",ascending=False))