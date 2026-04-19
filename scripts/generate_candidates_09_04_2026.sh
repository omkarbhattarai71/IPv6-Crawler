#!/bin/bash
#SBATCH --job-name=generate_candidates_09_04_2026.py
#SBATCH --time=12:00:00
#SBATCH --output=generate_candidates_09_04_2026.log
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G
#SBATCH --gres=gpu:4

start=$(date +%s)
echo "Started at: $(date)"

python3 generate_candidates_09_04_2026.py

end=$(date +%s)
echo "Finished at: $(date)"
echo "Total time: $((end - start)) seconds"
