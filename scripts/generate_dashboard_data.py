#!/usr/bin/env python3
"""
Generate comprehensive dashboard data from port reachability CSV files.
- CSV files have NO headers (from GCS probe)
- Only parse TRUE/FALSE port columns
- Count successes and port responses
"""
import pandas as pd
import json
import re
from pathlib import Path
from datetime import datetime


def parse_phase_to_date(phase_str):
    """
    Convert phase format (dd_mm_yy) to date string (YYYY-MM-DD)
    Example: 08_05_26 → 2026-05-08
    """
    try:
        parts = phase_str.split('_')
        if len(parts) != 3:
            return None
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
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


def analyze_port_reachability_new_format(df):
    """
    Analyze port reachability from NEW format CSV (no headers, TRUE/FALSE columns)
    CSV columns: ip(0), status(1), server(2), hsts(3), common_name(4), icmp(5), tcp80(6), tcp443(7), tcp8080(8), tcp8443(9), udp53(10)
    
    Returns: dict with port statistics and analysis
    """
    # Ensure we have at least 11 columns (includes all port columns)
    if len(df.columns) < 11:
        return None
    
    # Extract port columns by index (columns 5-10 are the port TRUE/FALSE values)
    port_columns = [5, 6, 7, 8, 9, 10]  # icmp, tcp80, tcp443, tcp8080, tcp8443, udp53
    port_names = ['icmp', 'tcp80', 'tcp443', 'tcp8080', 'tcp8443', 'udp53']
    
    # Convert port columns to boolean (TRUE = responsive)
    for col in port_columns:
        df[col] = df[col].astype(str).str.strip().str.upper() == 'TRUE'
    
    # Calculate port-level statistics
    port_stats = {}
    for idx, port_name in enumerate(port_names):
        col_idx = port_columns[idx]
        responsive_count = int(df[col_idx].sum())  # Count TRUE values
        port_stats[port_name] = {
            'responsive': responsive_count,  # Number of IPs responding on this port
            'percentage': round((responsive_count / len(df)) * 100, 2) if len(df) > 0 else 0
        }
    
    # Calculate multi-port analysis: How many IPs respond to N ports?
    df['port_count'] = df[[port_columns[i] for i in range(len(port_columns))]].astype(int).sum(axis=1)
    
    # Count IPs by number of responding ports
    multi_port_dist = df['port_count'].value_counts().sort_index().to_dict()
    multi_port_analysis = [
        {
            'ports': int(k),
            'count': int(v),
            'percentage': round((v / len(df)) * 100, 2),
            'label': f'{int(k)} port{"s" if k != 1 else ""}'
        }
        for k, v in sorted(multi_port_dist.items())
    ]
    
    # Count responsive IPs (at least 1 port responds)
    responsive_ips = int((df['port_count'] > 0).sum())
    silent_ips = int((df['port_count'] == 0).sum())
    
    # Count successes from status column (column 1)
    successful_ips = int((df[1].astype(str).str.strip() == 'success').sum())
    
    return {
        'port_stats': port_stats,
        'multi_port_analysis': multi_port_analysis,
        'responsive_ips': responsive_ips,
        'silent_ips': silent_ips,
        'total_ips': len(df),
        'successful_ips': successful_ips,
        'success_rate': round((successful_ips / len(df)) * 100, 2) if len(df) > 0 else 0
    }


def analyze_status_distribution(df):
    """
    Analyze status distribution (status is column 1)
    """
    if 1 not in df.columns:
        return {}
    
    status_dist = df[1].astype(str).str.strip().value_counts().to_dict()
    total = len(df)
    
    return {
        status: {
            'count': int(count),
            'percentage': round((count / total) * 100, 2)
        }
        for status, count in status_dist.items()
    }


