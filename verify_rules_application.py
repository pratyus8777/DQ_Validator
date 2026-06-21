import pandas as pd
import traceback
from rules_parser import RulesParser
from deterministic_engine.dynamic_rule_executor import DynamicRuleExecutor

CONFIG = {'llm': {}}

def main():
    # Load data
    df = pd.read_csv('data/Sample_Policy_Data.csv', encoding='latin-1')

    # Parse descriptive rules into executable rules
    rules_df = RulesParser.parse_descriptive_rules('data/DQ_Rule_Repository-Policy.csv')
    if rules_df is None or rules_df.empty:
        print('No executable rules parsed. Exiting.')
        return

    # Normalize column name keys to match executor expectations
    # Executor accepts 'cde' or 'column'
    if 'column' in rules_df.columns and 'cde' not in rules_df.columns:
        rules_df['cde'] = rules_df['column']

    # Instantiate executor
    executor = DynamicRuleExecutor(CONFIG)

    summary = {
        'total_rules': len(rules_df),
        'rules_executed': 0,
        'rules_failed': [],
        'rules_no_column': [],
        'violations_by_rule': {},
        'columns_covered': set(),
    }

    print(f"Loaded {len(df)} records and {len(rules_df)} executable rules.\n")

    for idx, rule in rules_df.iterrows():
        rule_id = rule.get('rule_id') or f'RULE_{idx}'
        cde = rule.get('cde') or rule.get('column')
        try:
            if not cde or cde not in df.columns:
                summary['rules_no_column'].append({'rule_id': rule_id, 'column': cde})
                print(f"SKIP: Rule {rule_id} - column '{cde}' not found in data")
                continue

            # Execute single rule
            violations = executor._execute_single_rule(df, rule)
            summary['rules_executed'] += 1
            summary['columns_covered'].add(cde)
            summary['violations_by_rule'][rule_id] = len(violations)

            print(f"EXECUTED: {rule_id} on column '{cde}' -> {len(violations)} violations")

        except Exception as e:
            summary['rules_failed'].append({'rule_id': rule_id, 'error': str(e), 'trace': traceback.format_exc()})
            print(f"ERROR: Rule {rule_id} -> {e}")

    # Post-checks
    all_columns = set(df.columns.tolist())
    covered_columns = summary['columns_covered']
    uncovered_columns = sorted(list(all_columns - covered_columns))

    print('\n=== SUMMARY ===')
    print(f"Total rules: {summary['total_rules']}")
    print(f"Rules executed: {summary['rules_executed']}")
    print(f"Rules skipped (missing column): {len(summary['rules_no_column'])}")
    print(f"Rules failed: {len(summary['rules_failed'])}")
    print(f"Columns covered by rules: {len(covered_columns)} / {len(all_columns)}")
    if uncovered_columns:
        print('Uncovered columns (no rule applies):')
        for col in uncovered_columns:
            print(f"  - {col}")

    # Show top rules by violations
    print('\nTop rules by violations:')
    items = sorted(summary['violations_by_rule'].items(), key=lambda x: x[1], reverse=True)
    for r, cnt in items[:10]:
        print(f"  {r}: {cnt}")

    # Write summary to file
    out = pd.DataFrame([summary['violations_by_rule']]).T.reset_index()
    out.columns = ['rule_id', 'violations']
    out.to_csv('output/Rules_Application_Summary.csv', index=False)
    print('\nWrote output/Rules_Application_Summary.csv')

if __name__ == '__main__':
    main()
