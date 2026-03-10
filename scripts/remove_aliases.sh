#!/bin/bash
#SBATCH --job-name=remove_aliases
#SBATCH --time=12:00:00
#SBATCH --output=myjob.log
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G

python3 remove_aliases.py

