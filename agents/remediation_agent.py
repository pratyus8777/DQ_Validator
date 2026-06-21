import pandas as pd
import logging
from rules_engine.dispatcher import run_fix
from agents.cleansing_rule_parser import CleansingRuleParser

logger = logging.getLogger(__name__)


class RemediationAgent:
    """
    Applies deterministic cleansing rules to the dataset.
    Converts descriptive rules into actionable fix configurations.
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.parser = CleansingRuleParser()

    def run(self, context: dict) -> dict:
        df = context["data"].copy()
        raw_rules_df = context.get("cleansing_rules")

        # If remediation not allowed, return original data
        if not context.get("remediation_allowed", False):
            logger.warning("Remediation not approved - returning original data")
            return {"data": df}

        if raw_rules_df is None or raw_rules_df.empty:
            logger.warning("No cleansing rules provided")
            return {"data": df}

        # Parse descriptive rules into actionable fix configurations
        logger.info("Parsing cleansing rules...")
        rules_df = self.parser.parse_cleansing_rules(raw_rules_df)
        
        if rules_df.empty:
            logger.warning("No parseable cleansing rules found")
            return {"data": df}

        logger.info(f"Parsed {len(rules_df)} cleansing rules")

        # Apply rules in priority order
        rules_df = rules_df.sort_values("priority", ascending=True)

        applied_fixes = 0
        for _, rule in rules_df.iterrows():
            try:
                df_before = len(df)
                df = self._apply_rule(df, rule)
                df_after = len(df)
                
                if df_after != df_before:
                    logger.info(f"Rule affected {df_before - df_after} rows")
                
                applied_fixes += 1
            except Exception as e:
                logger.error(f"Failed to apply rule for {rule['cde']}: {e}")
                # Continue with next rule (fail-safe)

        logger.info(f"Applied {applied_fixes} remediation rules")
        return {"data": df}

    def _apply_rule(self, df: pd.DataFrame, rule: pd.Series) -> pd.DataFrame:
        """
        Applies a single cleansing rule.
        Converts Series to dict for compatibility with run_fix.
        """
        try:
            # Convert Series to dict
            rule_dict = rule.to_dict()
            
            updated_df = run_fix(
                df=df,
                rule=rule_dict,
                llm_client=self.llm
            )
            return updated_df if updated_df is not None else df

        except Exception as e:
            logger.warning(f"Rule application failed for {rule.get('cde')}: {e}")
            # Fail-safe: never crash remediation, return unchanged data
            return df
