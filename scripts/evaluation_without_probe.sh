#!/bin/bash
#SBATCH --job-name=evaluation_without_probe
#SBATCH --time=12:00:00
#SBATCH --output=evaluation_without_probe.log
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G

start=$(date +%s)
echo "Started at: $(date)"

python3 evaluation_without_probe.py

end=$(date +%s)
echo "Finished at: $(date)"
echo "Total time: $((end - start)) seconds"
