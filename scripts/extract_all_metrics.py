#!/usr/bin/env python3
"""
Comprehensive Thesis Metrics Extraction Script

Extracts ALL experimental data needed for thesis report:
  • LightGBM model configuration
  • Evaluation metrics (precision, recall, F1, accuracy)
  • Thesis metrics (phase statistics, port analysis, temporal trends)
  • Dataset characteristics
  • Candidate generation statistics

Outputs:
  • metrics_report.txt  - Human-readable thesis report
  • metrics_data.csv    - Structured CSV for appendix

Usage:
  python3 extract_all_metrics.py [--include-raw-csv]

Scalable for batch-wise crawling:
  - Automatically detects all phases in processed_gcloud/
  - Processes all phases in scan_history from dashboard
  - Ready to append new phases as they complete
  - Can be re-run anytime for updated metrics
"""

import sys
import json
import csv
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime


class MetricsExtractor:
    """Unified metrics extraction from all sources."""
    
    def __init__(self):
        self.base_path = Path(".")
        self.results = {
            'config': {},
            'phases': {},
            'summary': {},
            'dataset': {},
        }
    
    # ============================================================================
    # SECTION 1: MODEL CONFIGURATION EXTRACTION
    # ============================================================================
    
    def extract_lightgbm_config(self):
        """Extract LightGBM hyperparameters from pipeline.py"""
        pipeline_file = self.base_path / "scripts" / "pipeline.py"
        
        if not pipeline_file.exists():
            print("⚠ pipeline.py not found")
            return None
        
        with open(pipeline_file) as f:
            content = f.read()
        
        config = {}
        
        # Extract LGBMClassifier parameters
        params = [
            ('n_estimators', r'n_estimators\s*=\s*(\d+)'),
            ('max_depth', r'max_depth\s*=\s*(-?\d+)'),
            ('learning_rate', r'learning_rate\s*=\s*([\d.]+)'),
            ('class_weight', r'class_weight\s*=\s*"?([^",\)]+)"?'),
            ('random_state', r'random_state\s*=\s*(\d+)'),
        ]
        
        for param_name, pattern in params:
            match = re.search(pattern, content)
            if match:
                value = match.group(1)
                try:
                    if '.' in value:
                        config[param_name] = float(value)
                    else:
                        config[param_name] = int(value)
                except ValueError:
                    config[param_name] = value
        
        # Extract candidate generation config
        patterns_match = re.search(r'PATTERNS\s*=\s*\[(.*?)\]', content)
        if patterns_match:
            patterns_str = patterns_match.group(1)
            patterns = []
            for item in patterns_str.split(','):
                item = item.strip()
                if 'x' in item.lower():
                    patterns.append(int(item, 16))
                else:
                    patterns.append(int(item))
            config['heuristic_patterns'] = len(patterns)
            config['pattern_list'] = patterns
        
        random_match = re.search(r'RANDOM_PER_PREFIX\s*=\s*(\d+)', content)
        if random_match:
            config['random_per_prefix'] = int(random_match.group(1))
        
        target_match = re.search(r'TARGET_TOTAL\s*=\s*([\d_]+)', content)
        if target_match:
            config['target_candidates'] = int(target_match.group(1).replace('_', ''))
        
        threshold_match = re.search(r'data\["density"\]\s*>\s*(\d+)', content)
        if threshold_match:
            config['active_threshold'] = int(threshold_match.group(1))
        
        self.results['config'] = config
        return config
    
    # ============================================================================
    # SECTION 2: DATASET CHARACTERISTICS EXTRACTION
    # ============================================================================
    
    def extract_dataset_info(self):
        """Extract dataset statistics from data_info_results.csv"""
        data_info_file = self.base_path / "processed" / "data_info_results.csv"
        
        if not data_info_file.exists():
            print("⚠ data_info_results.csv not found")
            return None
        
        dataset = {}
        
        try:
            with open(data_info_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    dataset[row['file_name']] = {
                        'size_human': row['file_size_human'],
                        'size_bytes': int(row['file_size_bytes']),
                        'line_count': int(row['line_count']),
                    }
            
            self.results['dataset'] = dataset
            return dataset
        except Exception as e:
            print(f"✗ Error reading dataset info: {e}")
            return None
    
    # ============================================================================
    # SECTION 3: EVALUATION METRICS EXTRACTION
    # ============================================================================
    
    def extract_phase_from_filename(self, filename):
        """Extract phase ID from filename."""
        match = re.search(r'(\d{2}_\d{2}_\d{2,4})', filename)
        return match.group(1) if match else None
    
    def load_dashboard_data(self):
        """Load dashboard JSON metrics."""
        dashboard_file = self.base_path / "dashboard" / "public" / "dashboard_data.json"
        
        if not dashboard_file.exists():
            print("⚠ dashboard_data.json not found")
            return None
        
        try:
            with open(dashboard_file) as f:
                return json.load(f)
        except Exception as e:
            print(f"✗ Error loading dashboard: {e}")
            return None
    
    def load_probe_results(self):
        """Load ground-truth probe results from processed_gcloud."""
        results = {}
        processed_gcloud = self.base_path / "processed_gcloud"
        
        if not processed_gcloud.exists():
            return results
        
        for csv_file in sorted(processed_gcloud.glob("processed_metrics*.csv")):
            phase = self.extract_phase_from_filename(csv_file.name)
            if not phase:
                continue
            
            try:
                responsive_counts = defaultdict(int)
                total_count = 0
                
                with open(csv_file) as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        total_count += 1
                        parts = line.split(',')
                        
                        if len(parts) >= 7:
                            protocols = ['icmp', 'tcp80', 'tcp443', 'tcp8080', 'tcp8443', 'udp53']
                            for idx, protocol in enumerate(protocols, start=1):
                                if idx < len(parts):
                                    val = parts[idx].strip().upper()
                                    if val == 'TRUE':
                                        responsive_counts[f'responsive_{protocol}'] += 1
                
                response_rate = 0.0
                if total_count > 0:
                    any_responsive = sum(1 for k, v in responsive_counts.items() 
                                       if 'responsive' in k and v > 0)
                    response_rate = (any_responsive / total_count) * 100
                
                results[phase] = {
                    'total_probed': total_count,
                    'responsive_icmp': responsive_counts.get('responsive_icmp', 0),
                    'responsive_tcp80': responsive_counts.get('responsive_tcp80', 0),
                    'responsive_tcp443': responsive_counts.get('responsive_tcp443', 0),
                    'responsive_tcp8080': responsive_counts.get('responsive_tcp8080', 0),
                    'responsive_tcp8443': responsive_counts.get('responsive_tcp8443', 0),
                    'responsive_udp53': responsive_counts.get('responsive_udp53', 0),
                    'response_rate': round(response_rate, 2),
                }
                
            except Exception as e:
                print(f"✗ Error processing {csv_file.name}: {e}")
        
        return results
    
    def extract_candidate_stats(self):
        """Extract candidate statistics from parquet files."""
        stats = {}
        results_path = self.base_path / "results"
        
        if not results_path.exists():
            return stats
        
        for parquet_file in sorted(results_path.glob("candidates*.parquet")):
            phase = self.extract_phase_from_filename(parquet_file.name)
            if not phase:
                continue
            
            try:
                size_bytes = parquet_file.stat().st_size
                estimated_rows = int(size_bytes / 400)  # ~400 bytes per row heuristic
                
                stats[phase] = {
                    'file_size_mb': round(size_bytes / (1024**2), 1),
                    'estimated_candidates': estimated_rows,
                }
            except Exception as e:
                print(f"✗ Error processing {parquet_file.name}: {e}")
        
        return stats
    
    def compute_phase_metrics(self, dashboard_data, probe_results):
        """Compute metrics for each phase."""
        phases = {}
        
        scan_history = dashboard_data.get('scan_history', [])
        
        for scan in scan_history:
            phase = scan.get('phase', 'unknown')
            date = scan.get('date', 'unknown')
            
            total_probed = scan.get('total_ips', 0)
            responsive = scan.get('responsive_ips', 0)
            successful = scan.get('successful_ips', 0)
            
            # Get probe data
            probe_data = probe_results.get(phase, {})
            
            # Calculate metrics
            precision = (responsive / total_probed * 100) if total_probed > 0 else 0
            recall = probe_data.get('response_rate', 0)
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            accuracy = (successful / total_probed * 100) if total_probed > 0 else 0
            
            # Port stats
            port_stats = scan.get('port_stats', {})
            
            # Multi-port analysis
            multi_port = scan.get('multi_port_analysis', [])
            single_port_pct = 0
            for entry in multi_port:
                if entry.get('ports') == 1:
                    single_port_pct = entry.get('percentage', 0)
                    break
            
            phases[phase] = {
                'date': date,
                'total_probed': total_probed,
                'responsive_ips': responsive,
                'successful_ips': successful,
                'response_rate_pct': probe_data.get('response_rate', 0),
                'precision_pct': round(precision, 2),
                'recall_pct': round(recall, 2),
                'f1_score': round(f1, 2),
                'accuracy_pct': round(accuracy, 2),
                'https_pct': port_stats.get('tcp443', {}).get('percentage', 0),
                'http_pct': port_stats.get('tcp80', {}).get('percentage', 0),
                'icmp_pct': port_stats.get('icmp', {}).get('percentage', 0),
                'dns_pct': port_stats.get('udp53', {}).get('percentage', 0),
                'single_service_pct': round(single_port_pct, 2),
                'format': scan.get('format', 'unknown'),
            }
        
        self.results['phases'] = phases
        return phases
    
    def compute_summary_stats(self, phases, dataset, config):
        """Compute overall summary statistics."""
        summary = {}
        
        if dataset:
            if 'clean_ipv6.txt' in dataset:
                summary['total_ips_scanned'] = dataset['clean_ipv6.txt']['line_count']
                summary['total_ips_size_gb'] = round(dataset['clean_ipv6.txt']['size_bytes'] / (1024**3), 1)
            
            if 'prefix_counts.txt' in dataset:
                summary['total_prefixes'] = dataset['prefix_counts.txt']['line_count']
                summary['prefix_size_gb'] = round(dataset['prefix_counts.txt']['size_bytes'] / (1024**3), 1)
        
        if phases:
            phase_list = sorted(phases.values(), key=lambda x: x['date'])
            
            summary['num_phases'] = len(phases)
            summary['date_range'] = f"{phase_list[0]['date']} to {phase_list[-1]['date']}"
            summary['total_probed_all_phases'] = sum(p['total_probed'] for p in phases.values())
            summary['total_responsive_all_phases'] = sum(p['responsive_ips'] for p in phases.values())
            
            if phase_list:
                latest = phase_list[-1]
                summary['latest_phase'] = [k for k, v in phases.items() if v == latest][0]
                summary['avg_https_pct'] = round(sum(p['https_pct'] for p in phases.values()) / len(phases), 2)
                summary['avg_single_service_pct'] = round(sum(p['single_service_pct'] for p in phases.values()) / len(phases), 2)
        
        if config:
            summary['ml_features'] = 2  # prefix, density
            summary['model_algorithm'] = 'LightGBM'
            summary['model_estimators'] = config.get('n_estimators', 'N/A')
            summary['active_threshold'] = config.get('active_threshold', 'N/A')
            summary['candidates_target'] = config.get('target_candidates', 'N/A')
        
        self.results['summary'] = summary
        return summary
    
    # ============================================================================
    # SECTION 4: REPORT GENERATION
    # ============================================================================
    
    def generate_text_report(self):
        """Generate human-readable thesis report."""
        lines = [
            "=" * 100,
            "COMPREHENSIVE THESIS METRICS EXTRACTION REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 100,
            "",
        ]
        
        # Section 1: Dataset Characteristics
        lines.extend([
            "1. DATASET CHARACTERISTICS",
            "-" * 100,
        ])
        
        dataset = self.results.get('dataset', {})
        if dataset:
            if 'clean_ipv6.txt' in dataset:
                lines.append(f"  Total IPv6 addresses scanned: {dataset['clean_ipv6.txt']['line_count']:,}")
                lines.append(f"  Dataset size: {dataset['clean_ipv6.txt']['size_human']}")
            
            if 'prefix_counts.txt' in dataset:
                lines.append(f"  Total /64 prefixes: {dataset['prefix_counts.txt']['line_count']:,}")
                lines.append(f"  Prefix data size: {dataset['prefix_counts.txt']['size_human']}")
        
        lines.extend(["", "2. MODEL CONFIGURATION", "-" * 100])
        
        config = self.results.get('config', {})
        if config:
            lines.append("  LightGBM Classifier:")
            for key in ['n_estimators', 'max_depth', 'learning_rate', 'class_weight', 'random_state']:
                if key in config:
                    lines.append(f"    {key}: {config[key]}")
            
            lines.append("\n  Feature Engineering:")
            lines.append("    Input features: prefix, density")
            lines.append("    Derived features: log_density = log(1 + density)")
            lines.append(f"    Active prefix threshold: density > {config.get('active_threshold', 'N/A')}")
            
            lines.append("\n  Candidate Generation:")
            lines.append(f"    Heuristic patterns: {config.get('heuristic_patterns', 'N/A')}")
            lines.append(f"    Random per prefix: {config.get('random_per_prefix', 'N/A')}")
            lines.append(f"    Total per prefix: {config.get('heuristic_patterns', 0) + config.get('random_per_prefix', 0)}")
            lines.append(f"    Target candidates: {config.get('target_candidates', 'N/A'):,}")
        
        lines.extend(["", "3. EVALUATION METRICS - ALL PHASES", "-" * 100, ""])
        
        phases = self.results.get('phases', {})
        if phases:
            # Header
            lines.append(
                f"{'Phase':<12} {'Date':<12} {'Probed':<12} {'Responsive':<12} "
                f"{'Precision':<12} {'Recall':<10} {'F1':<8} {'HTTPS%':<10}"
            )
            lines.append("-" * 100)
            
            # Rows
            for phase in sorted(phases.keys(), key=lambda p: phases[p]['date']):
                m = phases[phase]
                lines.append(
                    f"{phase:<12} {m['date']:<12} {m['total_probed']:>11,} "
                    f"{m['responsive_ips']:>11,} {m['precision_pct']:>10.1f}% "
                    f"{m['recall_pct']:>8.1f}% {m['f1_score']:>6.2f} {m['https_pct']:>8.1f}%"
                )
        
        lines.extend(["", "4. SUMMARY STATISTICS", "-" * 100, ""])
        
        summary = self.results.get('summary', {})
        if summary:
            lines.append(f"  Number of phases: {summary.get('num_phases', 'N/A')}")
            lines.append(f"  Date range: {summary.get('date_range', 'N/A')}")
            lines.append(f"  Total IPs probed (all phases): {summary.get('total_probed_all_phases', 0):,}")
            lines.append(f"  Total responsive (all phases): {summary.get('total_responsive_all_phases', 0):,}")
            lines.append(f"  Average HTTPS prevalence: {summary.get('avg_https_pct', 0):.2f}%")
            lines.append(f"  Average single-service hosts: {summary.get('avg_single_service_pct', 0):.2f}%")
            
            if 'total_ips_scanned' in summary:
                lines.append(f"  Dataset: {summary['total_ips_scanned']:,} IPs ({summary.get('total_ips_size_gb', 0):.1f} GB)")
            
            if 'total_prefixes' in summary:
                lines.append(f"  Prefixes: {summary['total_prefixes']:,} ({summary.get('prefix_size_gb', 0):.1f} GB)")
        
        lines.extend(["", "5. PROTOCOL ANALYSIS - LATEST PHASE", "-" * 100, ""])
        
        if phases:
            latest_phase = max(phases.items(), key=lambda x: x[1]['date'])
            phase_name, phase_data = latest_phase
            lines.append(f"  Phase: {phase_name} ({phase_data['date']})")
            lines.append(f"  Probed: {phase_data['total_probed']:,} IPs")
            lines.append("")
            lines.append("  Protocol Breakdown:")
            lines.append(f"    HTTPS (TCP/443): {phase_data['https_pct']:.2f}%")
            lines.append(f"    HTTP (TCP/80):   {phase_data['http_pct']:.2f}%")
            lines.append(f"    ICMP:            {phase_data['icmp_pct']:.2f}%")
            lines.append(f"    DNS (UDP/53):    {phase_data['dns_pct']:.2f}%")
            lines.append("")
            lines.append("  Multi-Port Distribution:")
            lines.append(f"    Single-service hosts: {phase_data['single_service_pct']:.2f}%")
            lines.append(f"    Multi-service hosts:  {100 - phase_data['single_service_pct']:.2f}%")
        
        lines.extend(["", "=" * 100])
        
        return "\n".join(lines)
    
    def save_csv_report(self, filename='metrics_data.csv'):
        """Save phase metrics to CSV for appendix."""
        phases = self.results.get('phases', {})
        
        if not phases:
            print("⚠ No phases to export to CSV")
            return False
        
        try:
            with open(filename, 'w', newline='') as f:
                fieldnames = list(phases[list(phases.keys())[0]].keys())
                fieldnames.insert(0, 'phase')
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for phase_name in sorted(phases.keys(), key=lambda p: phases[p]['date']):
                    row = {'phase': phase_name}
                    row.update(phases[phase_name])
                    writer.writerow(row)
            
            print(f"✓ CSV exported to {filename}")
            return True
        except Exception as e:
            print(f"✗ Error saving CSV: {e}")
            return False
    
    # ============================================================================
    # MAIN EXTRACTION WORKFLOW
    # ============================================================================
    
    def extract_all(self):
        """Run complete extraction workflow."""
        print("\n" + "=" * 100)
        print("EXTRACTING ALL THESIS METRICS")
        print("=" * 100 + "\n")
        
        print("[1/6] Extracting model configuration...")
        self.extract_lightgbm_config()
        
        print("[2/6] Loading dataset characteristics...")
        self.extract_dataset_info()
        
        print("[3/6] Loading dashboard aggregated metrics...")
        dashboard = self.load_dashboard_data()
        
        print("[4/6] Loading ground-truth probe results...")
        probe_results = self.load_probe_results()
        
        print("[5/6] Computing evaluation metrics...")
        self.compute_phase_metrics(dashboard, probe_results)
        
        print("[6/6] Computing summary statistics...")
        self.compute_summary_stats(
            self.results['phases'],
            self.results['dataset'],
            self.results['config']
        )
        
        print("\n✓ Extraction complete\n")
    
    def save_reports(self, text_file='metrics_report.txt', csv_file='metrics_data.csv'):
        """Save all reports."""
        # Text report
        report = self.generate_text_report()
        with open(text_file, 'w') as f:
            f.write(report)
        print(f"✓ Text report saved to {text_file}")
        print(report)
        
        # CSV report
        self.save_csv_report(csv_file)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract all thesis metrics')
    parser.add_argument('--text', default='metrics_report.txt', help='Text output file')
    parser.add_argument('--csv', default='metrics_data.csv', help='CSV output file')
    
    args = parser.parse_args()
    
    extractor = MetricsExtractor()
    extractor.extract_all()
    extractor.save_reports(args.text, args.csv)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
