from rules_engine.fix_actions import FIX_ACTION_REGISTRY
from rules_engine.checks import CHECK_REGISTRY


# -------------------------------
# VALIDATION DISPATCH
# -------------------------------
def run_check(df, rule):
    check_type = rule["check_type"]

    if check_type not in CHECK_REGISTRY:
        raise ValueError(f"Unsupported check_type: {check_type}")

    check_fn = CHECK_REGISTRY[check_type]
    return check_fn(df, rule)


# -------------------------------
# FIX DISPATCH (🔥 MISSING PIECE 🔥)
# -------------------------------
def run_fix(df, rule, llm_client=None):
    fix_action = rule.get("fix_action")

    if not fix_action:
        return df

    if fix_action not in FIX_ACTION_REGISTRY:
        # Unknown fix → no-op (safe)
        return df

    fix_fn = FIX_ACTION_REGISTRY[fix_action]

    return fix_fn(
        df=df,
        rule=rule,
        llm_client=llm_client
    )
