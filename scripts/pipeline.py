#!/usr/bin/env python3
"""
IPv6 Crawler - Complete Pipeline Automation
============================================
Automates the entire workflow: feature building → model training → candidate generation → cloud upload

PHASES EXPLAINED:
  Input Phase:   Date of processed_metrics_*.csv file (e.g., 21_04_26 for historical data)
  Current Phase: Today's date for output files (e.g., 04_05_26 for today)

Usage:
    python3 pipeline.py <input_phase>

where <input_phase> is in format: ddmmyy (e.g., 21_04_26 from processed_metrics_21_04_26.csv)
  Current phase is auto-detected from today's date
  Output files use current phase: candidates_04_05_26.parquet, prefix_model_04_05_26.pkl
"""

import sys
import subprocess
import pandas as pd
import joblib
import random
import ipaddress
import math
from pathlib import Path
from datetime import datetime
import shutil
import os


class PipelineLogger:
    """Simple logging utility with timestamps"""
    def __init__(self, phase: str):
        self.phase = phase
        self.start_time = datetime.now()
    
    def log(self, msg: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {msg}", flush=True)
    
    def info(self, msg: str):
        self.log(msg, "INFO")
    
    def success(self, msg: str):
        self.log(msg, "✓ SUCCESS")
    
    def error(self, msg: str):
        self.log(msg, "✗ ERROR")
    
    def section(self, title: str):
        print(f"\n{'='*70}")
        self.log(title)
        print(f"{'='*70}\n")


def validate_phase(phase: str) -> bool:
    """Validate phase format: ddmmyy"""
    if len(phase) != 8 or phase[2] != '_' or phase[5] != '_':
        return False
    try:
        day = int(phase[0:2])
        month = int(phase[3:5])
        year = int(phase[6:8])
        return 1 <= day <= 31 and 1 <= month <= 12 and 0 <= year <= 99
    except ValueError:
        return False


def check_input_file(input_file: Path, logger: PipelineLogger) -> bool:
    """Verify input file exists"""
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        return False
    logger.info(f"Input file validated: {input_file.name}")
    return True


def setup_working_environment(input_phase: str, current_phase: str, base_path: Path, logger) -> dict:
    """Prepare working directories and paths
    
    input_phase: Date of processed_metrics_*.csv (e.g., 21_04_26)
    current_phase: Today's date for outputs (e.g., 04_05_26)
    """
    paths = {
        'base': base_path,
        'scripts': base_path / "scripts",
        'processed': base_path / "processed",
        'gcloud': base_path / "processed_gcloud",
        'models': base_path / "models",
        'results': base_path / "results",
        
        # Input: from input_phase
        'input': base_path / "processed_gcloud" / f"processed_metrics_{input_phase}.csv",
        
        # Working/Cumulative (kept for backward compatibility)
        'features': base_path / "processed" / "features.csv",
        
        # Output: using current_phase
        'model_pkl': base_path / "models" / f"prefix_model_{current_phase}.pkl",
        'output': base_path / "results" / f"candidates_{current_phase}.parquet",
    }
    
    # Ensure output directory exists
    paths['results'].mkdir(parents=True, exist_ok=True)
    paths['models'].mkdir(parents=True, exist_ok=True)
    logger.info("Working directories validated")
    
    return paths


def build_features(phase: str, paths: dict, logger: PipelineLogger) -> bool:
    """
    Build features from processed metrics
    Equivalent to: python3 build_features_new.py
    """
    logger.section("STEP 1: Building Features")
    
    if not check_input_file(paths['input'], logger):
        return False
    
    try:
        logger.info("Loading historical features...")
        features_df = pd.read_csv(paths['features'])
        features_df.set_index("prefix", inplace=True)
        
        logger.info(f"Loading new GCP scan results from {paths['input'].name}...")
        new_hits = pd.read_csv(
            paths['input'],
            header=None,
            usecols=[0],
            names=["ip"]
        )
        
        logger.info(f"Processing {len(new_hits)} newly discovered active IPs...")
        new_counts = {}
        
        # Count densities of newly discovered IPs
        for ip_str in new_hits["ip"]:
            try:
                ip = ipaddress.IPv6Address(ip_str)
                prefix = str(ipaddress.IPv6Network(f"{ip}/48", strict=False))
                new_counts[prefix] = new_counts.get(prefix, 0) + 1
            except ValueError:
                continue
        
        logger.info(f"Found {len(new_counts)} unique /48 prefixes. Merging datasets...")
        
        # Vectorized merge for efficiency
        new_df = pd.DataFrame.from_dict(new_counts, orient='index', columns=['density'])
        merged_df = features_df.add(new_df, fill_value=0)
        merged_df['density'] = merged_df['density'].astype(int)
        
        # Save merged features
        merged_df.index.name = "prefix"
        merged_df.reset_index(inplace=True)
        merged_df.to_csv(paths['features'], index=False)
        
        logger.success(f"Features built successfully: {len(merged_df)} prefixes")
        return True
        
    except Exception as e:
        logger.error(f"Feature building failed: {str(e)}")
        return False


def train_model(input_phase: str, current_phase: str, paths: dict, logger: PipelineLogger) -> bool:
    """
    Train LightGBM model on features with model merging/accumulation
    
    - Loads existing models if available (to merge with current)
    - Trains new model on current features
    - Saves as: prefix_model_<current_phase>.pkl
    """
    logger.section("STEP 2: Training Model")
    
    try:
        from lightgbm import LGBMClassifier
        from sklearn.metrics import classification_report
        import numpy as np
        
        logger.info("Loading updated features...")
        data = pd.read_csv(paths['features'])
        
        # Sanitize data
        data["density"] = data["density"].fillna(0).astype(int)
        data["log_density"] = np.log1p(data["density"])
        
        X = data[["density", "log_density"]]
        y = (data["density"] > 10).astype(int)
        
        logger.info("Training LightGBM Classifier...")
        logger.info(f"  Training data: {len(data)} prefixes")
        logger.info(f"  Active prefixes: {y.sum()} ({y.sum()/len(y)*100:.1f}%)")
        
        model = LGBMClassifier(
            n_estimators=300,
            max_depth=-1,
            learning_rate=0.05,
            class_weight="balanced",
            random_state=42
        )
        
        model.fit(X, y)
        
        # Performance report
        y_pred = model.predict(X)
        logger.info("\n--- Model Performance Benchmark ---")
        print(classification_report(y, y_pred, target_names=["Inactive Prefix", "Active Prefix"]))
        logger.info("-----------------------------------")
        
        # Save model with current phase
        joblib.dump(model, paths['model_pkl'])
        logger.success(f"Model trained and saved to: {paths['model_pkl'].name}")
        logger.info(f"  Input phase: {input_phase}")
        logger.info(f"  Current phase: {current_phase}")
        
        # Also keep a latest model for backward compatibility (if needed)
        latest_model_path = paths['models'] / "prefix_model_latest.pkl"
        joblib.dump(model, latest_model_path)
        logger.info(f"Also saved as: {latest_model_path.name} (latest)")
        
        return True
        
    except Exception as e:
        logger.error(f"Model training failed: {str(e)}")
        return False


def generate_candidates(input_phase: str, current_phase: str, paths: dict, logger: PipelineLogger) -> bool:
    """
    Generate candidate addresses from trained model
    
    - Loads model from current_phase
    - Generates candidates using heuristics + random selection
    - Output: candidates_<current_phase>.parquet
    """
    logger.section("STEP 3: Generating Candidates")
    
    try:
        logger.info(f"Loading model and features...")
        logger.info(f"  Model: {paths['model_pkl'].name}")
        
        model = joblib.load(paths['model_pkl'])
        data = pd.read_csv(paths['features'])
        
        # Feature engineering
        data["log_density"] = data["density"].apply(
            lambda x: __import__("math").log1p(x)
        )
        
        # Predict active prefixes
        pred = model.predict(data[["density", "log_density"]])
        active = data[pred == 1].copy()
        
        # Configuration
        PATTERNS = [1, 2, 80, 443, 8080, 0x100, 0x200]
        RANDOM_PER_PREFIX = 120
        TARGET_TOTAL = 50_000_000
        
        per_prefix = len(PATTERNS) + RANDOM_PER_PREFIX
        needed_prefixes = math.ceil(TARGET_TOTAL / per_prefix)
        active_prefixes = active["prefix"].tolist()[:needed_prefixes]
        
        logger.info(f"Active prefixes available: {len(active)}")
        logger.info(f"Using prefixes: {len(active_prefixes)}")
        logger.info(f"Target total candidates: {TARGET_TOTAL:,}")
        
        # Load previous candidates to avoid duplicates
        logger.info("Loading historical candidates to avoid duplicates...")
        old_candidates = set()
        
        for file_path in paths['results'].iterdir():
            if file_path.name == paths['output'].name:
                continue
            
            if file_path.suffix == '.parquet':
                logger.info(f" -> Loading Parquet: {file_path.name}")
                df = pd.read_parquet(file_path, columns=["address"])
                old_candidates.update(df["address"].tolist())
            elif file_path.suffix == '.txt':
                logger.info(f" -> Loading Text: {file_path.name}")
                with open(file_path, 'r') as f:
                    old_candidates.update(line.strip() for line in f if line.strip())
        
        logger.info(f"Historical addresses to avoid: {len(old_candidates):,}")
        
        # Generate candidates
        raw_candidates = set()
        logger.info("Generating new unique addresses...")
        
        for idx, prefix in enumerate(active_prefixes):
            if (idx + 1) % max(1, len(active_prefixes) // 10) == 0:
                logger.info(f"  Progress: {idx + 1}/{len(active_prefixes)}")
            
            net = ipaddress.ip_network(prefix)
            base = int(net.network_address)
            
            # Heuristic patterns (high value)
            for p in PATTERNS:
                raw_candidates.add(str(ipaddress.IPv6Address(base + p)))
            
            # Biased random IIDs (medium value)
            for _ in range(RANDOM_PER_PREFIX):
                rand_int = random.choice([
                    random.randint(0, 2**16),
                    random.randint(0, 2**32),
                    random.getrandbits(64),
                ])
                raw_candidates.add(str(ipaddress.IPv6Address(base + rand_int)))
            
            if len(raw_candidates) >= (TARGET_TOTAL * 1.1):
                break
        
        logger.info("Filtering out historical duplicates...")
        unique_candidates = list(raw_candidates - old_candidates)[:TARGET_TOTAL]
        
        # Save as Parquet
        df_output = pd.DataFrame(unique_candidates, columns=["address"])
        df_output.to_parquet(paths['output'], engine="pyarrow", index=False)
        
        logger.success(f"Generated {len(df_output):,} unique new candidates")
        logger.info(f"Output saved to: {paths['output'].name}")
        logger.info(f"  Input phase: {input_phase}")
        logger.info(f"  Current phase: {current_phase}")
        
        return True
        
    except Exception as e:
        logger.error(f"Candidate generation failed: {str(e)}")
        return False


def upload_to_cloud(current_phase: str, paths: dict, logger: PipelineLogger) -> bool:
    """
    Upload candidates to Google Cloud Storage
    Uses current_phase in filename
    """
    logger.section("STEP 4: Uploading to Google Cloud Storage")
    
    if not paths['output'].exists():
        logger.error(f"Output file not found: {paths['output']}")
        return False
    
    try:
        gcs_bucket = "gs://ipv6-crawler-batches/batches/"
        gcs_filename = f"candidates_{current_phase}.parquet"
        gcs_path = f"{gcs_bucket}{gcs_filename}"
        
        logger.info(f"Uploading to: {gcs_path}")
        logger.info(f"File size: {paths['output'].stat().st_size / (1024**2):.2f} MB")
        
        cmd = ["gcloud", "storage", "cp", str(paths['output']), gcs_path]
        logger.info(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            logger.success(f"Successfully uploaded to: {gcs_path}")
            logger.info(f"Command output: {result.stdout}")
            return True
        else:
            logger.error(f"Upload failed with code {result.returncode}")
            logger.error(f"stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Upload timed out (>600 seconds)")
        return False
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return False


def update_dashboard(input_phase: str, logger: PipelineLogger) -> bool:
    """
    Update dashboard data with current phase metrics
    Appends to historical data (does not replace)
    """
    logger.section("BONUS: Updating Dashboard Data")
    
    try:
        # Import the dashboard generator
        sys.path.insert(0, str(Path(__file__).parent))
        from generate_dashboard_data import generate_dashboard_data
        
        logger.info(f"Generating dashboard data for phase: {input_phase}")
        
        # Generate dashboard data with current phase marked as latest
        result = generate_dashboard_data(current_phase=input_phase)
        
        if result:
            logger.success(f"Dashboard updated with {result.get('total_phases', 0)} historical phases")
            logger.info(f"Total records across all phases: {result['scan_stats']['total']}")
            return True
        else:
            logger.error("Dashboard generation returned no data")
            return False
            
    except Exception as e:
        logger.error(f"Dashboard update failed: {str(e)}")
        # Don't fail the pipeline for dashboard update
        return True  # Return True to not block pipeline


def main():
    """Main pipeline orchestration with dual-phase system"""
    
    # Argument validation
    if len(sys.argv) != 2:
        print("Usage: python3 pipeline.py <input_phase>")
        print("  where <input_phase> is in format: ddmmyy (e.g., 21_04_26)")
        print("  This is the date of the processed_metrics_*.csv file")
        print("")
        print("PHASES:")
        print("  Input Phase:   Date of processed_metrics_<input_phase>.csv")
        print("  Current Phase: Today's date (auto-detected for outputs)")
        sys.exit(1)
    
    input_phase = sys.argv[1]
    
    if not validate_phase(input_phase):
        print(f"Error: Invalid input_phase format '{input_phase}'")
        print("Expected format: ddmmyy (e.g., 21_04_26 for April 21, 2026)")
        sys.exit(1)
    
    # Auto-detect current phase (today's date)
    current_phase = datetime.now().strftime("%d_%m_%y")
    
    # Initialize logger
    logger = PipelineLogger(f"{input_phase} → {current_phase}")
    logger.section(f"IPv6 Crawler Pipeline - Dual Phase Execution")
    
    # Set base path
    base_path = Path(__file__).parent.parent
    
    # Setup paths
    paths = setup_working_environment(input_phase, current_phase, base_path, logger)
    
    logger.info(f"Base directory: {base_path}")
    logger.info(f"Input phase (data): {input_phase}")
    logger.info(f"Current phase (output): {current_phase}")
    logger.info(f"Input file: {paths['input'].name}")
    logger.info(f"Output model: {paths['model_pkl'].name}")
    logger.info(f"Output candidates: {paths['output'].name}")
    
    # Execute pipeline
    success = True
    
    if not build_features(input_phase, paths, logger):
        success = False
    elif not train_model(input_phase, current_phase, paths, logger):
        success = False
    elif not generate_candidates(input_phase, current_phase, paths, logger):
        success = False
    elif not upload_to_cloud(current_phase, paths, logger):
        success = False
    elif not update_dashboard(input_phase, logger):
        # Don't fail pipeline if dashboard update fails
        logger.error("Dashboard update failed, but continuing...")
    
    # Final summary
    logger.section("Pipeline Summary")
    
    if success:
        elapsed = datetime.now() - logger.start_time
        logger.success(f"✓ COMPLETE - All steps finished successfully in {elapsed}")
        logger.info(f"Candidates: gs://ipv6-crawler-batches/batches/candidates_{current_phase}.parquet")
        logger.info(f"Model: {paths['model_pkl'].name}")
        return 0
    else:
        elapsed = datetime.now() - logger.start_time
        logger.error(f"✗ FAILED - Pipeline did not complete in {elapsed}")
        logger.error("Check logs above for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
