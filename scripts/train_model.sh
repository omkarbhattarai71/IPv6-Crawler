#!/bin/bash
#SBATCH --job-name=train_model
#SBATCH --time=12:00:00
#SBATCH --output=train_model.log
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G

start=$(date +%s)
echo "Started at: $(date)"

python3 train_model.py

end=$(date +%s)
echo "Finished at: $(date)"
echo "Total time: $((end - start)) seconds"
