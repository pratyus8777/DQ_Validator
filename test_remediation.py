import pandas as pd
from agents.remediation_agent import RemediationAgent
from data_io.db_helpers import read_sample_policy_data, read_guidewire_cleansing_rules

# Load the data and rules from Neon DB
data = read_sample_policy_data(limit=1000)
cleansing_rules = read_guidewire_cleansing_rules()

print(f'Original data: {len(data)} records')
print(f'Cleansing rules: {len(cleansing_rules)} rows')

# Run remediation agent
agent = RemediationAgent()
context = {
    "data": data,
    "cleansing_rules": cleansing_rules,
    "remediation_allowed": True
}

result = agent.run(context)
output_data = result["data"]

print(f'After remediation: {len(output_data)} records')

# Show which rules were parsed
from agents.cleansing_rule_parser import CleansingRuleParser
parser = CleansingRuleParser()
parsed = parser.parse_cleansing_rules(cleansing_rules)
print(f'\nParsed {len(parsed)} rules')
print('\nRules by type:')
print(parsed['remediation_type'].value_counts())
