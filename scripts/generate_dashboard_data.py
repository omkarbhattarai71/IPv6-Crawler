#!/usr/bin/env python3
import pandas as pd
import json
from pathlib import Path

# Target directory
gcloud_dir = Path("../processed_gcloud")

# Find all CSV files
csv_files = list(gcloud_dir.glob("*.csv"))

if not csv_files:
    print("No CSV files found in processed_gcloud!")
    exit()

print(f"Found {len(csv_files)} metrics files. Aggregating...")

# Read and concatenate all CSVs
dfs = []
for file in csv_files:
    # Use fillna("") to handle completely empty files gracefully
    df = pd.read_csv(file, header=None, names=["ip", "status", "server", "hsts", "common_name"]).fillna("")
    dfs.append(df)

combined_df = pd.concat(dfs, ignore_index=True)

# Calculate high-level stats
total_scanned = len(combined_df)
successful_connections = len(combined_df[combined_df["status"] == "success"])
failed_connections = total_scanned - successful_connections

# Get the top 10 most common Subject Names (CDNs/Infrastructures)
# We filter out empty strings to only count actual valid hostnames
valid_cdns = combined_df[combined_df["common_name"] != ""]
top_cdns = valid_cdns["common_name"].value_counts().head(10).to_dict()

# Format the data for React
dashboard_data = {
    "scan_stats": {
        "total": total_scanned,
        "success": successful_connections,
        "failed": failed_connections,
        "hit_rate_percentage": round((successful_connections / total_scanned) * 100, 4) if total_scanned > 0 else 0
    },
    "top_infrastructure": [{"name": k, "count": v} for k, v in top_cdns.items()]
}

# Save directly into the React source folder
output_path = "../dashboard/src/dashboard_data.json"
with open(output_path, "w") as f:
    json.dump(dashboard_data, f, indent=4)

print(f"Successfully generated React data at {output_path}")
