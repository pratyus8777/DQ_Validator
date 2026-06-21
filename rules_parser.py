"""
Smart Rules Parser - Converts descriptive DQ rules into executable rules
Generates structured rules from the Guidewire/Policy DQ descriptive files
"""

import pandas as pd
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class RulesParser:
    """Parse descriptive DQ rules and convert to executable format."""
    
    @staticmethod
    def parse_descriptive_rules(rules_file: str) -> pd.DataFrame:
        """
        Parse descriptive DQ rules from CSV and convert to executable format.
        
        Each row in the output will have:
        - rule_id: unique identifier
        - column: CDE (column to check)
        - dimension: Completeness, Validity, Accuracy, Consistency, Uniqueness, etc.
        - check_type: Type of check (not_null, not_blank, regex, etc.)
        - check_params: Parameters for the check
        """
        
        try:
            # Read the descriptive rules
            df_rules = pd.read_csv(rules_file, encoding='latin-1')
            executable_rules = []
            
            # Map columns to checks
            for idx, row in df_rules.iterrows():
                rule_id = f"RULE_{idx + 1}"
                cde = row.get('CDE', '').strip()
                
                if not cde or pd.isna(cde):
                    continue
                
                # Parse completeness rules
                completeness = str(row.get('Completeness', '')).strip()
                if completeness and completeness != 'nan':
                    executable_rules.append({
                        'rule_id': f"{rule_id}_COMPLETENESS",
                        'column': cde,
                        'dimension': 'Completeness',
                        'check_type': 'not_null',
                        'check_params': {},
                        'description': f"Check {cde} is not null/blank"
                    })
                
                # Parse validity rules
                validity = str(row.get('Validity / Conformance', '')).strip()
                if validity and validity != 'nan':
                    rules_from_validity = RulesParser._parse_validity(cde, validity)
                    executable_rules.extend(rules_from_validity)
                
                # Parse accuracy rules
                accuracy = str(row.get('Accuracy', '')).strip()
                if accuracy and accuracy != 'nan':
                    rules_from_accuracy = RulesParser._parse_accuracy(cde, accuracy)
                    executable_rules.extend(rules_from_accuracy)
                
                # Parse consistency rules
                consistency = str(row.get('Consistency', '')).strip()
                if consistency and consistency != 'nan':
                    rules_from_consistency = RulesParser._parse_consistency(cde, consistency)
                    executable_rules.extend(rules_from_consistency)
                
                # Parse uniqueness rules
                uniqueness = str(row.get('Uniqueness / Deduplication', '')).strip()
                if uniqueness and uniqueness != 'nan' and 'unique' in uniqueness.lower():
                    executable_rules.append({
                        'rule_id': f"{rule_id}_UNIQUENESS",
                        'column': cde,
                        'dimension': 'Uniqueness',
                        'check_type': 'unique_in_dataset',
                        'check_params': {},
                        'description': f"Check {cde} is unique"
                    })
            
            return pd.DataFrame(executable_rules)
        
        except Exception as e:
            logger.error(f"Failed to parse rules: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def _parse_validity(column: str, validity_text: str) -> List[Dict[str, Any]]:
        """Extract validity/format rules from descriptive text."""
        rules = []
        
        # Check for date format patterns
        if 'date' in column.lower() or any(x in validity_text.lower() for x in ['mm/dd/yyyy', 'yyyy-mm-dd', 'format']):
            rules.append({
                'rule_id': f"{column}_VALIDITY_DATEFORMAT",
                'column': column,
                'dimension': 'Validity',
                'check_type': 'date_format',
                'check_params': {'formats': ['%m/%d/%Y', '%d-%m-%Y', '%Y-%m-%d', '%m-%d-%Y']},
                'description': f"Check {column} is valid date"
            })
        
        # Check for length constraints
        if 'length' in validity_text.lower():
            # Extract length specifications
            if '=' in validity_text:
                parts = validity_text.split('=')
                if len(parts) > 1:
                    try:
                        length = int(''.join(filter(str.isdigit, parts[1].split()[0])))
                        rules.append({
                            'rule_id': f"{column}_VALIDITY_LENGTH",
                            'column': column,
                            'dimension': 'Validity',
                            'check_type': 'length_in',
                            'check_params': {'min': length, 'max': length},
                            'description': f"Check {column} length equals {length}"
                        })
                    except:
                        pass
        
        # Check for patterns/regex
        if 'pattern' in validity_text.lower() or 'format' in validity_text.lower():
            if 'alphanumeric' in validity_text.lower():
                rules.append({
                    'rule_id': f"{column}_VALIDITY_ALPHANUMERIC",
                    'column': column,
                    'dimension': 'Validity',
                    'check_type': 'regex',
                    'check_params': {'pattern': '^[a-zA-Z0-9]+$'},
                    'description': f"Check {column} is alphanumeric"
                })
            elif 'numeric' in validity_text.lower():
                rules.append({
                    'rule_id': f"{column}_VALIDITY_NUMERIC",
                    'column': column,
                    'dimension': 'Validity',
                    'check_type': 'regex',
                    'check_params': {'pattern': '^[0-9]+$'},
                    'description': f"Check {column} is numeric"
                })
        
        return rules
    
    @staticmethod
    def _parse_accuracy(column: str, accuracy_text: str) -> List[Dict[str, Any]]:
        """Extract accuracy rules from descriptive text."""
        rules = []
        
        # Check for range constraints
        if 'range' in accuracy_text.lower() or any(x in accuracy_text for x in ['<', '>', '=']):
            rules.append({
                'rule_id': f"{column}_ACCURACY_RANGE",
                'column': column,
                'dimension': 'Accuracy',
                'check_type': 'range',
                'check_params': {'description': accuracy_text},
                'description': f"Check {column} is within valid range: {accuracy_text}"
            })
        
        # Check for master data linkages
        if 'valid' in accuracy_text.lower() and 'master' in accuracy_text.lower():
            rules.append({
                'rule_id': f"{column}_ACCURACY_MASTERDATA",
                'column': column,
                'dimension': 'Accuracy',
                'check_type': 'not_null',  # Fallback to not_null for now
                'check_params': {},
                'description': f"Check {column} references valid master data"
            })
        
        return rules
    
    @staticmethod
    def _parse_consistency(column: str, consistency_text: str) -> List[Dict[str, Any]]:
        """Extract consistency rules from descriptive text."""
        rules = []
        
        # Check for relationship constraints
        if 'linked' in consistency_text.lower() or 'reference' in consistency_text.lower():
            rules.append({
                'rule_id': f"{column}_CONSISTENCY_REFERENCE",
                'column': column,
                'dimension': 'Consistency',
                'check_type': 'not_null',  # Fallback
                'check_params': {},
                'description': f"Check {column} is consistent: {consistency_text}"
            })
        
        # Check for comparison constraints
        if '>' in consistency_text or '<' in consistency_text or '=' in consistency_text:
            rules.append({
                'rule_id': f"{column}_CONSISTENCY_COMPARISON",
                'column': column,
                'dimension': 'Consistency',
                'check_type': 'range',
                'check_params': {'description': consistency_text},
                'description': f"Check {column} comparison: {consistency_text}"
            })
        
        return rules


if __name__ == "__main__":
    # Test the parser
    rules_df = RulesParser.parse_descriptive_rules('data/DQ_Rule_Repository-Policy.csv')
    print(f"Parsed {len(rules_df)} executable rules")
    print(rules_df.head(10))
    print("\nRule dimensions:")
    print(rules_df['dimension'].value_counts())
    print("\nCheck types:")
    print(rules_df['check_type'].value_counts())
