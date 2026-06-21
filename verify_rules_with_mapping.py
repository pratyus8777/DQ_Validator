import pandas as pd
import difflib
import traceback
from rules_parser import RulesParser
from deterministic_engine.dynamic_rule_executor import DynamicRuleExecutor

CONFIG = {'llm': {}}


def find_best_match(cde, columns):
    # Exact match
    if cde in columns:
        return cde
    # Case-insensitive exact
    lc = {col.lower(): col for col in columns}
    if cde.lower() in lc:
        return lc[cde.lower()]
    # Remove punctuation/spaces
    def normalize(s):
        return ''.join(ch for ch in s.lower() if ch.isalnum())
    norm = {normalize(col): col for col in columns}
    if normalize(cde) in norm:
        return norm[normalize(cde)]
    # Substring match
    for col in columns:
        if cde.lower() in col.lower() or col.lower() in cde.lower():
            return col
    # difflib close match
    matches = difflib.get_close_matches(cde, columns, n=1, cutoff=0.6)
    if matches:
        return matches[0]
    return None


def main():
    df = pd.read_csv('data/Sample_Policy_Data.csv', encoding='latin-1')
    rules_df = RulesParser.parse_descriptive_rules('data/DQ_Rule_Repository-Policy.csv')
    if rules_df is None or rules_df.empty:
        print('No rules parsed; exiting')
        return

    # Ensure column key
    if 'column' in rules_df.columns and 'cde' not in rules_df.columns:
        rules_df['cde'] = rules_df['column']

    columns = list(df.columns)
    mapping = {}

    for idx, row in rules_df.iterrows():
        cde = row.get('cde') or row.get('column')
        if not cde or cde in columns:
            mapping[cde] = cde
            continue
        best = find_best_match(cde, columns)
        mapping[cde] = best

    # Save mapping
    mapping_df = pd.DataFrame([(k, v) for k, v in mapping.items()], columns=['rule_cde', 'mapped_column'])
    mapping_df.to_csv('output/Rules_to_Columns_Mapping.csv', index=False)
    print('Wrote output/Rules_to_Columns_Mapping.csv')

    executor = DynamicRuleExecutor(CONFIG)
    summary = {'total_rules': len(rules_df), 'executed':0, 'skipped':0, 'failed':[], 'violations_by_rule':{}}

    for idx, row in rules_df.iterrows():
        rule_id = row.get('rule_id') or f'RULE_{idx}'
        orig_cde = row.get('cde')
        mapped = mapping.get(orig_cde)
        if not mapped:
            print(f"SKIP: {rule_id} - no mapped column for '{orig_cde}'")
            summary['skipped'] += 1
            continue
        # set the rule to use mapped column
        row['cde'] = mapped
        try:
            violations = executor._execute_single_rule(df, row)
            summary['executed'] += 1
            summary['violations_by_rule'][rule_id] = len(violations)
            print(f"EXECUTED: {rule_id} -> column '{mapped}' -> {len(violations)} violations")
        except Exception as e:
            summary['failed'].append({'rule_id': rule_id, 'error': str(e)})
            print(f"ERROR executing {rule_id}: {e}")

    # Report
    print('\n=== MAPPED EXECUTION SUMMARY ===')
    print(f"Total rules: {summary['total_rules']}")
    print(f"Executed: {summary['executed']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Failed: {len(summary['failed'])}")

    top = sorted(summary['violations_by_rule'].items(), key=lambda x: x[1], reverse=True)
    print('\nTop rules by violations:')
    for r,c in top[:10]:
        print(f"  {r}: {c}")

    pd.DataFrame(list(summary['violations_by_rule'].items()), columns=['rule_id','violations']).to_csv('output/Rules_Application_Summary_Mapped.csv', index=False)
    print('Wrote output/Rules_Application_Summary_Mapped.csv')

if __name__ == '__main__':
    main()
