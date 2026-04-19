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

OLD_CANDIDATES = BASE / "results" / "candidates.txt"          # existing addresses
OUTPUT = BASE / "results" / "candidates_09_04_2026.txt"       # new addresses

# Target size
TARGET_TOTAL = 20_000_000

# Heuristic patterns (HIGH VALUE)
PATTERNS = [1, 2, 80, 443, 8080, 0x100, 0x200]

# Random IIDs per prefix (we'll tune this to hit ~20M)
RANDOM_PER_PREFIX = 120  # can adjust if needed


def load_old_candidates(path: Path):
    if not path.exists():
        return set()
    with open(path) as f:
        return set(line.strip() for line in f if line.strip())


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

    # Compute how many prefixes we need to reach ~20M
    per_prefix = len(PATTERNS) + RANDOM_PER_PREFIX
    needed_prefixes = math.ceil(TARGET_TOTAL / per_prefix)

    # Limit to available active prefixes
    active_prefixes = active["prefix"].tolist()[:needed_prefixes]

    print(f"Active prefixes available: {len(active)}")
    print(f"Using prefixes: {len(active_prefixes)}")
    print(f"Per-prefix candidates: {per_prefix}")
    print(f"Target total: {TARGET_TOTAL}")

    # Load old candidates to avoid regenerating them
    old = load_old_candidates(OLD_CANDIDATES)
    print(f"Loaded {len(old)} old candidates to avoid reusing.")

    seen = set()  # to avoid duplicates within this run

    written = 0
    with open(OUTPUT, "w") as out:
        for prefix in active_prefixes:
            net = ipaddress.ip_network(prefix)
            base = int(net.network_address)

            # Heuristic patterns
            for p in PATTERNS:
                addr = str(ipaddress.IPv6Address(base + p))
                if addr in old or addr in seen:
                    continue
                out.write(addr + "\n")
                seen.add(addr)
                written += 1

            # Biased random IIDs
            for _ in range(RANDOM_PER_PREFIX):
                rand_int = random.choice([
                    random.randint(0, 2**16),
                    random.randint(0, 2**32),
                    random.getrandbits(64),
                ])
                addr = str(ipaddress.IPv6Address(base + rand_int))
                if addr in old or addr in seen:
                    continue
                out.write(addr + "\n")
                seen.add(addr)
                written += 1

                if written >= TARGET_TOTAL:
                    break

            if written >= TARGET_TOTAL:
                break

    print(f"New candidates written: {written}")
    print(f"Output file: {OUTPUT}")


if __name__ == "__main__":
    main()
