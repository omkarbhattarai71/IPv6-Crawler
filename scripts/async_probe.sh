#!/bin/bash
#SBATCH --job-name=async_probe
#SBATCH --time=12:00:00
#SBATCH --output=async_probe.log
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G
#SBATCH --gres=gpu:4

start=$(date +%s)
echo "Started at: $(date)"

python3 async_probe.py

end=$(date +%s)
echo "Finished at: $(date)"
echo "Total time: $((end - start)) seconds"