def generate_dashboard_data(current_phase=None):
    """
    Generate comprehensive dashboard data from headerless CSV files
    """
    
    # Use absolute path to handle any working directory
    script_dir = Path(__file__).parent
    gcloud_dir = script_dir.parent / "processed_gcloud"
    
    # Find all CSV files
    csv_files = list(gcloud_dir.glob("processed_metrics_*.csv"))
    
    if not csv_files:
        print("No CSV files found in processed_gcloud!")
        return None
    
    print(f"Found {len(csv_files)} metrics files. Analyzing...")
    
    # Load existing dashboard data to preserve history (even if old CSVs are deleted later)
    output_path = script_dir.parent / "dashboard" / "public" / "dashboard_data.json"
    existing_history = []
    
    if output_path.exists():
        try:
            with open(output_path, 'r') as f:
                existing_data = json.load(f)
                existing_history = existing_data.get('scan_history', [])
            print(f"Loaded {len(existing_history)} historical scan records")
        except Exception as e:
            print(f"Could not load existing data: {e}")
    
    # Process each metrics file
    scan_history = []
    new_records_by_phase = {}
    
    for file in sorted(csv_files):
        phase = extract_phase_from_filename(file.name)
        if not phase:
            print(f"  Skipping {file.name} - could not extract phase")
            continue
        
        date_str = parse_phase_to_date(phase)
        if not date_str:
            print(f"  Skipping {file.name} - invalid phase format")
            continue
        
        print(f"  Processing {file.name} (phase: {phase}, date: {date_str})")
        
        try:
            # Read CSV WITHOUT headers (GCS doesn't provide headers)
            df = pd.read_csv(file, header=None, quotechar='"')
            
            print(f"    Rows: {len(df)}, Columns: {len(df.columns)}")
            
            total_scanned = len(df)
            
            # Build phase record
            phase_record = {
                "phase": phase,
                "date": date_str,
                "timestamp": datetime.now().isoformat(),
                "total_ips": total_scanned,
                "format": "port_reachability" if len(df.columns) >= 11 else "legacy",
            }
            
            status_analysis = analyze_status_distribution(df)
            # Analyze port reachability (only if we have all columns)
            if len(df.columns) >= 11:
                port_analysis = analyze_port_reachability_new_format(df)

                if port_analysis:
                    phase_record.update({
                        "port_stats": port_analysis["port_stats"],
                        "multi_port_analysis": port_analysis["multi_port_analysis"],
                        "responsive_ips": port_analysis["responsive_ips"],
                        "silent_ips": port_analysis["silent_ips"],
                        "successful_ips": port_analysis["successful_ips"],
                        "status_distribution": status_analysis,
                        "response_rate": round((port_analysis["responsive_ips"] / total_scanned) * 100, 2) if total_scanned > 0 else 0,
                        "success_rate": port_analysis["success_rate"],
                    })

                    # Print summary
                    print(f"    ✓ Responsive IPs: {port_analysis['responsive_ips']}/{total_scanned}")
                    print(f"    ✓ Successful IPs: {port_analysis['successful_ips']}/{total_scanned}")
                    print(f"    ✓ Port stats:")
                    for port, stats in port_analysis["port_stats"].items():
                        print(f"      - {port.upper()}: {stats['responsive']} IPs ({stats['percentage']:.1f}%)")
            else:
                # Legacy file: still count successes/statuses if present
                successful_ips = int((df[1].astype(str).str.strip() == "success").sum()) if 1 in df.columns else 0
                phase_record.update({
                    "successful_ips": successful_ips,
                    "success_rate": round((successful_ips / total_scanned) * 100, 2) if total_scanned > 0 else 0,
                    "status_distribution": status_analysis,
                })
            
            scan_history.append(phase_record)
            new_records_by_phase[phase] = phase_record
            
        except Exception as e:
            print(f"  ✗ Error processing {file.name}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Merge with existing history by phase so history is preserved even if CSVs disappear
    existing_by_phase = {
        r.get("phase"): r for r in existing_history if isinstance(r, dict) and r.get("phase")
    }
    merged_by_phase = dict(existing_by_phase)
    for phase, new_rec in new_records_by_phase.items():
        old_rec = merged_by_phase.get(phase, {})
        if isinstance(old_rec, dict):
            # Keep old keys that are not produced anymore (e.g., old infrastructure fields)
            merged = dict(old_rec)
            merged.update(new_rec)
            merged_by_phase[phase] = merged
        else:
            merged_by_phase[phase] = new_rec

    merged_history = list(merged_by_phase.values())
    merged_history = sorted(merged_history, key=lambda x: (x.get("date") or "", x.get("phase") or ""))

    # Choose latest scan: prefer requested current_phase if present, otherwise newest by date
    latest_data = None
    if current_phase:
        latest_data = next((r for r in merged_history if r.get("phase") == current_phase), None)
    if latest_data is None and merged_history:
        latest_data = merged_history[-1]

    # Mark latest scan
    for record in merged_history:
        record["is_latest"] = bool(latest_data and record.get("phase") == latest_data.get("phase"))
    
    # Format the final dashboard data
    dashboard_data = {
        "last_updated": datetime.now().isoformat(),
        "total_scans": len(merged_history),
        "latest_scan": latest_data,
        "current_format": latest_data.get("format") if isinstance(latest_data, dict) else "unknown",
        "scan_history": merged_history,
        
        # Summary statistics (from latest scan)
        "summary": {
            "total_ips_scanned": latest_data.get('total_ips', 0),
            "responsive_ips": latest_data.get('responsive_ips', 0),
            "successful_ips": latest_data.get('successful_ips', 0),
            "response_rate_percentage": latest_data.get('response_rate', 0),
            "success_rate_percentage": latest_data.get('success_rate', 0),
            "status_breakdown": latest_data.get('status_distribution', {})
        },
        
        # Port analysis
        "port_analysis": latest_data.get('port_stats', {}) if isinstance(latest_data, dict) else {},
        "multi_port_distribution": latest_data.get('multi_port_analysis', []) if isinstance(latest_data, dict) else [],
    }
    
    # Save dashboard data
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(dashboard_data, f, indent=4)
    
    print(f"\n✓ Successfully generated dashboard data at {output_path}")
    print(f"  Total scans processed: {len(merged_history)}")
    print(f"  IPs in latest scan: {dashboard_data['summary']['total_ips_scanned']}")
    print(f"  Responsive IPs: {dashboard_data['summary']['responsive_ips']}")
    print(f"  Successful IPs: {dashboard_data['summary']['successful_ips']}")
    print(f"  Port analysis: {json.dumps(dashboard_data['port_analysis'], indent=2)}")
    
    return dashboard_data


if __name__ == "__main__":
    import sys
    current_phase = sys.argv[1] if len(sys.argv) > 1 else None
    generate_dashboard_data(current_phase)
