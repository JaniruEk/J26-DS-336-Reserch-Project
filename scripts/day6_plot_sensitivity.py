import pandas as pd
import matplotlib.pyplot as plt

df =pd.read_csv("results/day6/layer_sensitivity_scores.csv")

plt.figure(figsize=(12,5))

plt.bar(
    df["layer"],
    df["sensitivity_score"]
)

plt.xlabel("Phi-3 Transformer Layer")
plt.ylabel("Sensitivity Score")
plt.title("Phi-3 Mini Layer Sensitivity for Text-to-Sql")

plt.xticks(range(32),rotation=90)
plt.grid(axis="y",alpha=0.3)
plt.tight_layout()

plt.savefig("results/day6/layer_sensitivity.png",dpi=300)

plt.show()