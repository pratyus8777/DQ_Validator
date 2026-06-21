"""
Standardization Rules Engine
Handles standardization for dates, phone numbers, emails, addresses, etc.
"""

import pandas as pd
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class StandardizationRules:
    """Define and apply standardization rules across data"""
    
    def __init__(self):
        self.rules = {}
        self._init_default_rules()
    
    def _init_default_rules(self):
        """Initialize default standardization rules"""
        self.rules = {
            # Date columns - standardize to YYYY-MM-DD
            'date_columns': [
                'Policy Effective Date', 'Policy Expiry Date', 'Customer DOB',
                'Endorsement Effective Date', 'Cancellation Effective Date'
            ],
            'date_format': '%Y-%m-%d',  # Standard output format
            
            # Phone columns - standardize to E.164 format
            'phone_columns': ['Phone'],
            'phone_format': 'E164',  # E.164 format (+1234567890)
            'country_code': 'US',  # Default country
            
            # Email columns - lowercase
            'email_columns': ['Email'],
            
            # Name columns - title case
            'name_columns': ['Customer Name', 'Agent Name'],
            
            # ID columns - uppercase
            'id_columns': ['Policy Number', 'Customer ID', 'Coverage ID', 'Agent ID', 'National ID'],
        }
    
    def set_custom_rule(self, column: str, rule_type: str, rule_value: str):
        """Set custom standardization rule for a column"""
        if 'custom_rules' not in self.rules:
            self.rules['custom_rules'] = {}
        
        self.rules['custom_rules'][column] = {
            'type': rule_type,
            'value': rule_value
        }
        logger.info(f"Set custom rule for {column}: {rule_type}={rule_value}")
    
    def standardize_dates(self, df: pd.DataFrame, columns: list = None) -> pd.DataFrame:
        """Standardize date columns to consistent format"""
        df = df.copy()
        cols_to_process = columns or self.rules['date_columns']
        
        for col in cols_to_process:
            if col not in df.columns:
                continue
            
            df[col] = df[col].apply(self._parse_and_format_date)
        
        return df
    
    def _parse_and_format_date(self, value, output_format='%Y-%m-%d'):
        """Parse date in any format and return standardized format"""
        if pd.isna(value) or value == '':
            return None
        
        value_str = str(value).strip()
        if value_str.lower() == 'nan':
            return None
        
        # Try multiple formats
        formats = [
            '%m/%d/%Y', '%d-%m-%Y', '%Y-%m-%d', '%m-%d-%Y', 
            '%d/%m/%Y', '%Y/%m/%d', '%d.%m.%Y', '%m.%d.%Y'
        ]
        
        for fmt in formats:
            try:
                parsed = pd.to_datetime(value_str, format=fmt)
                return parsed.strftime(output_format)
            except:
                pass
        
        # Try flexible parsing
        try:
            parsed = pd.to_datetime(value_str)
            return parsed.strftime(self.rules['date_format'])
        except:
            return value_str  # Return as-is if can't parse
    
    def standardize_phone(self, df: pd.DataFrame, columns: list = None, country_code: str = 'US') -> pd.DataFrame:
        """Standardize phone numbers"""
        df = df.copy()
        cols_to_process = columns or self.rules['phone_columns']
        
        for col in cols_to_process:
            if col not in df.columns:
                continue
            
            df[col] = df[col].apply(lambda x: self._format_phone(x, country_code))
        
        return df
    
    def _format_phone(self, value, country_code='US'):
        """Format phone number to E.164 standard"""
        if pd.isna(value) or value == '':
            return None
        
        value_str = str(value).strip()
        
        # Extract only digits
        digits = re.sub(r'\D', '', value_str)
        
        if not digits:
            return value_str
        
        # Add country code if needed
        if country_code == 'US':
            if len(digits) == 10:
                return f"+1{digits}"
            elif len(digits) == 11 and digits[0] == '1':
                return f"+{digits}"
            elif len(digits) > 11:
                return f"+{digits[-10:]}"  # Take last 10 digits
            else:
                return value_str
        
        return f"+{digits}" if not digits.startswith('+') else digits
    
    def standardize_email(self, df: pd.DataFrame, columns: list = None) -> pd.DataFrame:
        """Standardize email (lowercase)"""
        df = df.copy()
        cols_to_process = columns or self.rules['email_columns']
        
        for col in cols_to_process:
            if col not in df.columns:
                continue
            
            df[col] = df[col].apply(lambda x: str(x).lower() if pd.notna(x) else x)
        
        return df
    
    def standardize_names(self, df: pd.DataFrame, columns: list = None) -> pd.DataFrame:
        """Standardize names to title case"""
        df = df.copy()
        cols_to_process = columns or self.rules['name_columns']
        
        for col in cols_to_process:
            if col not in df.columns:
                continue
            
            df[col] = df[col].apply(lambda x: str(x).title() if pd.notna(x) else x)
        
        return df
    
    def standardize_ids(self, df: pd.DataFrame, columns: list = None) -> pd.DataFrame:
        """Standardize IDs to uppercase"""
        df = df.copy()
        cols_to_process = columns or self.rules['id_columns']
        
        for col in cols_to_process:
            if col not in df.columns:
                continue
            
            df[col] = df[col].apply(lambda x: str(x).upper() if pd.notna(x) else x)
        
        return df
    
    def apply_all_standardization(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all standardization rules"""
        df = self.standardize_dates(df)
        df = self.standardize_phone(df)
        df = self.standardize_email(df)
        df = self.standardize_names(df)
        df = self.standardize_ids(df)
        
        return df
    
    def get_column_standardization_suggestion(self, column: str, data_type: str) -> str:
        """Get suggested standardization rule for a column"""
        suggestions = {
            'date': 'Standardize to YYYY-MM-DD format',
            'phone': 'Standardize to +1-XXX-XXX-XXXX (E.164 format)',
            'email': 'Convert to lowercase',
            'name': 'Convert to Title Case',
            'id': 'Convert to UPPERCASE',
            'currency': 'Remove currency symbols, standardize to 2 decimals',
            'percentage': 'Ensure value is between 0-100',
            'address': 'Standardize to format: Street, City, State ZIP'
        }
        
        # Try to match column name with type
        lower_col = column.lower()
        
        if any(x in lower_col for x in ['date', 'dob', 'effective', 'expiry']):
            return suggestions['date']
        elif any(x in lower_col for x in ['phone', 'mobile', 'telephone']):
            return suggestions['phone']
        elif 'email' in lower_col:
            return suggestions['email']
        elif any(x in lower_col for x in ['name', 'customer', 'agent']):
            return suggestions['name']
        elif any(x in lower_col for x in ['id', 'number', 'code']):
            return suggestions['id']
        
        return ''


class CustomCleansingRuleParser:
    """Parse and apply custom cleansing rules from natural language"""
    
    @staticmethod
    def parse_custom_rule(rule_text: str) -> dict:
        """
        Parse natural language rule into operations
        
        Args:
            rule_text: Natural language rule (e.g., "Convert to lowercase", "Format as phone")
            
        Returns:
            dict with 'operations' list containing parsed operations
        """
        if not rule_text:
            return {'operations': []}
        
        rule_lower = rule_text.lower()
        operations = []
        
        # Match patterns for common operations
        if any(word in rule_lower for word in ['lowercase', 'lower case', 'to lower']):
            operations.append({'op': 'lowercase'})
        
        if any(word in rule_lower for word in ['uppercase', 'upper case', 'to upper']):
            operations.append({'op': 'uppercase'})
        
        if any(word in rule_lower for word in ['trim', 'strip', 'remove spaces', 'remove leading', 'remove trailing']):
            operations.append({'op': 'trim'})
        
        if any(word in rule_lower for word in ['title case', 'title']):
            operations.append({'op': 'title_case'})
        
        if any(word in rule_lower for word in ['phone', 'e.164', 'format phone']):
            operations.append({'op': 'format_phone'})
        
        # Date format detection - be flexible with separators
        if any(word in rule_lower for word in ['date', 'yyyy', 'format date', 'iso 8601', 'mm', 'dd']):
            # Extract desired date format from rule text
            date_format = '%Y-%m-%d'  # Default
            
            # Check for specific format patterns in the rule (case-insensitive, separator-flexible)
            if 'yyyy/mm/dd' in rule_lower:
                date_format = '%Y/%m/%d'
            elif 'yyyy-mm-dd' in rule_lower or 'yyyy mm dd' in rule_lower:
                date_format = '%Y-%m-%d'
            elif 'mm/dd/yyyy' in rule_lower or 'mm-dd-yyyy' in rule_lower:
                date_format = '%m/%d/%Y'
            elif 'dd/mm/yyyy' in rule_lower or 'dd-mm-yyyy' in rule_lower:
                date_format = '%d/%m/%Y'
            elif 'yyyy.mm.dd' in rule_lower:
                date_format = '%Y.%m.%d'
            
            operations.append({'op': 'format_date', 'format': date_format})
        
        if any(word in rule_lower for word in ['email', 'format email']):
            operations.append({'op': 'format_email'})
        
        if 'remove' in rule_lower and 'space' in rule_lower:
            operations.append({'op': 'remove_spaces'})
        
        if 'remove' in rule_lower and 'special' in rule_lower:
            operations.append({'op': 'remove_special_chars'})
        
        if 'remove' in rule_lower and 'leading' in rule_lower:
            operations.append({'op': 'remove_leading_spaces'})
        
        if 'remove' in rule_lower and 'trailing' in rule_lower:
            operations.append({'op': 'remove_trailing_spaces'})
        
        # If no operations matched, try to extract replacement patterns
        if not operations:
            operations.append({'op': 'trim'})  # Default to trim
        
        return {'operations': operations, 'rule_text': rule_text}
    
    @staticmethod
    def apply_custom_rule(value, parsed_rule: dict) -> str:
        """
        Apply parsed rule operations to a value
        
        Args:
            value: The value to transform
            parsed_rule: dict with 'operations' list from parse_custom_rule()
            
        Returns:
            Transformed value
        """
        if pd.isna(value):
            return value
        
        result = str(value)
        operations = parsed_rule.get('operations', [])
        
        for op in operations:
            op_type = op.get('op', '')
            
            if op_type == 'lowercase':
                result = result.lower()
            elif op_type == 'uppercase':
                result = result.upper()
            elif op_type == 'trim':
                result = result.strip()
            elif op_type == 'title_case':
                result = result.title()
            elif op_type == 'remove_spaces':
                result = result.replace(' ', '')
            elif op_type == 'remove_special_chars':
                result = re.sub(r'[^a-zA-Z0-9\s]', '', result)
            elif op_type == 'remove_leading_spaces':
                result = result.lstrip()
            elif op_type == 'remove_trailing_spaces':
                result = result.rstrip()
            elif op_type == 'format_phone':
                # Simple E.164 formatting
                digits = re.sub(r'\D', '', result)
                if len(digits) >= 10:
                    if len(digits) == 10:
                        result = f"({digits[:3]}){digits[3:6]}-{digits[6:]}"
                    else:
                        result = f"+{digits}"
            elif op_type == 'format_email':
                result = result.lower().strip()
            elif op_type == 'format_date':
                # Parse and format date with specified format
                try:
                    date_format = op.get('format', '%Y-%m-%d')
                    from agents.standardization_rules import StandardizationRules
                    sr = StandardizationRules()
                    result = sr._parse_and_format_date(result, output_format=date_format)
                except:
                    pass
        
        return result
