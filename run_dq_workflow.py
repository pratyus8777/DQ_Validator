#!/usr/bin/env python
"""
Complete Data Quality Pipeline - Single File Workflow
Runs full assessment → cleansing → results in one execution
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import subprocess
import sys

class DQWorkflowRunner:
    """Complete DQ workflow in a single runner"""
    
    def __init__(self):
        self.data_path = 'data/Sample_Policy_Data.csv'
        self.output_dir = Path('output')
        self.output_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.assessment_report = None
        self.original_df = None
        self.cleaned_df = None
        
    def print_header(self, text):
        """Print formatted header"""
        print("\n" + "="*80)
        print(f"  {text}")
        print("="*80)
    
    def print_section(self, text):
        """Print formatted section"""
        print(f"\n{text}")
        print("-" * 80)
    
    def step1_run_assessment(self):
        """Step 1: Run assessment"""
        self.print_header("STEP 1: RUNNING ASSESSMENT")
        
        print("\nExecuting assessment phase...")
        cmd = ["python", "assessment_first_pipeline.py"]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"Error running assessment: {result.stderr}")
            return False
        
        # Load the generated assessment report
        reports = sorted(Path('output').glob('Assessment_Report_*.json'), reverse=True)
        if reports:
            with open(reports[0], 'r') as f:
                self.assessment_report = json.load(f)
            print(f"✓ Assessment complete: {reports[0].name}")
            return True
        
        print("✗ Assessment report not found")
        return False
    
    def step2_display_assessment(self):
        """Step 2: Display assessment results"""
        self.print_header("STEP 2: ASSESSMENT RESULTS")
        
        if not self.assessment_report:
            print("No assessment report available")
            return
        
        summary = self.assessment_report.get('summary', {})
        
        # Data Summary
        self.print_section("DATA SUMMARY")
        print(f"Total Records:        {summary.get('total_records', 'N/A')}")
        print(f"Total Columns:        {summary.get('total_columns', 'N/A')}")
        print(f"Problem Columns:      {summary.get('columns_with_issues', 0)}")
        print(f"Total Violations:     {summary.get('total_violations', 0)}")
        
        # Violations by Dimension
        self.print_section("VIOLATIONS BY DIMENSION")
        violations_by_dim = self.assessment_report.get('violations_by_dimension', {})
        for dimension, violations in violations_by_dim.items():
            if violations:
                print(f"\n{dimension}: {len(violations)} issue types")
                for v in violations[:3]:
                    print(f"  • {v.get('column', 'N/A')}: {v.get('type', 'Unknown')} ({v.get('count', 0)} records)")
                if len(violations) > 3:
                    print(f"  ... and {len(violations) - 3} more")
        
        # Violations by Column (Top 10)
        self.print_section("TOP 10 PROBLEM COLUMNS")
        violations_by_col = self.assessment_report.get('violations_by_column', {})
        for i, (col, count) in enumerate(sorted(violations_by_col.items(), key=lambda x: x[1], reverse=True)[:10], 1):
            print(f"{i:2}. {col:40} {count:6} violations")
        
        # Data Sheet
        self.print_section("DATA SHEET - SAMPLE COLUMNS")
        columns = self.assessment_report.get('column_profiles', {})
        sample_cols = list(columns.keys())[:5]
        for col in sample_cols:
            profile = columns[col]
            print(f"\n{col}")
            print(f"  Type: {profile.get('data_type', 'N/A')}")
            print(f"  Non-null: {profile.get('non_null_count', 0)} ({100 - profile.get('null_percentage', 0):.1f}%)")
            print(f"  Unique: {profile.get('unique_values', 0)}")
            samples = profile.get('sample_values', [])
            if samples:
                print(f"  Samples: {', '.join(str(s) for s in samples[:2])}")
        print(f"\n... and {len(columns) - 5} more columns")
        
        # Rules Sheet
        self.print_section("RULES SHEET - CLEANSING RULES")
        rules = self.assessment_report.get('rules_for_cleaning', {})
        print(f"\nPre-populated rules ({len(rules)} total):")
        for i, (col, rule) in enumerate(rules.items(), 1):
            if isinstance(rule, dict):
                rule_text = rule.get('user_rule', str(rule))
            else:
                rule_text = str(rule)
            print(f"{i}. {col}")
            print(f"   {rule_text}")
    
    def step3_review_and_confirm(self):
        """Step 3: User review and confirmation"""
        self.print_header("STEP 3: REVIEW & CONFIRM")
        
        print("\nAssessment complete. Review the results above.")
        print("\nYou can:")
        print("  1. Continue with cleaning (using current rules)")
        print("  2. Edit rules in Tab 3 of dashboard before cleaning")
        print("  3. Exit and review later")
        
        while True:
            choice = input("\nProceed with cleaning? (yes/no/edit): ").strip().lower()
            if choice in ['yes', 'y']:
                return True
            elif choice in ['no', 'n']:
                print("Exiting without cleaning. Run dashboard to edit rules:")
                print("  streamlit run dashboard_final.py")
                return False
            elif choice == 'edit':
                print("Launching dashboard to edit rules...")
                print("  streamlit run dashboard_final.py")
                print("After editing rules, run this script again to complete cleaning.")
                return False
            else:
                print("Please enter 'yes', 'no', or 'edit'")
    
    def step4_select_dedup_method(self):
        """Step 4: Select deduplication method"""
        self.print_header("STEP 4: DEDUPLICATION METHOD")
        
        print("\nChoose deduplication method:")
        print("  1. Keep first occurrence (default)")
        print("  2. Keep last occurrence")
        print("  3. Remove all duplicates")
        
        while True:
            choice = input("\nSelect (1-3): ").strip()
            if choice == '1':
                return 'keep-first'
            elif choice == '2':
                return 'keep-last'
            elif choice == '3':
                return 'remove-all'
            else:
                print("Please enter 1, 2, or 3")
    
    def step5_run_cleansing(self, dedup_method):
        """Step 5: Run cleansing with selected method"""
        self.print_header("STEP 5: EXECUTING CLEANSING")
        
        print(f"\nDeduplication method: {dedup_method}")
        print("Running cleansing pipeline...")
        
        cmd = [
            "python", "assessment_first_pipeline.py",
            "--clean",
            "--dedup-method", dedup_method
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"Error running cleansing: {result.stderr}")
            return False
        
        print("✓ Cleansing complete!")
        return True
    
    def step6_display_results(self):
        """Step 6: Display results and comparison"""
        self.print_header("STEP 6: RESULTS & COMPARISON")
        
        # Load original data
        try:
            self.original_df = pd.read_csv(self.data_path)
        except Exception as e:
            print(f"Error loading original data: {e}")
            return
        
        # Load cleaned data
        cleaned_files = sorted(Path('output').glob('Sample_Policy_Data_CLEANED_*.csv'), reverse=True)
        if not cleaned_files:
            print("No cleaned data found")
            return
        
        try:
            self.cleaned_df = pd.read_csv(cleaned_files[0])
        except Exception as e:
            print(f"Error loading cleaned data: {e}")
            return
        
        # Display metrics
        self.print_section("METRICS")
        original_count = len(self.original_df)
        cleaned_count = len(self.cleaned_df)
        removed = original_count - cleaned_count
        
        print(f"Original records:           {original_count}")
        print(f"Cleaned records:            {cleaned_count}")
        print(f"Records removed:            {removed}")
        print(f"Deduplication rate:         {removed/original_count*100:.1f}%")
        
        # Display cleaned data preview
        self.print_section("CLEANED DATA PREVIEW (First 10 rows)")
        print(self.cleaned_df.head(10).to_string())
        
        # Display column comparison (samples)
        self.print_section("BEFORE & AFTER COMPARISON")
        sample_cols = ['Policy Effective Date', 'Phone', 'Email', 'Customer Name']
        available_cols = [c for c in sample_cols if c in self.original_df.columns]
        
        for col in available_cols[:3]:
            print(f"\n{col}:")
            print("  Original samples → Cleaned samples")
            orig_samples = self.original_df[col].dropna().head(2).tolist()
            clean_samples = self.cleaned_df[col].dropna().head(2).tolist()
            for orig, clean in zip(orig_samples, clean_samples):
                print(f"    {orig} → {clean}")
        
        # Output file info
        self.print_section("OUTPUT FILES")
        print(f"\nCleaned data saved: {cleaned_files[0].name}")
        print(f"Full path: {cleaned_files[0].absolute()}")
        
        # Download instructions
        print(f"\nTo use cleaned data:")
        print(f"  1. Download from: {cleaned_files[0]}")
        print(f"  2. Use in your analysis or import to system")
        print(f"  3. Original data is preserved at: {self.data_path}")
    
    def run_complete_workflow(self):
        """Run complete workflow"""
        self.print_header("DATA QUALITY COMPLETE WORKFLOW")
        print("\nThis script will:")
        print("  1. Run data assessment")
        print("  2. Display violations and rules")
        print("  3. Ask for confirmation to clean")
        print("  4. Select deduplication method")
        print("  5. Execute cleansing")
        print("  6. Display results and comparison")
        
        # Step 1: Assessment
        if not self.step1_run_assessment():
            print("\nAssessment failed. Exiting.")
            return False
        
        # Step 2: Display Assessment
        self.step2_display_assessment()
        
        # Step 3: Review and Confirm
        if not self.step3_review_and_confirm():
            print("\nWorkflow paused. You can:")
            print("  - Edit rules: streamlit run dashboard_final.py")
            print("  - Continue cleaning: python run_dq_workflow.py")
            return False
        
        # Step 4: Select Dedup Method
        dedup_method = self.step4_select_dedup_method()
        
        # Step 5: Run Cleansing
        if not self.step5_run_cleansing(dedup_method):
            print("\nCleansing failed. Exiting.")
            return False
        
        # Step 6: Display Results
        self.step6_display_results()
        
        # Complete
        self.print_header("WORKFLOW COMPLETE")
        print("\n✓ Assessment completed")
        print("✓ Violations detected and reported")
        print("✓ Rules applied to data")
        print("✓ Data cleaned and deduplicated")
        print("✓ Results displayed and saved")
        
        print("\nNext steps:")
        print("  1. Review the cleaned data above")
        print("  2. Download the cleaned CSV file")
        print("  3. Use in your analysis or system")
        
        return True


def main():
    """Main entry point"""
    try:
        runner = DQWorkflowRunner()
        success = runner.run_complete_workflow()
        
        if success:
            print("\n" + "="*80)
            print("  WORKFLOW SUCCESSFUL - DATA READY FOR USE")
            print("="*80 + "\n")
            sys.exit(0)
        else:
            print("\n" + "="*80)
            print("  WORKFLOW PAUSED - AWAITING USER ACTION")
            print("="*80 + "\n")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
