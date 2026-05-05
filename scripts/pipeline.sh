#!/bin/bash
################################################################################
# IPv6 Crawler - Pipeline Launcher
# ================================
# Automates the complete workflow with a single command
# SLURM-compatible for AAU HPC (ailab)
#
# DUAL PHASE SYSTEM:
#   Input Phase:   Date of processed_metrics_*.csv file (e.g., 21_04_26)
#   Current Phase: Today's date for outputs (auto-detected)
#
# Usage (Local):
#   ./pipeline.sh 21_04_26
#
# Usage (SLURM - AAU HPC):
#   sbatch pipeline.sh 21_04_26
#   sbatch --job-name=ipv6-21_04_26 pipeline.sh 21_04_26
#
# INPUT FORMAT: ddmmyy (e.g., 21_04_26 from processed_metrics_21_04_26.csv)
# OUTPUT: Uses current date (e.g., candidates_04_05_26.parquet if today is May 4, 2026)
#
# If no input_phase provided to sbatch, uses current date automatically
################################################################################

#SBATCH --job-name=ipv6-pipeline
#SBATCH --output=slurm-output.log
#SBATCH --error=slurm-output.err
#SBATCH --time=12:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
# Note: Using default partition (l4)
# Available on ailab: l4 (GPU), vmware
# Override with: sbatch -p vmware pipeline.sh (or -p l4 explicitly)

set -e

# Use project root directly (hardcoded for reliability with SLURM)
BASE_DIR="/ceph/project/IPv6-BOS/IPv6-Crawler"
SCRIPT_DIR="$BASE_DIR/scripts"
PYTHON_SCRIPT="$SCRIPT_DIR/pipeline.py"

# Ensure logs directory exists
mkdir -p "$BASE_DIR/logs" 2>&1 || echo "Failed to create logs directory"

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Determine input_phase from argument or use current date
if [ $# -eq 1 ]; then
    INPUT_PHASE=$1
elif [ $# -eq 0 ]; then
    # Auto-generate input_phase from current date if not provided
    # Format: ddmmyy (e.g., 04_05_26 for May 4, 2026)
    INPUT_PHASE=$(date +%d_%m_%y)
    echo -e "${YELLOW}No input_phase provided. Using current date: ${INPUT_PHASE}${NC}"
else
    echo -e "${RED}Error: Too many arguments${NC}"
    echo "Usage: $0 [input_phase]"
    echo "  where <input_phase> is in format: ddmmyy (e.g., 21_04_26)"
    echo "  This should match: processed_metrics_<input_phase>.csv"
    echo "  If not provided, uses current date automatically"
    exit 1
fi

# Validate input_phase format
if ! [[ $INPUT_PHASE =~ ^[0-9]{2}_[0-9]{2}_[0-9]{2}$ ]]; then
    echo -e "${RED}Error: Invalid input_phase format '${INPUT_PHASE}'${NC}"
    echo "Expected format: ddmmyy (e.g., 21_04_26)"
    exit 1
fi

# Auto-detect current phase (today's date)
CURRENT_PHASE=$(date +%d_%m_%y)

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║          IPv6 Crawler - Complete Pipeline Automation               ║"
echo "║                  DUAL-PHASE SLURM Compatible                       ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Print SLURM job info if running under SLURM
if [ -n "$SLURM_JOB_ID" ]; then
    echo -e "${BLUE}SLURM Job Information:${NC}"
    echo "  Job ID: $SLURM_JOB_ID"
    echo "  Job Name: $SLURM_JOB_NAME"
    echo "  Partition: $SLURM_JOB_PARTITION"
    echo "  CPUs: $SLURM_CPUS_PER_TASK"
    echo "  Memory: $SLURM_MEM_PER_NODE MB"
    echo "  Time Limit: $SLURM_TIME_LIMIT"
    echo ""
fi

echo -e "${YELLOW}Phase Information:${NC}"
echo -e "  Input Phase (Data):     ${GREEN}${INPUT_PHASE}${NC}"
echo -e "  Current Phase (Output): ${GREEN}${CURRENT_PHASE}${NC}"
echo -e "${YELLOW}Start Time: ${GREEN}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo "Starting pipeline..."
echo ""

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "${RED}Error: Python script not found: $PYTHON_SCRIPT${NC}"
    exit 1
fi

# Check if input file exists
INPUT_FILE="$BASE_DIR/processed_gcloud/processed_metrics_${INPUT_PHASE}.csv"
if [ ! -f "$INPUT_FILE" ]; then
    echo -e "${RED}Error: Input file not found: $INPUT_FILE${NC}"
    echo "Please ensure the GCP scan results are downloaded first:"
    echo "  gsutil cp gs://your-bucket/processed_metrics_${INPUT_PHASE}.csv $INPUT_FILE"
    exit 1
fi

echo -e "${GREEN}✓ Input file found: $INPUT_FILE${NC}"
echo ""

# Run the pipeline with input_phase parameter
echo -e "${YELLOW}Activating Python environment and running pipeline...${NC}"
echo ""

# Use venv Python explicitly
VENV_PYTHON="$BASE_DIR/venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}Error: Virtual environment Python not found: $VENV_PYTHON${NC}"
    exit 1
fi

if "$VENV_PYTHON" "$PYTHON_SCRIPT" "$INPUT_PHASE"; then
    END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║ ✓ Pipeline completed successfully!                               ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}End Time: ${END_TIME}${NC}"
    echo -e "${GREEN}Results:${NC}"
    echo -e "  Candidates: results/candidates_${CURRENT_PHASE}.parquet"
    echo -e "  Model: models/prefix_model_${CURRENT_PHASE}.pkl"
    echo -e "${GREEN}Cloud Path: gs://ipv6-crawler-batches/batches/candidates_${CURRENT_PHASE}.parquet${NC}"
    
    if [ -n "$SLURM_JOB_ID" ]; then
        echo -e "${GREEN}SLURM Job: $SLURM_JOB_ID completed successfully${NC}"
        echo -e "${YELLOW}View logs: cat logs/pipeline_${SLURM_JOB_ID}.log${NC}"
    fi
    
    exit 0
else
    END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║ ✗ Pipeline failed. Check logs above for details.                  ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${RED}End Time: ${END_TIME}${NC}"
    
    if [ -n "$SLURM_JOB_ID" ]; then
        echo -e "${RED}SLURM Job: $SLURM_JOB_ID failed${NC}"
        echo -e "${YELLOW}View logs: cat logs/pipeline_${SLURM_JOB_ID}.log${NC}"
    fi
    
    exit 1
fi
