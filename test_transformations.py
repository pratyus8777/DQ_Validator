#!/usr/bin/env python
"""Quick debug to see if transformations are being created"""

import sys
sys.path.insert(0, '.')

from assessment_first_pipeline import DQAssessmentFirst

pipeline = DQAssessmentFirst()

# Test the heuristic transformation for different columns
test_cases = [
    ('Phone', 'If Phone is null, standardize format'),
    ('Email', 'If Email is invalid format, lowercase and standardize'),
    ('Customer Name', 'If Name is malformed, apply title case'),
    ('Customer ID', 'If ID is malformed, uppercase and validate'),
    ('Policy Effective Date', 'If date is invalid format, standardize to YYYY-MM-DD'),
]

print("Testing heuristic transformations:\n")
for col, rule in test_cases:
    trans = pipeline._get_heuristic_transformation(col, rule)
    if trans is None:
        print("[FAIL] {}: NO TRANSFORMATION ({})".format(col, rule))
    else:
        # Test the transformation
        test_val = "abc 123 def"
        try:
            result = trans(test_val)
            print("[OK] {}: '{}' -> '{}'".format(col, test_val, result))
        except Exception as e:
            print("[ERROR] {}: {}".format(col, e))

print("\n" + "="*70)
print("The issue: _get_heuristic_transformation returns lambda functions")
