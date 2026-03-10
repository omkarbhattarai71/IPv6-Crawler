#!/bin/bash
#SBATCH --job-name=extract_prefix
#SBATCH --time=12:00:00
#SBATCH --output=extractPrefix.log
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G

python3 extract_prefix.py

