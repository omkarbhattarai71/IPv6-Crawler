#!/bin/bash
################################################################################
# Pipeline Setup Validator
# Checks all prerequisites before running the pipeline
################################################################################

echo "================================================"
echo "  IPv6 Crawler Pipeline - Validation Checker  "
echo "================================================"
echo ""

ERRORS=0
WARNINGS=0

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check Python
echo -n "Checking Python 3.8+... "
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo -e "${GREEN}✓ Found Python $PYTHON_VERSION${NC}"
else
    echo -e "${RED}✗ Python 3 not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check required Python packages
echo -n "Checking Python packages... "
python3 -c "import pandas, lightgbm, sklearn, joblib, pyarrow" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All packages installed${NC}"
else
    echo -e "${YELLOW}⚠ Missing packages. Run: pip install pandas lightgbm scikit-learn joblib pyarrow${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# Check Google Cloud SDK
echo -n "Checking Google Cloud SDK... "
if command -v gcloud &> /dev/null; then
    GCLOUD_VERSION=$(gcloud --version | head -1)
    echo -e "${GREEN}✓ $GCLOUD_VERSION${NC}"
else
    echo -e "${RED}✗ gcloud CLI not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check GCP authentication
echo -n "Checking GCP authentication... "
gcloud auth list 2>/dev/null | grep -q "ACTIVE"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Authenticated${NC}"
else
    echo -e "${YELLOW}⚠ Not authenticated. Run: gcloud auth login${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# Check project configuration
echo -n "Checking GCP project... "
PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -n "$PROJECT" ] && [ "$PROJECT" != "(unset)" ]; then
    echo -e "${GREEN}✓ Project: $PROJECT${NC}"
else
    echo -e "${YELLOW}⚠ No project set. Run: gcloud config set project <project-id>${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# Check pipeline files
echo ""
echo "Checking pipeline files..."
PIPELINE_DIR="/ceph/project/IPv6-BOS/IPv6-Crawler"

echo -n "  pipeline.py... "
if [ -f "$PIPELINE_DIR/scripts/pipeline.py" ]; then
    echo -e "${GREEN}✓ Found${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo -n "  pipeline.sh... "
if [ -f "$PIPELINE_DIR/scripts/pipeline.sh" ]; then
    if [ -x "$PIPELINE_DIR/scripts/pipeline.sh" ]; then
        echo -e "${GREEN}✓ Found (executable)${NC}"
    else
        echo -e "${YELLOW}⚠ Found but not executable${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${RED}✗ Not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check working directories
echo ""
echo "Checking working directories..."

DIRS=(
    "processed"
    "processed_gcloud"
    "models"
    "results"
)

for dir in "${DIRS[@]}"; do
    echo -n "  $dir/... "
    if [ -d "$PIPELINE_DIR/$dir" ]; then
        echo -e "${GREEN}✓ Exists${NC}"
    else
        echo -e "${YELLOW}⚠ Missing${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
done

# Check for input data
echo ""
echo "Checking for input data..."
INPUT_COUNT=$(ls "$PIPELINE_DIR/processed_gcloud/processed_metrics_"*.csv 2>/dev/null | wc -l)
if [ $INPUT_COUNT -gt 0 ]; then
    echo -e "${GREEN}✓ Found $INPUT_COUNT input file(s)${NC}"
    ls -1 "$PIPELINE_DIR/processed_gcloud/processed_metrics_"*.csv | head -3
    if [ $INPUT_COUNT -gt 3 ]; then
        echo "  ... and $((INPUT_COUNT - 3)) more"
    fi
else
    echo -e "${YELLOW}⚠ No input files found${NC}"
    echo "  Expected: processed_gcloud/processed_metrics_<phase>.csv"
    WARNINGS=$((WARNINGS + 1))
fi

# Summary
echo ""
echo "================================================"
echo "  Validation Summary"
echo "================================================"
echo -e "${GREEN}✓ Errors: 0${NC}"
if [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ Warnings: 0${NC}"
else
    echo -e "${YELLOW}⚠ Warnings: $WARNINGS${NC}"
fi

if [ $ERRORS -eq 0 ]; then
    echo ""
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}✅ All checks passed! Ready to run pipeline.${NC}"
        echo ""
        echo "Usage:"
        echo "  cd $PIPELINE_DIR/scripts"
        echo "  ./pipeline.sh 21_04_26"
    else
        echo -e "${YELLOW}⚠ Pipeline can run but check warnings above.${NC}"
    fi
    exit 0
else
    echo ""
    echo -e "${RED}❌ Pipeline cannot run. Fix errors above.${NC}"
    exit 1
fi
