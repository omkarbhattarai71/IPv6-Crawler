#!/bin/bash
#SBATCH --job-name=data_info
#SBATCH --time=12:00:00
#SBATCH --output=data_info.log
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G

OUTPUT_FILE="../processed/data_info_results.csv"

echo "file_name,file_size_human,file_size_bytes,line_count" > $OUTPUT_FILE

FILES=(
    "/ceph/project/IPv6-BOS/IPv6-Crawler/processed/clean_ipv6.txt"
    "/ceph/project/IPv6-BOS/IPv6-Crawler/processed/prefix_counts.txt"
    "/ceph/project/IPv6-BOS/IPv6-Crawler/dataset/latest-data/apd/2026-02-12-aliased.txt"
    "/ceph/project/IPv6-BOS/IPv6-Crawler/dataset/latest-data/input/2026-02-12-input.txt"
)

echo "===== Starting file analysis at $(date) ====="

for FILE in "${FILES[@]}"; do
    echo ""
    echo "------------------------------------------------------------"
    echo "Processing file: $FILE"
    echo "Start time: $(date)"
    echo "------------------------------------------------------------"

    if [[ -f "$FILE" ]]; then

        echo "[INFO] Getting file size..."
        SIZE_HUMAN=$(ls -lh "$FILE" | awk '{print $5}')
        SIZE_BYTES=$(stat -c %s "$FILE")
        echo "[OK] Size: $SIZE_HUMAN ($SIZE_BYTES bytes)"

        echo "[INFO] Counting lines (this may take a long time)..."
        echo "[INFO] Progress updates every ~10 seconds."

        # Background progress indicator
        (
            while true; do
                echo "[PROGRESS] Still counting lines at $(date)..."
                sleep 10
            done
        ) &
        PROGRESS_PID=$!

        # Actual line counting
        LINE_COUNT=$(wc -l < "$FILE")

        # Stop progress indicator
        kill $PROGRESS_PID 2>/dev/null

        echo "[OK] Line count: $LINE_COUNT"

        echo "[INFO] Writing results to CSV..."
        echo "$(basename "$FILE"),$SIZE_HUMAN,$SIZE_BYTES,$LINE_COUNT" >> $OUTPUT_FILE

        echo "Finished processing $FILE at $(date)"

    else
        echo "[ERROR] File not found: $FILE"
        echo "$(basename "$FILE"),NOT_FOUND,0,0" >> $OUTPUT_FILE
    fi

done

echo ""
echo "===== Analysis complete at $(date) ====="
echo "Results saved to $OUTPUT_FILE"
