# IPv6-Crawler

Automated IPv6 candidate generation pipeline using machine learning for active prefix prediction and GCP cloud integration.

## Overview

This project implements a **dual-phase pipeline** that processes IPv6 scan data to generate active address candidates. It uses LightGBM to classify IPv6 /48 prefixes as active or inactive, generates 50M+ candidate addresses, and uploads results to Google Cloud Storage.

**Key Features:**
- ✅ Automated 5-stage pipeline orchestration
- ✅ SLURM integration for HPC batch execution (AAU ailab)
- ✅ Dual-phase system (input data phase + current execution phase)
- ✅ Historical data preservation with automatic date tracking
- ✅ Google Cloud Storage integration
- ✅ Real-time dashboard updates with historical metrics

---

## Requirements

### System
- **Python:** 3.8+
- **OS:** Linux/macOS
- **HPC (optional):** SLURM scheduler (tested on AAU ailab)

### Python Packages
```
pandas>=2.0
numpy
lightgbm>=3.0
scikit-learn
pyarrow
```

### External Tools
- `gsutil` (for Google Cloud Storage uploads)

### Data
- Processed GCP metrics file: `processed_gcloud/processed_metrics_<PHASE>.csv`
  - Format: Phase-based naming (e.g., `processed_metrics_20_04_26.csv` for April 20, 2026)
  - Required columns: IP address, infrastructure provider, success rate

---

## Installation

### 1. Clone Repository
```bash
cd /ceph/project/IPv6-BOS/IPv6-Crawler
```

### 2. Set Up Python Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install pandas numpy lightgbm scikit-learn pyarrow
```

### 3. Verify Setup
```bash
python3 -c "import pandas, lightgbm; print('✓ Dependencies installed')"
```

---

## How to Run

### Local Execution
```bash
cd scripts
./pipeline.sh 20_04_26
```

### SLURM Batch Submission (AAU HPC)
```bash
cd scripts
sbatch pipeline.sh 20_04_26
```

**Parameters:**
- `20_04_26` = Input phase (format: `ddmmyy` matching your data file)
- Output phase auto-detected from current date

**Monitor Job:**
```bash
squeue | grep ipv6-pip        # Check status
tail -f ../logs/pipeline_*.log # View real-time logs
sacct -j <JobID>              # Check completed job
```

---

## Pipeline Stages

### Stage 1: Build Features
- Loads historical features and new GCP scan data
- Extracts /48 IPv6 prefixes
- Calculates prefix densities and activity metrics
- **Output:** `processed/features.csv`

### Stage 2: Train Model
- Trains LightGBM classifier (300 trees, balanced classes)
- Learns prefix activity patterns
- **Output:** `models/prefix_model_<PHASE>.pkl`

### Stage 3: Generate Candidates
- Loads trained model
- Predicts active prefixes from IPv6 address space
- Generates 50M candidate addresses
- Deduplicates against historical candidates
- **Output:** `results/candidates_<PHASE>.parquet`

### Stage 4: Upload to Cloud
- Uploads candidate set to Google Cloud Storage
- **Destination:** `gs://ipv6-crawler-batches/batches/`

### Stage 5: Update Dashboard
- Aggregates metrics across all phases
- Appends to historical data (preserves history)
- Generates dashboard JSON for frontend
- **Output:** `dashboard/src/dashboard_data.json`

---

## File Structure

```
IPv6-Crawler/
├── README.md                           # This file
├── scripts/
│   ├── pipeline.sh                     # Main SLURM launcher
│   ├── pipeline.py                     # Core orchestrator
│   └── generate_dashboard_data.py      # Dashboard metrics
├── processed_gcloud/
│   └── processed_metrics_<PHASE>.csv   # Input GCP data
├── processed/
│   └── features.csv                    # Cumulative features
├── models/
│   ├── prefix_model_<PHASE>.pkl        # Phase-specific model
│   └── prefix_model_latest.pkl         # Symlink to latest
├── results/
│   └── candidates_<PHASE>.parquet      # 50M addresses
├── logs/
│   └── pipeline_<JOBID>.log            # SLURM execution logs
├── dashboard/src/
│   └── dashboard_data.json             # Historical metrics
└── dataset/
    ├── input/                          # Input data
    ├── apd/                            # Anonymized data
    └── latest-data/                    # Current snapshots
```

