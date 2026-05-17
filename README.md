# IPv6-Crawler

**Automated IPv6 candidate generation & probing pipeline using LightGBM + GCP + SLURM**

---

## A.  Closed-Loop Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│ AI Lab (AAU ailab)                                              │
│                                                                 │
│ 1. Generate Candidates                                          │
│    sbatch pipeline.sh <phase>                                   │
│              ↓                                                  │
│    Output: parquet → uploaded to GCS                                   │
│              ↓                                                  │
│    gs://ipv6-crawler-batches/batches/candidates_<phase>.parquet │
└────────────────────────┬────────────────────────────────────────┘
                         │ Download
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ GCP VM (europe-west9-b)                                         │
│                                                                 │
│ 2. Run ZMap Crawler                                             │
│    nohup bash crawler_main.sh <phase> > nohup.out 2>&1 &        │
│      Converts .parquet candidates to .txt and starts probing    │
│              ↓                                                  │
│    TCP/ICMP probing (port 80, 443, 8080, etc.)                  │
│              ↓                                                  │
│    Output: processed_metrics_<phase>.csv                        │
│              ↓                                                  │
│    gs://ipv6-crawler-batches/processed_at_vm/...                │
└────────────────────────┬────────────────────────────────────────┘
                         │ Download
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ AI Lab (Analysis & Metrics)                                     │
│                                                                 │
│ 3. Process Results                                              │
│    python scripts/extract_all_metrics.py                        │
│    python scripts/metrics_test.py                               │
│           ↓                                                     │
│    Metrics: precision, recall, response rates, protocols        │
│    Dashboard: update with new phase data                        │
│           ↓                                                     │
│    REPEAT: Loop back to step 1 for next phase                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## B. Quick Start

### Run Pipeline (AI Lab)

```bash
cd /ceph/project/IPv6-BOS/IPv6-Crawler
source venv/bin/activate

# Generate candidates for phase DD_MM_YY
# (e.g., 20_04_26 for April 20, 2026)
sbatch pipeline.sh 20_04_26

# Outputs:
#   - Parquet file: results/candidates_20_04_26.parquet
#   - Uploaded to: gs://ipv6-crawler-batches/batches/candidates_20_04_26.txt
```

### Run Crawler (GCP VM)

```bash
gcloud compute ssh [instance-name] --zone=europe-west9-b

cd ~/IPv6-Scanner/crawl_analysis

# Download candidates and run ZMap
nohup bash crawler_main.sh 20_04_26 > nohup.out 2>&1 &

# Monitor
tail -f nohup.out

# Results uploaded to:
#   gs://ipv6-crawler-batches/processed_at_vm/processed_metrics_20_04_26.csv
```

### Extract Metrics (AI Lab)

```bash
cd /ceph/project/IPv6-BOS/IPv6-Crawler
source venv/bin/activate

# Download results from GCP VM folder
python scripts/extract_all_metrics.py
This generates:
- metrics_report.txt - Human-readable metrics
- metrics_data.csv - Structured data 

# Validation & testing
python scripts/metrics_test.py
# View results
cat test_results.txt

```

---

## C. GCS Bucket Structure

| Path | Content | Updated By |
|------|---------|-----------|
| `gs://ipv6-crawler-batches/batches/` | Candidate .txt files | AI Lab (pipeline.sh) |
| `gs://ipv6-crawler-batches/processed_at_vm/` | Probe results (CSV) | GCP VM (crawler_main.sh) |

---

## D. Configuration

**LightGBM Model:** 300 estimators, learning_rate=0.05, balanced classes  
**Candidate Heuristics:** Patterns [1, 2, 80, 443, 8080, 0x100, 0x200] + 120 random per prefix  
**Active Threshold:** density > 10  
**Probing:** ZMap (TCP 80, 443, 8080, ICMP, UDP/53)

---

## E. Results (7+ Phases)

- **Total probed:** 273,856 + candidates till report was written.
- **Response rate:** 94.2%
- **HTTPS:** 91%, HTTP: 6.5%, ICMP: 7.4%, DNS: 0.2%
- **Single-service:** 93.89%
- **Stability:** σ < 0.4% across phases

---


## F. Troubleshooting

| Issue | Fix |
|-------|-----|
| Pipeline fails: input file missing | Candidates uploaded to GCS batches folder |
| Crawler hangs | `tail -f nohup.out` to debug |
| Results not found | Check `gs://ipv6-crawler-batches/processed_at_vm/` |
| Metrics extraction error | Run `python scripts/extract_all_metrics.py` after crawler completes |

---

## G. Limitations

**Infrastructure Constraints:**
- AI Lab infrastructure lacks native IPv6 support, preventing active probing from the local environment. GCP VMs were deployed to overcome this limitation.

**Resource Limitations:**
- GCP VM instance is constrained by memory (16GB), CPU (4 cores), and network bandwidth, limiting concurrent probe rates.
- Cost-factor restrictions limit continuous 24/7 scanning operations. Probing is conducted in discrete phases to balance accuracy and budget.

**Probing Limitations:**
- Rate-limiting imposed by target networks and ISP policies restricts probe throughput (avg. 1K-5K packets/sec per phase).
- Single vantage point (europe-west9-b region) introduces geographic bias in IPv6 reachability measurements.
- Measurement window (April 19 - May 13, 2026, 25 days) captures a temporal snapshot and may not represent long-term trends.

**Data Constraints:**
- Response rates (94.2%) reflect firewall filtering and network policies that may hide active infrastructure behind restrictive ACLs.
- Protocol distribution heavily weighted toward HTTPS (91%) due to focus on HTTP/HTTPS services; other IPv6-enabled services may be underrepresented.
- Candidate generation relies on heuristic patterns and random sampling, potentially missing non-standard service deployments.
