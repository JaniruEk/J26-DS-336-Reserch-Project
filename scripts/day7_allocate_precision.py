import csv
import json
from pathlib import Path

# Set up the Input and Ouput

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "results/day6/layer_sensitivity_scores.csv"
OUTPUT = ROOT  / "results/day7"
OUTPUT.mkdir(parents=True, exist_ok=True)

Top_k = 4   ##first 4 highest apply INT8
Expected_layers = 32

def load_sensitivity_scores(file_path):
    layers =[]

    with open(file_path,"r",newline="",encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            layers.append({
                "layer":int(row["layer"]),
                "EX":float(row["EX"]),
                "EM":float(row["EM"]),
                "sensitivity_score":float(row["sensitivity_score"])
            })

    return layers


def allocated_precision(layers,top_k=4):

    # sorted by sensitivity,highest first
    ranked_layers =sorted(
        layers,
        key= lambda x:(
            -x["sensitivity_score"],
            x["layer"]
        )
    )

   
    # selected the top K sensitivity layers
    sensitivity_layer_ids ={
        row["layer"] for row in ranked_layers[:top_k]
    }

    
    allocation =[]

    for row in layers:
        layer_id = row["layer"]

        if layer_id in sensitivity_layer_ids:
            precision ="INT8"

        else:
            precision="INT4"

        allocation.append({
            "layer":layer_id,
            "sensitivity_score":row["sensitivity_score"],
            "precision":precision
        })

    
    return sorted(allocation, key=lambda x: x["layer"])


def save_results(allocation):
    csv_path = OUTPUT/"precision_allocation.csv"
    json_path = OUTPUT/"precision_allocation.json"

    with open(csv_path,"w",newline="",encoding="utf-8")  as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "layer",
                "sensitivity_score",
                "precision"
            ]
        )

        writer.writeheader()
        writer.writerows(allocation)

    with open(json_path,"w",newline="",encoding="utf-8") as f:
        json.dump(allocation,f,indent=4)

    print(f"CSV saved to : {csv_path}")
    print(f"JSON saved to : {json_path}")


def main():
    print("...............Sensitivity Aware Precision Allocation................")

    layers = load_sensitivity_scores(INPUT)
    
    layer_ids = [row["layer"] for row in layers]

    if(len(layers) != Expected_layers or set(layer_ids) != set(range(Expected_layers))):
        raise ValueError("Expected exactly 32 unique layers numbered 0-31")

    allocation = allocated_precision(layers,Top_k)

    print(allocation)

    save_results(allocation)

    int8_layers =[row["layer"] for row in allocation if row["precision"] =="INT8" ]
    int4_layers =[row["layer"] for row in allocation if row["precision"] =="INT4" ]

    print("INT8 layers: ",int8_layers)
    print("INT4 layers: ",int4_layers)

    for row in allocation:
        print(
            f"Layer {row['layer']:02d} | "
            f"Score {row['sensitivity_score']:.4f} | "
            f"Precision: {row['precision']}"
        )




if __name__ == "__main__":
    main()
