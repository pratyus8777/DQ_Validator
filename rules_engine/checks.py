import pandas as pd
import re


# --------------------------------------------------
# CHECK FUNCTIONS
# Each returns a DataFrame of FAILED rows
# --------------------------------------------------

def not_null(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    col = rule["cde"]
    return df[df[col].isnull()]


def not_blank(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    col = rule["cde"]
    return df[df[col].astype(str).str.strip() == ""]


def regex(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    col = rule["cde"]
    pattern = rule.get("parameters")
    if not pattern:
        return pd.DataFrame()
    return df[~df[col].astype(str).str.match(pattern, na=False)]


def date_format(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    col = rule["cde"]
    parsed = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    return df[parsed.isnull() & df[col].notnull()]


def gte_field(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    col = rule["cde"]
    other = rule.get("parameters")
    if not other:
        return pd.DataFrame()
    return df[df[col] < df[other]]


def lte_field(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    col = rule["cde"]
    other = rule.get("parameters")
    if not other:
        return pd.DataFrame()
    return df[df[col] > df[other]]


def in_set(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    col = rule["cde"]
    allowed = rule.get("parameters")
    if not allowed:
        return pd.DataFrame()
    allowed_set = set(str(allowed).split(","))
    return df[~df[col].astype(str).isin(allowed_set)]


def length_in(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    col = rule["cde"]
    lengths = rule.get("parameters")
    if not lengths:
        return pd.DataFrame()
    allowed = set(int(x) for x in str(lengths).split(","))
    return df[~df[col].astype(str).str.len().isin(allowed)]


def unique_in_dataset(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    col = rule["cde"]
    return df[df.duplicated(subset=[col], keep=False)]


def range_check(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    col = rule["cde"]
    params = rule.get("parameters")
    if not params or "-" not in str(params):
        return pd.DataFrame()
    low, high = map(float, str(params).split("-"))
    return df[(df[col] < low) | (df[col] > high)]


# --------------------------------------------------
# REGISTRY (🔥 REQUIRED 🔥)
# --------------------------------------------------
CHECK_REGISTRY = {
    "not_null": not_null,
    "not_blank": not_blank,
    "regex": regex,
    "date_format": date_format,
    "gte_field": gte_field,
    "lte_field": lte_field,
    "in_set": in_set,
    "length_in": length_in,
    "unique_in_dataset": unique_in_dataset,
    "range": range_check,
}
