#!/bin/bash
#SBATCH --job-name=generate_candidates_21_04_26.py
#SBATCH --time=12:00:00
#SBATCH --output=generate_candidates_21_04_26.log
#SBATCH --cpus-per-task=8
#SBATCH --mem=32
#SBATCH --gres=gpu:2

start=$(date +%s)
echo "Started at: $(date)"

python3 generate_candidates_21_04_26.py

end=$(date +%s)
echo "Finished at: $(date)"
echo "Total time: $((end - start)) seconds"
