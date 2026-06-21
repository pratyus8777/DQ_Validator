import pandas as pd
from agents.cleansing_rule_parser import CleansingRuleParser
import logging

# Suppress logs for clarity
logging.getLogger().setLevel(logging.WARNING)

data = pd.read_csv('data/Sample_Policy_Data.csv')
from data_io.db_helpers import read_guidewire_cleansing_rules

rules_raw = read_guidewire_cleansing_rules()

print('📊 RULE ANALYSIS - WHICH RULES MODIFY DATA?')
print('='*80)

parser = CleansingRuleParser()
parsed = parser.parse_cleansing_rules(rules_raw)

# Categorize rules
modifying_actions = ['parse_date', 'if_null_fill', 'standardize', 'numeric_standardize', 
                     'validate_email', 'validate_phone', 'validate_range', 'dedupe_keep_first']
non_modifying = ['flag_for_review', 'validate_referential']

print('\n📝 RULE DISTRIBUTION:')
print('-'*80)

modifying = parsed[parsed['fix_action'].isin(modifying_actions)]
non_modifying_rules = parsed[parsed['fix_action'].isin(non_modifying)]
other = parsed[~parsed['fix_action'].isin(modifying_actions + non_modifying)]

print(f'Data-modifying rules: {len(modifying)} ({100*len(modifying)/len(parsed):.0f}%)')
print(f'  By action:')
for action in modifying_actions:
    count = len(modifying[modifying['fix_action'] == action])
    if count > 0:
        print(f'    {action}: {count}')

print(f'\nNon-modifying rules: {len(non_modifying_rules)} ({100*len(non_modifying_rules)/len(parsed):.0f}%)')
print(f'  flag_for_review: {len(non_modifying_rules[non_modifying_rules["fix_action"]=="flag_for_review"])}')
print(f'  validate_referential: {len(non_modifying_rules[non_modifying_rules["fix_action"]=="validate_referential"])}')

print(f'\nOther: {len(other)}')

print('\n📋 COLUMNS AFFECTED BY MODIFYING RULES:')
print('-'*80)

for col in sorted(modifying['cde'].unique()):
    col_rules = modifying[modifying['cde'] == col]
    actions = col_rules['fix_action'].unique()
    print(f'{col}:')
    for action in actions:
        count = len(col_rules[col_rules['fix_action'] == action])
        print(f'  - {action} ({count})')
