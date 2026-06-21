#!/usr/bin/env python
"""Test LLM and rule application"""
import json
from llm.llm_client import LLMClient
from agents.standardization_rules import CustomCleansingRuleParser
import pandas as pd

print("="*80)
print("TESTING LLM AND RULE APPLICATION")
print("="*80)

# Test 1: LLM connection
print("\n1. Testing LLM Connection...")
try:
    config = {
        'enabled': True,
        'provider': 'ollama',
        'model': 'llama2',
        'base_url': 'http://localhost:11434',
        'timeout': 30
    }
    client = LLMClient(config)
    if client.available:
        response = client.complete('Convert date 5/7/2022 to YYYY/MM/DD')
        print("[OK] LLM is working!")
        print(f"   Response: {response[:100] if response else 'No response'}")
    else:
        print("[ERROR] LLM is not available")
except Exception as e:
    print(f"[ERROR] LLM error: {e}")

# Test 2: Load rules
print("\n2. Loading cleansing rules...")
try:
    with open('output/cleansing_rules.json', 'r') as f:
        rules = json.load(f)
    non_empty = {k: v for k, v in rules.items() if v and v.strip()}
    print(f"[OK] Loaded {len(non_empty)} rules:")
    for col, rule in non_empty.items():
        print(f"   - {col}: {rule}")
except Exception as e:
    print(f"[ERROR] Error loading rules: {e}")

# Test 3: Parse and apply rule
print("\n3. Testing rule parsing and application...")
try:
    rule_text = "convert all into YYYY/MM/DD format"
    parsed = CustomCleansingRuleParser.parse_custom_rule(rule_text)
    print(f"[OK] Parsed rule: {parsed}")
    
    # Test application
    test_value = "5/7/2022"
    result = CustomCleansingRuleParser.apply_custom_rule(test_value, parsed)
    print(f"   Input: {test_value}")
    print(f"   Output: {result}")
except Exception as e:
    print(f"[ERROR] Error: {e}")

# Test 4: Load and transform data
print("\n4. Testing data transformation...")
try:
    df = pd.read_csv('data/Sample_Policy_Data.csv')
    print(f"[OK] Loaded data: {df.shape}")
    print(f"   Policy Effective Date samples:")
    print(df['Policy Effective Date'].head(3).to_list())
    
    # Apply rule
    rule_text = "convert all into YYYY/MM/DD format"
    parsed = CustomCleansingRuleParser.parse_custom_rule(rule_text)
    
    df['Policy Effective Date'] = df['Policy Effective Date'].apply(
        lambda x: CustomCleansingRuleParser.apply_custom_rule(x, parsed)
    )
    
    print(f"\n   After transformation:")
    print(df['Policy Effective Date'].head(3).to_list())
    
except Exception as e:
    print(f"[ERROR] Error: {e}")

print("\n" + "="*80)
print("TESTING COMPLETE")
print("="*80)
