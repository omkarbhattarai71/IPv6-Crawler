# Guide to Run - Semester Project-II

This document provides the complete workflow for running the IPv6-Crawler pipeline. The system operates in a closed loop between the AAU AI-Lab (for machine learning and candidate generation) and a Google Cloud Platform (GCP) Virtual Machine (for active probing).

## 1. Prerequisites and Data Source

If you need to fetch the latest dataset prior to starting:
- **Data Source:** [IPv6 Hitlist Service - APD](https://alcatraz.net.in.tum.de/ipv6-hitlist-service/registered/apd/)
- **Username:** `obhatt25-at-student-aau-dk`
- **Password:** `Pa0aisei6ai7`

Download the recent aliased and non-aliased data into the `dataset` folder if you are initializing the pipeline from scratch.
# IPv6-Crawler

```text
IPv6-Crawler/
├── dashboard/
├── dataset/
├── models/
│   ├── prefix_model_{phase}.pkl
│   └── prefix_model_latest.pkl
├── processed/
│   ├── clean_ipv6.txt
│   ├── data_info_results.csv
│   ├── features.csv
│   └── prefix_counts.txt
├── logs/
│   ├── phase_{phase}_{jobid}.err
│   └── phase_{phase}_{jobid}.log
├── results/
│   ├── candidates_{phase}.csv
├── scripts/
│   ├── pipeline.sh
│   ├── pipeline.py
│   ├── generate_dashboard_data.py
│   ├── build_features.py
│   ├── extract_prefix.py
│   ├── remove_aliases.py
│   ├── extract_all_metrics.py
│   ├── metrics_test.py
│   └── other initially created individual slurm batches
├── README.md
└── venv/

```

##  2. The Continuous Execution Pipeline (Everyday Workflow)

Once initialized, the pipeline only requires two alternating steps.

### Step A: Generate Candidates (AAU AI-Lab)
```Note: It is under the``` **```IPv6-Crawler-main```** ```zip folder ``` - [IPv6-Crawler - (github link)](https://github.com/omkarbhattarai71/IPv6-Crawler.git)
1. Log in to the [AAU AI-Lab](https://hpc.aau.dk/ai-lab/guides/login/#_tabbed_1_1).
2. Navigate to the project directory:
   ```bash
   cd /ceph/project/IPv6-BOS/IPv6-Crawler/
   ```
3. *(First time only)* Verify your `gcloud` installation. If it fails, install and authenticate:
   ```bash
   curl https://sdk.cloud.google.com | bash  # Press Enter, Yes, and Enter when prompted
   exec -l $SHELL
   gcloud auth login  # Follow URL in browser and paste the verification code
   gsutil mb -l europe-west1 gs://ipv6-crawler-batches  # Creates the storage bucket
   ```
4. Run the automated pipeline script:
   ```bash
   cd scripts
   sbatch pipeline.sh {phase}
   ```
   *Note: `{phase}` is the date identifier (format: `DD_MM_YY`) from the latest metrics file located in the GCS bucket at `ipv6-crawler-batches/processed_at_vm/`.*

**What happens here?** The batch job generates new candidates, updating the model (`.pkl`), logs, and dashboard data (`.json`). The results are saved as parachute (`.parquet`) files to the GCS folder: `ipv6-crawler-batches/batches/`.

### Step B: Active Probing (Google Cloud VM)
```Note: It is under the``` **```IPv6-Scanner-main```** ```zip folder ``` - [IPv6-Scanner (github link)](https://github.com/omkarbhattarai71/IPv6-Scanner.git)
1. Log in to Google Cloud using the authorized Gmail account ( It will be made accessible upon request and where to make request is given at the end).
2. Select the project named **ipv6** and navigate to **Compute Engine > VM instances**.
3. Start the instance named **`ipv6-crawler`** (Do NOT use `ipv6-crawler-vm` if you are logging in from our virtual machine).
4. Click **SSH** to access the terminal.
5. Set necessary permissions and activate the virtual environment:
   ```bash
   chmod -R 755 /home/ubuntu/IPv6-Scanner
   cd ~/IPv6-Scanner/crawl_analysis
   source ~/IPv6-Scanner/venv/bin/activate
   ```
6. Run the active crawler in the background:
   ```bash
   nohup bash crawler_main.sh {phase} > nohup.out 2>&1 &
   ```
   *Note: Ensure `{phase}` matches the date format `DD_MM_YY` of the latest candidate file arrived in the bucket.*

**What happens here?** The VM pulls the candidates, probes them, and automatically uploads the newly probed metrics (`processed_metrics_{phase}.csv`) back into the cloud bucket to be picked up by Step A. **Repeat Step A and Step B continuously.**

---

## 3. Manual Pipeline Initialization (Scratch Setup)

If you are running the project from scratch (brand new downloaded data), execute the following sequentially on AI-Lab before joining the continuous loop above:

1. Update the input/output files to reflect your newly downloaded recent files.
2. Filter aliases:
   ```bash
   sbatch remove_aliases.sh
   ```
3. Extract prefixes:
   ```bash
   sbatch extract_prefix.sh
   ```
4. Build features:
   ```bash
   sbatch build_features.sh
   ```
5. Train the model:
   ```bash
   sbatch train_model.sh
   ```
6. Generate candidates:
   ```bash
   sbatch generate_candidates.sh
   ```
7. Manually upload the output `candidates_{phase}.parquet` to the GCS bucket.
8. Follow **Step B** above to perform the first crawl and obtain the first `processed_metrics_{phase}.csv`.
9. Then, run the automated pipeline script:
   ```bash
   cd scripts
   sbatch pipeline.sh {phase}  ({phase} dhase comes from the processed_metrics_{phase})
   ```
---

## Deployed web dashboard
[Predictive IPv6 Crawling](https://ipv6-crawler.vercel.app/)

---

##  Support & Contacts
If you are an external sensor, reviewer, or encountering issues accessing the AI-Lab or Google Cloud environment, please contact the team:
- `omkarbhattarai71@gmail.com`
- `yg03u@student.aau.dk` or `obhatt25@student.aau.dk`