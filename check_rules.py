import pandas as pd
from agents.cleansing_rule_parser import CleansingRuleParser
from data_io.db_helpers import read_guidewire_cleansing_rules

# Read the raw rules from Neon DB
rules_df = read_guidewire_cleansing_rules()

# Parse them
parser = CleansingRuleParser()
parsed = parser.parse_cleansing_rules(rules_df)

# Filter for dedup rules
dedup_rules = parsed[parsed['remediation_type'] == 'deduplication']
print(f'Deduplication rules found: {len(dedup_rules)}')
for _, rule in dedup_rules.iterrows():
    print(f'  - Column: {rule["cde"]}, Fix: {rule["fix_action"]}')

# Show first few parsed rules
print(f'\nTotal rules parsed: {len(parsed)}')
print('\nFirst 10 rules:')
print(parsed[['cde', 'fix_action', 'priority', 'remediation_type']].head(10).to_string())
