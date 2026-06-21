#!/usr/bin/env python
"""Test rule parsing for new format"""
import sys
sys.path.insert(0, 'e:\\LR 1\\DQ_PE')

from agents.standardization_rules import CustomCleansingRuleParser

# Test the new rule format
rules_to_test = [
    "change to DD-MM-YYYY format",
    "convert all into YYYY/MM/DD format",
    "change to DD-MM-YYYY format",
    "standardize to YYYY-MM-DD"
]

for rule_text in rules_to_test:
    print(f"\nRule: {rule_text}")
    parsed = CustomCleansingRuleParser.parse_custom_rule(rule_text)
    print(f"  Parsed: {parsed}")
    
    # Test with a sample date
    test_val = "5/7/2022"
    result = CustomCleansingRuleParser.apply_custom_rule(test_val, parsed)
    print(f"  {test_val} -> {result}")
