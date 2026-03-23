import pandas as pd
import numpy as np
import joblib
import time

INPUT_FILE = "../processed/features.csv"
MODEL_FILE = "../models/prefix_model.pkl"
OUTPUT_FILE = "../results/evaluation_without_probe.txt"

start_time = time.time()

print("Loading data...")
data = pd.read_csv(INPUT_FILE)

# Ensure required columns exist
if "density" not in data.columns:
    raise ValueError("Column 'density' not found in features.csv")

# Create log_density if missing (FIX for your error)
if "log_density" not in data.columns:
    print("Creating log_density...")
    data["log_density"] = np.log1p(data["density"])

print("Loading model...")
model = joblib.load(MODEL_FILE)

print("Running evaluations...")

# 1. Random baseline
random_sample = data.sample(n=10000, random_state=42)
random_avg = random_sample["density"].mean()

# 2. Model prediction
pred = model.predict(data[["density", "log_density"]])
selected = data[pred == 1]

# Avoid empty selection crash
model_avg = selected["density"].mean() if len(selected) > 0 else 0
selected_count = len(selected)

# 3. Top-K baseline
top_k = data.sort_values("density", ascending=False).head(10000)
top_avg = top_k["density"].mean()

end_time = time.time()

print("Saving results...")

with open(OUTPUT_FILE, "w") as f:
    f.write("=== --- Evaluation Without Probing --- ===\n\n")

    f.write(f"Random Sample Size: 10000\n")
    f.write(f"Random Average Density: {random_avg:.4f}\n\n")

    f.write(f"Model Selected Prefixes: {selected_count}\n")
    f.write(f"Model Average Density: {model_avg:.4f}\n\n")

    f.write(f"Top-K (10000) Average Density: {top_avg:.4f}\n\n")

    f.write(f"Execution Time: {end_time - start_time:.2f} seconds\n")

print("Done. Results saved to:", OUTPUT_FILE)
