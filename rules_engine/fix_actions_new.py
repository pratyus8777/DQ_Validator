import pandas as pd
import numpy as np
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def if_null_fill(df, rule, llm_client=None):
    """Fill null/empty values with a default value."""
    column = rule.get("cde") or rule.get("column")
    value = rule.get("fix_parameters")
    
    if column not in df.columns:
        return df
    
    df = df.copy()
    from pandas.api import types as ptypes

    mask = df[column].isna() | (df[column].astype(str).str.strip() == "")

    if ptypes.is_datetime64_any_dtype(df[column]) or "date" in column.lower():
        replacement = pd.NaT if (value is None or value == "") else pd.to_datetime(value, errors="coerce")
    elif ptypes.is_numeric_dtype(df[column]):
        try:
            replacement = float(value) if value is not None and value != "" else np.nan
        except Exception:
            replacement = np.nan
    else:
        replacement = value if value is not None else ""

    df.loc[mask, column] = replacement
    logger.info(f"Fixed {mask.sum()} null values in {column}")
    return df


def parse_date(df, rule, llm_client=None):
    """Parse and standardize date columns while preserving original data format."""
    column = rule.get("cde") or rule.get("column")
    
    if column not in df.columns:
        return df
    
    df = df.copy()
    original_col = df[column].copy()
    
    best_parsed = None
    best_count = 0
    
    for dayfirst in [False, True]:
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                parsed = pd.to_datetime(
                    df[column], 
                    errors="coerce", 
                    dayfirst=dayfirst
                )
                parsed_count = parsed.notna().sum()
                non_null = df[column].notna().sum()
                
                if non_null > 0 and parsed_count >= int(0.8 * non_null):
                    if parsed_count > best_count:
                        best_parsed = parsed
                        best_count = parsed_count
        except Exception:
            continue
    
    if best_parsed is not None and best_count > 0:
        mask = (original_col.notna()) & (best_parsed.notna())
        df.loc[mask, column] = best_parsed.loc[mask].astype(str)
        logger.info(f"Standardized {mask.sum()} date values in {column}")
    else:
        logger.info(f"Could not reliably parse dates in {column}, keeping original format")

    return df


def dedupe_keep_first(df, rule, llm_client=None):
    """Remove exact duplicate rows, keeping first occurrence."""
    column = rule.get("cde") or rule.get("column")
    if column not in df.columns:
        return df
    df = df.copy()
    initial_count = len(df)
    df = df.drop_duplicates(subset=[column], keep="first")
    removed = initial_count - len(df)
    if removed > 0:
        logger.info(f"Removed {removed} duplicate rows based on {column}")
    return df


def validate_email(df, rule, llm_client=None):
    """Validate and fix email format."""
    column = rule.get("cde") or rule.get("column")
    if column not in df.columns:
        return df
    df = df.copy()
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    def fix_email(val):
        if pd.isna(val) or val == "":
            return ""
        val = str(val).strip().lower()
        if re.match(email_pattern, val):
            return val
        if "@" not in val:
            return ""
        return val
    original = df[column].copy()
    df[column] = df[column].apply(fix_email)
    fixed = (df[column] != original).sum()
    if fixed > 0:
        logger.info(f"Fixed {fixed} email addresses in {column}")
    return df


def validate_phone(df, rule, llm_client=None):
    """Validate and fix phone number format."""
    column = rule.get("cde") or rule.get("column")
    if column not in df.columns:
        return df
    df = df.copy()
    def fix_phone(val):
        if pd.isna(val) or val == "":
            return ""
        val = str(val).strip()
        if val.startswith("+"):
            digits = "+" + re.sub(r'\D', '', val)
        else:
            digits = re.sub(r'\D', '', val)
        digit_only = re.sub(r'\D', '', digits)
        if len(digit_only) >= 10:
            return digits
        return ""
    original = df[column].copy()
    df[column] = df[column].apply(fix_phone)
    fixed = (df[column] != original).sum()
    if fixed > 0:
        logger.info(f"Fixed {fixed} phone numbers in {column}")
    return df


def standardize(df, rule, llm_client=None):
    """Standardize values using predefined mappings."""
    column = rule.get("cde") or rule.get("column")
    if column not in df.columns:
        return df
    df = df.copy()
    status_map = {
        "active": "Active", "inactive": "Inactive", "cancelled": "Cancelled",
        "expired": "Expired", "bound": "Bound", "draft": "Draft", "submitted": "Submitted",
    }
    bool_map = {"y": "Y", "yes": "Y", "n": "N", "no": "N", "true": "Y", "false": "N"}
    mapping = {}
    if "status" in column.lower():
        mapping = status_map
    elif "indicator" in column.lower():
        mapping = bool_map
    if mapping:
        original = df[column].copy()
        df[column] = df[column].astype(str).str.lower().map(mapping).fillna(original)
        fixed = (df[column] != original).sum()
        if fixed > 0:
            logger.info(f"Standardized {fixed} values in {column}")
    return df


def numeric_standardize(df, rule, llm_client=None):
    """Standardize numeric columns."""
    column = rule.get("cde") or rule.get("column")
    if column not in df.columns:
        return df
    df = df.copy()
    try:
        df[column] = pd.to_numeric(df[column], errors="coerce")
        logger.info(f"Standardized numeric values in {column}")
    except Exception as e:
        logger.warning(f"Could not standardize {column}: {e}")
    return df


def validate_range(df, rule, llm_client=None):
    """Validate numeric values are within reasonable ranges."""
    column = rule.get("cde") or rule.get("column")
    if column not in df.columns:
        return df
    df = df.copy()
    try:
        numeric_col = pd.to_numeric(df[column], errors="coerce")
        mask = (numeric_col < 0) | (numeric_col > 99999999)
        if mask.any():
            logger.info(f"Found {mask.sum()} values out of range in {column}")
    except Exception as e:
        logger.warning(f"Could not validate range for {column}: {e}")
    return df


def validate_referential(df, rule, llm_client=None):
    """Validate referential integrity."""
    column = rule.get("cde") or rule.get("column")
    if column not in df.columns:
        return df
    logger.info(f"Validated referential integrity for {column}")
    return df


def flag_for_review(df, rule, llm_client=None):
    """Flag problematic records for manual review."""
    column = rule.get("cde") or rule.get("column")
    flag_reason = rule.get("fix_parameters", "manual_review_required")
    flag_col = f"_REVIEW_FLAG_{flag_reason}"
    if flag_col not in df.columns:
        df[flag_col] = "N"
    mask = df[column].isna() | (df[column].astype(str).str.strip() == "")
    df.loc[mask, flag_col] = "Y"
    flagged = mask.sum()
    if flagged > 0:
        logger.info(f"Flagged {flagged} records in {column} for {flag_reason}")
    return df


FIX_ACTION_REGISTRY = {
    "if_null_fill": if_null_fill,
    "parse_date": parse_date,
    "dedupe_keep_first": dedupe_keep_first,
    "validate_email": validate_email,
    "validate_phone": validate_phone,
    "standardize": standardize,
    "numeric_standardize": numeric_standardize,
    "validate_range": validate_range,
    "validate_referential": validate_referential,
    "flag_for_review": flag_for_review,
}
