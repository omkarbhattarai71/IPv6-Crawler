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
#SBATCH --time=4:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=4
# Note: Using default partition (l4)
# Available on ailab: l4 (GPU), vmware
# Override with: sbatch -p vmware pipeline.sh (or -p l4 explicitly)

set -e

# Use project root directly (hardcoded for reliability with SLURM)
BASE_DIR="/ceph/project/IPv6-BOS/IPv6-Crawler"
SCRIPT_DIR="$BASE_DIR/scripts"
PYTHON_SCRIPT="$SCRIPT_DIR/pipeline.py"

# Setup GCP credentials for SLURM jobs - use gcloud application-default credentials
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/application_default_credentials.json"

# Ensure logs directory exists
mkdir -p "$BASE_DIR/logs" 2>&1 || echo "Failed to create logs directory"

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging setup
LOG_DIR="$BASE_DIR/logs"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
JOB_ID="${SLURM_JOB_ID:-local_${TIMESTAMP}}"

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

# Setup phase-based logging (INPUT_PHASE only for easy searching)
LOG_PREFIX="${INPUT_PHASE}"
LOG_FILE="$LOG_DIR/phase_${LOG_PREFIX}_${JOB_ID}.log"
ERR_FILE="$LOG_DIR/phase_${LOG_PREFIX}_${JOB_ID}.err"
STATUS_FILE="$LOG_DIR/phase_${LOG_PREFIX}.status"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║          IPv6 Crawler - Complete Pipeline Automation               ║"
echo "║                  DUAL-PHASE SLURM Compatible                       ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Log header to file (REPLACE if same phase)
{
    echo "============================================================================="
    echo "IPv6 Crawler Pipeline Execution Log"
    echo "============================================================================="
    echo ""
    echo "Execution Start: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Job ID: $JOB_ID"
    echo "Input Phase (Data):     $INPUT_PHASE"
    echo "Current Phase (Output): $CURRENT_PHASE"
    echo ""
} > "$LOG_FILE"  # Use > to REPLACE (not append)

# Print SLURM job info if running under SLURM
if [ -n "$SLURM_JOB_ID" ]; then
    {
        echo "SLURM Job Information:"
        echo "  Job ID: $SLURM_JOB_ID"
        echo "  Job Name: $SLURM_JOB_NAME"
        echo "  Partition: $SLURM_JOB_PARTITION"
        echo "  CPUs: $SLURM_CPUS_PER_TASK"
        echo "  Memory: $SLURM_MEM_PER_NODE MB"
        echo "  Time Limit: $SLURM_TIME_LIMIT"
        echo ""
    } >> "$LOG_FILE"  # Use >> to append after first write
fi

{
    echo "Phase Information:"
    echo "  Input Phase (Data):     $INPUT_PHASE"
    echo "  Current Phase (Output): $CURRENT_PHASE"
    echo "  Start Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "  Starting pipeline..."
    echo ""
} >> "$LOG_FILE"

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    {
        echo "✗ ERROR: Python script not found: $PYTHON_SCRIPT"
    } >> "$LOG_FILE"
    cp "$LOG_FILE" "$ERR_FILE"
    echo "FAILED at: validation" >> "$STATUS_FILE"
    exit 1
fi

# Setup input file path
INPUT_FILE="$BASE_DIR/processed_gcloud/processed_metrics_${INPUT_PHASE}.csv"
GCS_SOURCE="gs://ipv6-crawler-batches/processed_at_vm/processed_metrics_${INPUT_PHASE}.csv"

# Check if input file exists locally, if not download from GCS
if [ ! -f "$INPUT_FILE" ]; then
    {
        echo "📥 Input file not found locally: $INPUT_FILE"
        echo "Attempting to download from GCS: $GCS_SOURCE"
        echo ""
    } >> "$LOG_FILE"
    
    # Try to download from GCS using gcloud storage (handles ADC better than gsutil)
    if gcloud storage cp "$GCS_SOURCE" "$INPUT_FILE" 2>&1 >> "$LOG_FILE"; then
        {
            echo "✓ Successfully downloaded from GCS"
            echo ""
        } >> "$LOG_FILE"
    else
        DOWNLOAD_STATUS=$?
        {
            echo "✗ ERROR: Failed to download from GCS (exit code: $DOWNLOAD_STATUS)"
            echo "  Source: $GCS_SOURCE"
            echo "  Target: $INPUT_FILE"
            echo ""
            echo "Possible causes:"
            echo "  1. File not found in GCS bucket"
            echo "  2. GCP authentication not configured"
            echo "     Run: gcloud auth application-default login"
            echo "  3. No permission to access the bucket"
            echo ""
        } >> "$LOG_FILE"
        
        # Copy error to err file
        {
            echo "GCS Download Failed:"
            tail -15 "$LOG_FILE" | grep -i "error\|failed\|permission\|servicexception\|commandexception"
        } > "$ERR_FILE"
        
        echo "FAILED at: gcs_download - Could not download $GCS_SOURCE" >> "$STATUS_FILE"
        exit 1
    fi
