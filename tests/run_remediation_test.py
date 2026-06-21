import pandas as pd
from agents.remediation_agent import RemediationAgent
from semantic_engine.interpreter import OllamaClient
import os

DATA_PATH = os.path.join("data", "Sample_Policy_Data.csv")
RULES_PATH = os.path.join("data", "Guidewire_Policy_DataCleansing_Rules.csv")


def load_files():
    df = pd.read_csv(DATA_PATH)
    rules = pd.read_csv(RULES_PATH)
    return df, rules


def compare_cols(before, after):
    diffs = {}
    for col in before.columns:
        b = before[col]
        a = after[col] if col in after.columns else pd.Series([None]*len(before))
        # Count differences treating NaN as equal
        neq = (~b.fillna("__NA__").astype(str).eq(a.fillna("__NA__").astype(str))).sum()
        diffs[col] = int(neq)
    return diffs


def main():
    df, rules = load_files()
    print(f"Loaded data: {len(df)} rows, {len(df.columns)} columns")
    print(f"Loaded rules: {len(rules)} rows")

    ollama = OllamaClient("http://localhost:11434")
    agent = RemediationAgent(ollama)

    context = {"data": df.copy(), "cleansing_rules": rules, "remediation_allowed": True}

    before = context["data"].copy()
    result = agent.run(context)
    after = result.get("data")

    diffs = compare_cols(before, after)
    print("Per-column changed value counts:")
    for c, v in diffs.items():
        print(f" - {c}: {v}")

    out_dir = "output"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "Sample_Policy_Data_clean_test.csv")
    after.to_csv(out_path, index=False)
    print(f"Wrote cleaned sample to {out_path}")


if __name__ == '__main__':
    main()
