#!/usr/bin/env python3
"""
Generate dashboard data from processed metrics files
Appends historical data with dates from processed_metrics_<phase>.csv files
"""
import pandas as pd
import json
import re
from pathlib import Path
from datetime import datetime


def parse_phase_to_date(phase_str):
    """
    Convert phase format (dd_mm_yy) to date string (YYYY-MM-DD)
    Example: 19_04_26 → 2026-04-19
    """
    try:
        parts = phase_str.split('_')
        if len(parts) != 3:
            return None
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        # Assume 20xx for years 00-99
        full_year = 2000 + year if year <= 99 else year
        date_obj = datetime(full_year, month, day)
        return date_obj.strftime("%Y-%m-%d")
    except (ValueError, IndexError):
        return None


def extract_phase_from_filename(filename):
    """Extract phase from processed_metrics_<phase>.csv"""
    match = re.search(r'processed_metrics_([0-9]{2}_[0-9]{2}_[0-9]{2})\.csv', filename)
    if match:
        return match.group(1)
    return None


def generate_dashboard_data(current_phase=None):
    """
    Generate dashboard data from all processed metrics files
    Preserves historical data and appends with dates
    
    Args:
        current_phase: Optional current phase to mark as latest (format: dd_mm_yy)
    """
    
    # Target directory
    gcloud_dir = Path("../processed_gcloud")
    
    # Find all CSV files
    csv_files = list(gcloud_dir.glob("processed_metrics_*.csv"))
    
    if not csv_files:
        print("No CSV files found in processed_gcloud!")
        return None
    
    print(f"Found {len(csv_files)} metrics files. Aggregating...")
    
    # Load existing dashboard data if it exists (to preserve history)
    # Target directory - write to public folder for serving
    output_path = Path("../dashboard/public/dashboard_data.json")
    existing_data = {}
    existing_history = {}
    
    if output_path.exists():
        try:
            with open(output_path, 'r') as f:
                existing_data = json.load(f)
                existing_history = {item['phase']: item for item in existing_data.get('historical_data', [])}
            print(f"Loaded existing dashboard data with {len(existing_history)} historical records")
        except Exception as e:
            print(f"Could not load existing data: {e}")
    
    # Process each metrics file
    historical_data = []
    all_combined_df = pd.DataFrame()
    
    for file in sorted(csv_files):
        phase = extract_phase_from_filename(file.name)
        if not phase:
            print(f"Skipping {file.name} - could not extract phase")
            continue
        
        date_str = parse_phase_to_date(phase)
        if not date_str:
            print(f"Skipping {file.name} - invalid phase format")
            continue
        
        print(f"  Processing {file.name} (phase: {phase}, date: {date_str})")
        
        try:
            # Read CSV with proper column names
            df = pd.read_csv(file, header=None, names=["ip", "status", "server", "hsts", "common_name"]).fillna("")
            
            # Calculate stats for this phase
            total_scanned = len(df)
            successful_connections = len(df[df["status"] == "success"])
            failed_connections = total_scanned - successful_connections
            
            # Get top 10 CDNs/Infrastructure for this phase
            valid_cdns = df[df["common_name"] != ""]
            top_cdns = valid_cdns["common_name"].value_counts().head(10).to_dict()
            
            # Create phase record
            phase_record = {
                "phase": phase,
                "date": date_str,
                "stats": {
                    "total": int(total_scanned),
                    "success": int(successful_connections),
                    "failed": int(failed_connections),
                    "hit_rate_percentage": round((successful_connections / total_scanned) * 100, 4) if total_scanned > 0 else 0
                },
                "top_infrastructure": [{"name": k, "count": int(v)} for k, v in top_cdns.items()]
            }
            
            historical_data.append(phase_record)
            all_combined_df = pd.concat([all_combined_df, df], ignore_index=True)
            
        except Exception as e:
            print(f"  Error processing {file.name}: {e}")
            continue
    
    if all_combined_df.empty:
        print("No valid data to process!")
        return None
    
    # Calculate overall stats (combined from all phases)
    total_scanned = len(all_combined_df)
    successful_connections = len(all_combined_df[all_combined_df["status"] == "success"])
    failed_connections = total_scanned - successful_connections
    
    # Get top 10 overall CDNs/Infrastructure
    valid_cdns = all_combined_df[all_combined_df["common_name"] != ""]
    top_cdns = valid_cdns["common_name"].value_counts().head(10).to_dict()
    
    # Sort historical data by phase
    historical_data = sorted(historical_data, key=lambda x: x['phase'])
    
    # Mark current phase as latest if provided
    if current_phase:
        for record in historical_data:
            record['is_latest'] = (record['phase'] == current_phase)
    
    # Format the final data for React
    dashboard_data = {
        "last_updated": datetime.now().isoformat(),
        "scan_stats": {
            "total": int(total_scanned),
            "success": int(successful_connections),
            "failed": int(failed_connections),
            "hit_rate_percentage": round((successful_connections / total_scanned) * 100, 4) if total_scanned > 0 else 0
        },
        "top_infrastructure": [{"name": k, "count": int(v)} for k, v in top_cdns.items()],
        "historical_data": historical_data,
        "total_phases": len(historical_data)
    }
    
    # Save directly into the React source folder
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(dashboard_data, f, indent=4)
    
    print(f"\n✓ Successfully generated React data at {output_path}")
    print(f"  Total records: {dashboard_data['scan_stats']['total']}")
    print(f"  Historical phases: {dashboard_data['total_phases']}")
    print(f"  Hit rate: {dashboard_data['scan_stats']['hit_rate_percentage']}%")
    
    return dashboard_data


if __name__ == "__main__":
    import sys
    current_phase = sys.argv[1] if len(sys.argv) > 1 else None
    generate_dashboard_data(current_phase)