else
    {
        echo "✓ Input file found locally: $INPUT_FILE"
        echo ""
    } >> "$LOG_FILE"
fi

# Run the pipeline with input_phase parameter
{
    echo "Activating Python environment and running pipeline..."
    echo ""
} >> "$LOG_FILE"

# Use venv Python explicitly
VENV_PYTHON="$BASE_DIR/venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    {
        echo "✗ ERROR: Virtual environment Python not found: $VENV_PYTHON"
    } >> "$LOG_FILE"
    cp "$LOG_FILE" "$ERR_FILE"
    echo "FAILED at: venv_validation - Python not found" >> "$STATUS_FILE"
    exit 1
fi

# Run Python pipeline and capture output to log file
if "$VENV_PYTHON" "$PYTHON_SCRIPT" "$INPUT_PHASE" 2>&1 >> "$LOG_FILE"; then
    PIPELINE_STATUS=0
else
    PIPELINE_STATUS=$?
fi

# Capture errors separately
if [ $PIPELINE_STATUS -ne 0 ]; then
    tail -100 "$LOG_FILE" >> "$ERR_FILE"
fi
if [ $PIPELINE_STATUS -eq 0 ]; then
    END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    {
        echo ""
        echo "=============================================================================="
        echo "✓ Pipeline completed successfully!"
        echo "=============================================================================="
        echo ""
        echo "Execution Summary:"
        echo "  Input Phase:   $INPUT_PHASE"
        echo "  Current Phase: $CURRENT_PHASE"
        echo "  End Time:      $END_TIME"
        echo ""
        echo "Results:"
        echo "  Candidates: results/candidates_${CURRENT_PHASE}.parquet"
        echo "  Model: models/prefix_model_${CURRENT_PHASE}.pkl"
        echo ""
        echo "Cloud Path: gs://ipv6-crawler-batches/batches/candidates_${CURRENT_PHASE}.parquet"
        echo ""
    } >> "$LOG_FILE"
    
    # Record success in status file
    echo "SUCCESS|$(date '+%Y-%m-%d %H:%M:%S')|$INPUT_PHASE|$CURRENT_PHASE|$JOB_ID" >> "$STATUS_FILE"
    
    if [ -n "$SLURM_JOB_ID" ]; then
        {
            echo "SLURM Job: $SLURM_JOB_ID completed successfully"
            echo ""
            echo "📋 Logs:"
            echo "  Main Log:  logs/phase_${LOG_PREFIX}_${JOB_ID}.log"
            echo "  Query:     grep -i 'phase\|error\|failed\|success' logs/phase_${LOG_PREFIX}_*.log"
            echo "  Status:    cat logs/phase_${LOG_PREFIX}.status"
        } >> "$LOG_FILE"
    fi
    
    exit 0
else
    END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    {
        echo ""
        echo "=============================================================================="
        echo "✗ Pipeline FAILED"
        echo "=============================================================================="
        echo ""
        echo "Failure Summary:"
        echo "  Input Phase:   $INPUT_PHASE"
        echo "  Current Phase: $CURRENT_PHASE"
        echo "  End Time:      $END_TIME"
        echo "  Exit Code:     $PIPELINE_STATUS"
        echo ""
        echo "Error Details:"
        echo "  See error messages in section above marked with [✗ ERROR]"
        echo ""
    } >> "$LOG_FILE"
    
    # Capture error reason from log file
    ERROR_REASON=$(grep -i "✗ ERROR" "$LOG_FILE" | tail -1 | sed 's/.*\[✗ ERROR\] //' || echo "Unknown error - check logs")
    
    # Record failure in status file with error reason
    {
        echo "FAILED|$(date '+%Y-%m-%d %H:%M:%S')|$INPUT_PHASE|$CURRENT_PHASE|$JOB_ID"
        echo "Error: $ERROR_REASON"
    } >> "$STATUS_FILE"
    
    # Copy last 50 lines to error file
    tail -50 "$LOG_FILE" > "$ERR_FILE"
    
    if [ -n "$SLURM_JOB_ID" ]; then
        {
            echo "SLURM Job: $SLURM_JOB_ID FAILED"
            echo ""
            echo "📋 Log Files:"
            echo "  Main Log:  logs/phase_${LOG_PREFIX}_${JOB_ID}.log"
            echo "  Error Log: logs/phase_${LOG_PREFIX}_${JOB_ID}.err"
            echo "  Status:    logs/phase_${LOG_PREFIX}.status"
            echo ""
            echo "🔍 View Last 30 Lines:"
            echo "  tail -30 logs/phase_${LOG_PREFIX}_${JOB_ID}.log"
            echo ""
            echo "❌ Last Error:"
            echo "  $ERROR_REASON"
        } >> "$LOG_FILE"
    fi
    
    exit 1
fi
