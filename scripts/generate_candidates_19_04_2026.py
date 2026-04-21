#!/usr/bin/env python3
import joblib
import pandas as pd
import random
import ipaddress
import math
from pathlib import Path

# Paths
BASE = Path("..")
FEATURES = BASE / "processed" / "features.csv"
MODEL = BASE / "models" / "prefix_model.pkl"
RESULTS_DIR = BASE / "results"

# The new output file (using Parquet for efficiency)
OUTPUT = RESULTS_DIR / "candidates_09_04_2026.parquet"

# Target size
TARGET_TOTAL = 20_000_000

# Heuristic patterns (HIGH VALUE)
PATTERNS = [1, 2, 80, 443, 8080, 0x100, 0x200]
RANDOM_PER_PREFIX = 120  


def load_all_previous_candidates(results_dir: Path):
    """
    Scans the results directory and loads all previously generated 
    candidates from both .txt and .parquet files into a single set.
    """
    old_candidates = set()
    if not results_dir.exists():
        return old_candidates

    print(f"Scanning {results_dir} for previous candidate files...")
    
    for file_path in results_dir.iterdir():
        # Skip the output file if we are overwriting it
        if file_path.name == OUTPUT.name:
            continue
            
        if file_path.suffix == '.parquet':
            print(f" -> Loading Parquet: {file_path.name}")
            df = pd.read_parquet(file_path, columns=["address"])
            old_candidates.update(df["address"].tolist())
            
        elif file_path.suffix == '.txt':
            print(f" -> Loading Text: {file_path.name}")
            with open(file_path, 'r') as f:
                # Strip whitespace and ignore empty lines
                old_candidates.update(line.strip() for line in f if line.strip())

    return old_candidates


def main():
    # Load model and features
    model = joblib.load(MODEL)
    data = pd.read_csv(FEATURES)

    # Feature: log_density
    data["log_density"] = data["density"].apply(
        lambda x: __import__("math").log1p(x)
    )

    # Predict active prefixes
    pred = model.predict(data[["density", "log_density"]])
    active = data[pred == 1].copy()

    # Compute how many prefixes we need
    per_prefix = len(PATTERNS) + RANDOM_PER_PREFIX
    needed_prefixes = math.ceil(TARGET_TOTAL / per_prefix)

    # Limit to available active prefixes
    active_prefixes = active["prefix"].tolist()[:needed_prefixes]

    print(f"Active prefixes available: {len(active)}")
    print(f"Using prefixes: {len(active_prefixes)}")
    print(f"Per-prefix candidates: {per_prefix}")
    print(f"Target total: {TARGET_TOTAL}")

    # Load ALL old candidates to avoid reusing
    old_candidates = load_all_previous_candidates(RESULTS_DIR)
    print(f"Total historical addresses loaded to memory: {len(old_candidates)}")

    raw_candidates = set()

    print("Generating new unique addresses...")
    for prefix in active_prefixes:
        net = ipaddress.ip_network(prefix)
        base = int(net.network_address)

        # Heuristic patterns
        for p in PATTERNS:
            raw_candidates.add(str(ipaddress.IPv6Address(base + p)))

        # Biased random IIDs
        for _ in range(RANDOM_PER_PREFIX):
            rand_int = random.choice([
                random.randint(0, 2**16),
                random.randint(0, 2**32),
                random.getrandbits(64),
            ])
            raw_candidates.add(str(ipaddress.IPv6Address(base + rand_int)))

        # Buffer generation by 10% to account for collisions with historical data
        if len(raw_candidates) >= (TARGET_TOTAL * 1.1):
            break

    print("Filtering out historical duplicates...")
    # Fast C-level set difference to remove all previously seen addresses
    unique_new_candidates = list(raw_candidates - old_candidates)[:TARGET_TOTAL]

    # Convert to DataFrame and save as Parquet
    df_output = pd.DataFrame(unique_new_candidates, columns=["address"])
    df_output.to_parquet(OUTPUT, engine="pyarrow", index=False)

    print(f"Successfully generated {len(df_output)} brand new unique candidates.")
    print(f"Output saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
