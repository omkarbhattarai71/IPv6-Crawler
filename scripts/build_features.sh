#!/bin/bash
#SBATCH --job-name=build_features
#SBATCH --time=12:00:00
#SBATCH --output=build_features.log
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G

start=$(date +%s)
echo "Started at: $(date)"

python3 build_features.py

end=$(date +%s)
echo "Finished at: $(date)"
echo "Total time: $((end - start)) seconds"
