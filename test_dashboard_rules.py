#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test if user-defined rules from dashboard are being applied"""
import json
from pathlib import Path
import logging
import sys

# Fix encoding on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("\n" + "="*80)
print("TEST: User-Defined Rules Application")
print("="*80 + "\n")

# Check if cleansing_rules.json exists
rules_file = Path('output/cleansing_rules.json')
if rules_file.exists():
    with open(rules_file, 'r') as f:
        rules = json.load(f)
    
    # Filter out empty rules
    active_rules = {k: v for k, v in rules.items() if v and v.strip()}
    
    print(f"Found cleansing_rules.json with {len(active_rules)} active rules:")
    for col, rule in active_rules.items():
        print(f"  • {col}: '{rule}'")
    print()
    
    # Now run the cleansing with these rules
    print("Running cleansing pipeline with these rules...\n")
    
    import subprocess
    result = subprocess.run(
        ['python', 'assessment_first_pipeline.py', '--clean', '--dedup-method', 'keep-first'],
        capture_output=True,
        text=True,
        cwd='e:\\LR 1\\DQ_PE_V2'
    )
    
    # Check logs for rule application
    output = result.stdout + result.stderr
    
    if 'DASHBOARD-DEFINED' in output or 'cleansing_rules.json' in output:
        print("[OK] Dashboard rules file was detected and loaded")
    else:
        print("[FAIL] Dashboard rules file was NOT loaded")
    
    # Look for rule application messages
    print("\nRule Application Status:")
    for col, rule in active_rules.items():
        if col in output:
            print(f"  [OK] {col}: Rule detected in processing")
        else:
            print(f"  [FAIL] {col}: No evidence of processing")
    
    # Check if transformations were applied
    if 'Total transformations applied' in output:
        import re
        match = re.search(r'Total transformations applied: (\d+)', output)
        if match:
            count = match.group(1)
            print(f"\n[OK] Total transformations applied: {count}")
    
    print("\n" + "="*80 + "\n")
else:
    print(f"[FAIL] Rules file not found: {rules_file}")