---

## Dual-Phase System

The pipeline uses **two independent date phases** for flexibility:

### Input Phase
- Date from your processed metrics file (e.g., `20_04_26`)
- Determines which data file to load
- Passed as command argument: `sbatch pipeline.sh 20_04_26`

### Current Phase
- Today's date (auto-detected, e.g., `04_05_26`)
- Used for all output filenames
- Ensures outputs don't overwrite each other

**Example:**
```bash
sbatch pipeline.sh 20_04_26
# Input:  processed_metrics_20_04_26.csv (April 20, 2026 data)
# Output: prefix_model_04_05_26.pkl     (generated May 4, 2026)
#         candidates_04_05_26.parquet   (generated May 4, 2026)
```

---

## Output Files

### Models
- `models/prefix_model_<PHASE>.pkl` - LightGBM classifier
- `models/prefix_model_latest.pkl` - Symlink to most recent

### Candidates
- `results/candidates_<PHASE>.parquet` - 50M IPv6 addresses
- Format: Apache Parquet (efficient, queryable)

### Dashboard
- `dashboard/src/dashboard_data.json` - Historical metrics
  - Aggregate statistics (all-time)
  - Per-phase statistics
  - Top 10 CDNs/providers
  - Marked "is_latest" for current phase

**Dashboard JSON Structure:**
```json
{
  "last_updated": "2026-05-04T19:30:00",
  "scan_stats": { "total": 50M, "success": 35M, "hit_rate": 70.0 },
  "historical_data": [
    {
      "phase": "20_04_26",
      "date": "2026-04-20",
      "is_latest": true,
      "stats": { ... },
      "top_infrastructure": [ ... ]
    }
  ]
}
```

---

## Troubleshooting

### SLURM Job Fails Immediately
```bash
# Check error file
cat logs/pipeline_*.err
# or SLURM output
cat scripts/slurm-output.err

# Verify input file exists
ls processed_gcloud/processed_metrics_<PHASE>.csv

# Check SLURM partitions
sinfo
```

### Missing Input Data
```bash
# Create symlink with correct phase naming
cd processed_gcloud
ln -sf processed_metrics_new_20_04_2026.csv processed_metrics_20_04_26.csv
```

### Python Package Errors
```bash
# Activate venv and reinstall
source venv/bin/activate
pip install --upgrade pandas lightgbm scikit-learn
```

### Job Still Running After Hours
- Large datasets (750M+ prefixes) take 2-3 hours for model training
- Check progress: `tail -f logs/pipeline_*.log`
- Model training is the longest stage (usually 1.5+ hours)

### Dashboard Not Updating
```bash
# Manually trigger dashboard update
cd scripts
source ../venv/bin/activate
python3 -c "from generate_dashboard_data import generate_dashboard_data; generate_dashboard_data(current_phase='20_04_26')"
```

---

## SLURM Configuration (AAU ailab)

### Available Partitions
- `l4` (default, GPU-equipped) - Recommended
- `vmware` - Alternative CPU-only partition

### Override Partition
```bash
sbatch -p vmware pipeline.sh 20_04_26
```

### Job Resources
- **Time:** 3 hours (adjustable with `#SBATCH --time=`)
- **Memory:** 32GB
- **CPUs:** 4 cores

### Monitor All Your Jobs
```bash
squeue --me
sacct --me
```

---

## Pipeline Performance Metrics

| Stage | Typical Duration | Dataset Size |
|-------|-----------------|--------------|
| Build Features | 50-60 min | 752M prefixes |
| Train Model | 60-90 min | Full dataset |
| Generate Candidates | 20-30 min | 50M addresses |
| Upload to Cloud | 5-10 min | ~400MB file |
| Update Dashboard | 5-10 sec | Historical data |
| **Total** | **2-3 hours** | **Full pipeline** |

---

## Cloud Integration

### Google Cloud Storage Upload
- Automatically uploads to: `gs://ipv6-crawler-batches/batches/`
- Requires `gsutil` authentication
- Configure: `gcloud auth login`

### Verify Upload
```bash
gsutil ls gs://ipv6-crawler-batches/batches/candidates_*.parquet
```

---

**Last Updated:** May 4, 2026  
**Status:** ✅ Production Ready  
**Python:** 3.8+  
