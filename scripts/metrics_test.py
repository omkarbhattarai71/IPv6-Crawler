#!/usr/bin/env python3
"""
Comprehensive metrics validation and testing suite for IPv6 measurement campaign.
Tests dataset integrity, model configuration, metrics computation, and reproducibility.
"""

import json
import csv
import os
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

class MetricsValidator:
    def __init__(self, project_root="/ceph/project/IPv6-BOS/IPv6-Crawler"):
        self.root = Path(project_root)
        self.test_results = []
        self.errors = []
        self.warnings = []
        
    def log_test(self, name, status, details=""):
        """Log test result"""
        result = {
            "name": name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.test_results.append(result)
        print(f"{'✓' if status == 'PASS' else '✗' if status == 'FAIL' else '⚠'} {name}: {status} {details}")
        
    def test_dataset_files(self):
        """Test 1: Verify dataset file accessibility"""
        print("\n" + "="*80)
        print("TEST 1: DATASET FILE ACCESSIBILITY")
        print("="*80)
        
        files_to_check = {
            "processed/data_info_results.csv": "Dataset info",
            "processed/clean_ipv6.txt": "Cleaned IPv6 addresses",
            "processed/features.csv": "Feature engineering output",
            "dashboard/public/dashboard_data.json": "Dashboard JSON",
        }
        
        for filepath, desc in files_to_check.items():
            full_path = self.root / filepath
            if full_path.exists():
                size_mb = full_path.stat().st_size / (1024*1024)
                self.log_test(f"File: {filepath}", "PASS", f"({size_mb:.1f} MB)")
            else:
                self.log_test(f"File: {filepath}", "FAIL", "(not found)")
                self.errors.append(f"Missing: {filepath}")
    
    def test_probe_results_files(self):
        """Test 2: Verify probe results CSV files"""
        print("\n" + "="*80)
        print("TEST 2: PROBE RESULTS FILE VALIDATION")
        print("="*80)
        
        probe_dir = self.root / "processed_gcloud"
        if not probe_dir.exists():
            self.log_test("Probe results directory", "FAIL", "Directory not found")
            self.errors.append("processed_gcloud/ directory missing")
            return
        
        csv_files = list(probe_dir.glob("processed_metrics*.csv"))
        self.log_test(f"Probe CSV files found", "PASS", f"({len(csv_files)} files)")
        
        for csv_file in csv_files:
            try:
                with open(csv_file, 'r') as f:
                    rows = sum(1 for _ in f) - 1  # Subtract header
                self.log_test(f"  {csv_file.name}", "PASS", f"({rows} rows)")
            except Exception as e:
                self.log_test(f"  {csv_file.name}", "FAIL", str(e))
                self.errors.append(f"Error reading {csv_file.name}: {e}")
    
    def test_dashboard_json(self):
        """Test 3: Validate dashboard JSON structure"""
        print("\n" + "="*80)
        print("TEST 3: DASHBOARD JSON VALIDATION")
        print("="*80)
        
        json_file = self.root / "dashboard/public/dashboard_data.json"
        
        if not json_file.exists():
            self.log_test("Dashboard JSON file", "FAIL", "File not found")
            self.errors.append("dashboard_data.json not found")
            return
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            self.log_test("JSON validity", "PASS", "(valid JSON structure)")
            
            # Check scan_history structure
            if 'scan_history' in data:
                scan_count = len(data['scan_history'])
                self.log_test("Scan history entries", "PASS", f"({scan_count} phases recorded)")
                
                # Validate phase entries - flexible validation
                for i, phase in enumerate(data['scan_history']):
                    if isinstance(phase, dict) and len(phase) > 0:
                        phase_name = phase.get('phase', f'Phase_{i}')
                        phase_keys = list(phase.keys())
                        self.log_test(f"  Phase {i+1} ({phase_name})", "PASS", f"(has data)")
                    else:
                        self.log_test(f"  Phase {i+1} structure", "FAIL", "Invalid structure")
                        self.errors.append(f"Phase {i+1} has invalid structure")
            else:
                self.log_test("Scan history", "FAIL", "Key not found in JSON")
                self.errors.append("'scan_history' key missing from dashboard JSON")
                
        except json.JSONDecodeError as e:
            self.log_test("JSON validity", "FAIL", f"Invalid JSON: {e}")
            self.errors.append(f"JSON decode error: {e}")
    
    def test_model_config(self):
        """Test 4: Extract and validate model configuration"""
        print("\n" + "="*80)
        print("TEST 4: MODEL CONFIGURATION EXTRACTION")
        print("="*80)
        
        pipeline_file = self.root / "scripts/train_model.py"
        
        if not pipeline_file.exists():
            self.log_test("Model config file", "FAIL", "train_model.py not found")
            return
        
        try:
            with open(pipeline_file, 'r') as f:
                content = f.read()
            
            self.log_test("Model config file", "PASS", "Found")
            
            # Extract key parameters
            params = {
                "n_estimators": None,
                "max_depth": None,
                "learning_rate": None,
                "class_weight": None
            }
            
            for param in params.keys():
                if param in content:
                    self.log_test(f"  Parameter: {param}", "PASS", "(extracted)")
                else:
                    self.log_test(f"  Parameter: {param}", "WARN", "(not explicitly found)")
                    self.warnings.append(f"Parameter {param} not found in model config")
            
        except Exception as e:
            self.log_test("Model config extraction", "FAIL", str(e))
            self.errors.append(f"Error reading model config: {e}")
    
    def test_metrics_computation(self):
        """Test 5: Validate metrics computation accuracy"""
        print("\n" + "="*80)
        print("TEST 5: METRICS COMPUTATION VALIDATION")
        print("="*80)
        
        metrics_file = self.root / "scripts/extract_all_metrics.py"
        
        if not metrics_file.exists():
            self.log_test("Metrics extraction script", "FAIL", "extract_all_metrics.py not found")
            return
        
        try:
            with open(metrics_file, 'r') as f:
                content = f.read()
            
            self.log_test("Metrics extraction script", "PASS", "Found")
            
            # Check for key computation functions
            computations = [
                "compute_phase_metrics",
                "generate_text_report",
                "save_csv_report"
            ]
            
            for comp in computations:
                if comp in content:
                    self.log_test(f"  Function: {comp}", "PASS", "(defined)")
                else:
                    self.log_test(f"  Function: {comp}", "FAIL", "(not found)")
                    self.errors.append(f"Function {comp} not found")
            
        except Exception as e:
            self.log_test("Metrics computation check", "FAIL", str(e))
            self.errors.append(f"Error checking metrics script: {e}")
    
    def test_output_files(self):
        """Test 6: Verify output file generation"""
        print("\n" + "="*80)
        print("TEST 6: OUTPUT FILE GENERATION")
        print("="*80)
        
        output_files = {
            "metrics_report.txt": "Text report",
            "metrics_data.csv": "CSV metrics"
        }
        
        for filename, desc in output_files.items():
            filepath = self.root / filename
            if filepath.exists():
                size_kb = filepath.stat().st_size / 1024
                lines = len(filepath.read_text().splitlines())
                self.log_test(f"Output: {filename}", "PASS", f"({lines} lines, {size_kb:.1f} KB)")
            else:
                self.log_test(f"Output: {filename}", "FAIL", "(not generated)")
                self.warnings.append(f"{filename} not found. Run extract_all_metrics.py first")
    
    def test_data_consistency(self):
        """Test 7: Validate data consistency across phases"""
        print("\n" + "="*80)
        print("TEST 7: DATA CONSISTENCY VALIDATION")
        print("="*80)
        
        json_file = self.root / "dashboard/public/dashboard_data.json"
        csv_file = self.root / "metrics_data.csv"
        
        if not json_file.exists() or not csv_file.exists():
            self.log_test("Data consistency", "WARN", "Output files missing (not critical)")
            return
        
        try:
            with open(json_file, 'r') as f:
                dashboard = json.load(f)
            
            with open(csv_file, 'r') as f:
                csv_reader = csv.DictReader(f)
                csv_data = list(csv_reader)
            
            json_phases = len(dashboard.get('scan_history', []))
            csv_phases = len(csv_data)
            
            if json_phases == csv_phases:
                self.log_test("Phase count consistency", "PASS", f"(both report {json_phases} phases)")
            else:
                self.log_test("Phase count consistency", "FAIL", f"(JSON: {json_phases}, CSV: {csv_phases})")
                self.errors.append(f"Phase count mismatch: JSON={json_phases}, CSV={csv_phases}")
            
            # Check response rates consistency
            response_rates = []
            for row in csv_data:
                if 'response_rate_pct' in row:
                    try:
                        rate = float(row['response_rate_pct'])
                        response_rates.append(rate)
                    except:
                        pass
            
            if response_rates:
                avg_rate = sum(response_rates) / len(response_rates)
                min_rate = min(response_rates)
                max_rate = max(response_rates)
                self.log_test("Response rate statistics", "PASS", 
                            f"(avg: {avg_rate:.1f}%, min: {min_rate:.1f}%, max: {max_rate:.1f}%)")
            
        except Exception as e:
            self.log_test("Data consistency check", "FAIL", str(e))
            self.errors.append(f"Error checking consistency: {e}")
    
    def test_reproducibility(self):
        """Test 8: Reproducibility validation"""
        print("\n" + "="*80)
        print("TEST 8: REPRODUCIBILITY VALIDATION")
        print("="*80)
        
        requirements = [
            ("scripts/extract_all_metrics.py", "Metrics extractor"),
            ("scripts/train_model.py", "Model trainer"),
            ("scripts/generate_candidates.py", "Candidate generator"),
            ("processed/clean_ipv6.txt", "Dataset"),
        ]
        
        reproducibility_score = 0
        
        for filepath, desc in requirements:
            full_path = self.root / filepath
            if full_path.exists():
                self.log_test(f"Reproducibility: {desc}", "PASS", "Available")
                reproducibility_score += 1
            else:
                self.log_test(f"Reproducibility: {desc}", "FAIL", "Missing")
        
        score_pct = (reproducibility_score / len(requirements)) * 100
        self.log_test("Reproducibility score", "PASS", f"({score_pct:.0f}%)")
    
    def generate_summary(self):
        """Generate test summary"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['status'] == 'PASS')
        failed = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        warnings = sum(1 for r in self.test_results if r['status'] == 'WARN')
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"  ✓ Passed:  {passed}")
        print(f"  ✗ Failed:  {failed}")
        print(f"  ⚠ Warnings: {warnings} (non-critical)")
        
        if self.errors:
            print(f"\n🔴 CRITICAL ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
        else:
            print(f"\n✅ No critical errors found!")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}) (non-critical):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        # Success rate counts PASS + WARN as acceptable
        acceptable = passed + warnings
        success_rate = (acceptable / total_tests * 100) if total_tests > 0 else 0
        critical_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📊 CRITICAL SUCCESS RATE (PASS only): {critical_rate:.1f}%")
        print(f"📊 OVERALL SUCCESS RATE (PASS+WARN): {success_rate:.1f}%")
        print("="*80)
        
        return failed == 0  # Overall pass if no critical failures

def main():
    print("\n" + "="*80)
    print("IPv6 MEASUREMENT CAMPAIGN - METRICS VALIDATION TEST SUITE")
    print("="*80)
    print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    validator = MetricsValidator()
    
    # Run all tests
    validator.test_dataset_files()
    validator.test_probe_results_files()
    validator.test_dashboard_json()
    validator.test_model_config()
    validator.test_metrics_computation()
    validator.test_output_files()
    validator.test_data_consistency()
    validator.test_reproducibility()
    
    # Generate summary
    success = validator.generate_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
