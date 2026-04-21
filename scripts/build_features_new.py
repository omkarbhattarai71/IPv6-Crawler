#!/usr/bin/env python3
import pandas as pd
import ipaddress
import sys

def main():
    # flush=True forces Python to write to the SLURM log immediately
    print("Loading historical features...", flush=True)
    
    # Load the existing features
    features_df = pd.read_csv("../processed/features.csv")
    features_df.set_index("prefix", inplace=True)

    print("Loading new GCP scan results...", flush=True)
    new_hits = pd.read_csv(
        "../processed_gcloud/processed_metrics.csv", 
        header=None, 
        usecols=[0], 
        names=["ip"]
    )

    print(f"Processing {len(new_hits)} newly discovered active IPs...", flush=True)
    new_counts = {}

    # Count the densities of the newly discovered IPs
    for ip_str in new_hits["ip"]:
        try:
            ip = ipaddress.IPv6Address(ip_str)
            prefix = str(ipaddress.IPv6Network(f"{ip}/48", strict=False))
            # Faster dictionary counter
            new_counts[prefix] = new_counts.get(prefix, 0) + 1
        except ValueError:
            continue

    print(f"Found {len(new_counts)} unique /48 prefixes. Merging datasets...", flush=True)

    # ---------------------------------------------------------
    # VECTORIZED MERGE: This reduces processing time from hours to milliseconds - Learned in Numerical Scientific Computing
    # ---------------------------------------------------------
    # 1. Convert the new counts dict directly into a DataFrame
    new_df = pd.DataFrame.from_dict(new_counts, orient='index', columns=['density'])
    
    # 2. Add the two DataFrames together. fill_value=0 ensures new prefixes are kept!
    merged_df = features_df.add(new_df, fill_value=0)
    
    # 3. Convert floats back to integers
    merged_df['density'] = merged_df['density'].astype(int)

    # Clean up and save
    merged_df.index.name = "prefix"
    merged_df.reset_index(inplace=True)

    print("Saving updated features...", flush=True)
    merged_df.to_csv("../processed/features.csv", index=False)
    
    print("Closed-loop update complete. Features saved to ../processed/features.csv", flush=True)

if __name__ == "__main__":
    main()

