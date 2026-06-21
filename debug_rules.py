import pandas as pd
from agents.cleansing_rule_parser import CleansingRuleParser
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

# Load and parse rules
from data_io.db_helpers import read_guidewire_cleansing_rules

rules_raw = read_guidewire_cleansing_rules()
parser = CleansingRuleParser()
parsed = parser.parse_cleansing_rules(rules_raw)

# Filter to see what rules are generated for key columns
print('📋 PARSED RULES FOR SPECIFIC COLUMNS:')
print('='*70)

test_columns = ['Policy Status', 'Email', 'Phone', 'Coverage Limit', 'Policy Number']

for col in test_columns:
    col_rules = parsed[parsed['cde'] == col]
    print(f'\n{col}:')
    if len(col_rules) == 0:
        print('  NO RULES FOUND!')
    else:
        for idx, rule in col_rules.iterrows():
            print(f'  [{rule["priority"]}] {rule["fix_action"]}')
            print(f'      Params: {rule.get("fix_parameters", "N/A")}')
            print(f'      Type: {rule.get("remediation_type", "N/A")}')

print('\n' + '='*70)
print('Now testing remediation agent directly...')

data = pd.read_csv('data/Sample_Policy_Data.csv')

# Test just on Policy Status
print(f'\nPolicy Status before: {data["Policy Status"].unique()[:5]}')
print(f'Email before: {data["Email"].unique()[:5]}')

from agents.remediation_agent import RemediationAgent
agent = RemediationAgent()
context = {
    'data': data,
    'cleansing_rules': rules_raw,
    'remediation_allowed': True
}

result = agent.run(context)
cleaned = result['data']

print(f'\nPolicy Status after: {cleaned["Policy Status"].unique()[:5]}')
print(f'Email after: {cleaned["Email"].unique()[:5]}')

print('\nDid standardize work?')
print(f'Policy Status changed: {(data["Policy Status"] != cleaned["Policy Status"]).sum()} records')
print(f'Email changed: {(data["Email"] != cleaned["Email"]).sum()} records')
