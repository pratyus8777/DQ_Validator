#!/usr/bin/env python
"""
Production Pipeline Test - Tests all new features
"""

import json
import sys
from pathlib import Path

def test_profiling():
    """Test data profiling engine"""
    print("\n" + "="*80)
    print("TEST 1: Data Profiling Engine")
    print("="*80)
    
    try:
        import pandas as pd
        from agents.profiling_orchestrator import DataProfiler
        
        # Load sample data (Neon DB)
        from data_io.db_helpers import read_sample_policy_data
        df = read_sample_policy_data(limit=1000)
        print(f"[OK] Loaded sample data: {df.shape}")
        
        # Profile
        profiler = DataProfiler()
        profile = profiler.profile_dataset(df)
        
        print(f"[OK] Profile generated for {profile['shape']['columns']} columns")
        print(f"  - Records: {profile['shape']['rows']}")
        
        for col_name, col_prof in list(profile['columns'].items())[:3]:
            null_pct = col_prof['null_percentage']
            unique_pct = col_prof['unique_percentage']
            print(f"    - {col_name}: {null_pct:.1f}% nulls, {unique_pct:.1f}% unique")
        
        return True
    except Exception as e:
        print(f"[FAIL] Profiling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rule_manager():
    """Test dynamic rule manager"""
    print("\n" + "="*80)
    print("TEST 2: Dynamic Rule Manager")
    print("="*80)
    
    try:
        import pandas as pd
        from agents.profiling_orchestrator import DynamicRuleManager
        
        # Create manager
        rule_manager = DynamicRuleManager({})
        
        # Start session
        session_id = "test_session_001"
        rule_manager.start_session(session_id)
        print(f"[OK] Session started: {session_id}")
        
        # Load base rules
        from data_io.db_helpers import read_guidewire_cleansing_rules, read_sample_policy_data
        base_rules = read_guidewire_cleansing_rules()
        sample_df = read_sample_policy_data(limit=1000)
        
        # Get effective rules
        effective_rules = rule_manager.get_effective_rules(sample_df, base_rules)
        print(f"[OK] Effective rules computed: {len(effective_rules)} rules")
        
        # End session
        rule_manager.end_session()
        print(f"[OK] Session ended")
        
        return True
    except Exception as e:
        print(f"[FAIL] Rule manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_assessment_engine():
    """Test assessment engine"""
    print("\n" + "="*80)
    print("TEST 3: Assessment Engine")
    print("="*80)
    
    try:
        import pandas as pd
        from deterministic_engine.assessment_engine import AssessmentEngine
        from deterministic_engine.dynamic_rule_executor import RuleExecutionResult
        
        # Create assessment engine
        config = {}
        engine = AssessmentEngine(config)
        
        # Load sample data
        df = pd.read_csv("data/Sample_Policy_Data.csv")
        
        # Create mock violations
        mock_violations = [
            RuleExecutionResult(
                record_id=0,
                column="Policy Number",
                rule_id="rule_1",
                check_type="not_null",
                passed=False,
                issue_type="null_value",
                original_value=None,
                confidence=1.0,
                execution_method="deterministic"
            )
        ]
        
        # Generate assessment
        assessment = engine.generate_assessment(
            df,
            mock_violations,
            assessment_id="TEST_001",
            phase="before"
        )
        
        print(f"[OK] Assessment generated")
        print(f"  - Total violations: {assessment['total_violations']}")
        print(f"  - Pass rate: {assessment['pass_rate']:.1f}%")
        print(f"  - DQ score: {assessment['overall_dq_score']:.1f}/100")
        
        return True
    except Exception as e:
        print(f"[FAIL] Assessment engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_client():
    """Test LLM client"""
    print("\n" + "="*80)
    print("TEST 4: LLM Client Integration")
    print("="*80)
    
    try:
        import yaml
        from llm.llm_client import LLMClient
        
        # Load config
        with open('config/local.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Initialize LLM client
        llm_client = LLMClient(config['llm'])
        
        print(f"[OK] LLM Client initialized")
        print(f"  - Provider: {llm_client.provider}")
        print(f"  - Model: {llm_client.model}")
        print(f"  - Available: {llm_client.available}")
        
        return True
    except Exception as e:
        print(f"[FAIL] LLM test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("PRODUCTION PIPELINE VALIDATION SUITE")
    print("="*80)
    
    tests = [
        ("Data Profiling", test_profiling),
        ("Dynamic Rule Manager", test_rule_manager),
        ("Assessment Engine", test_assessment_engine),
        ("LLM Client Integration", test_llm_client),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n[FAIL] {test_name} - Unexpected error: {e}")
            results[test_name] = False
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "[OK]" if result else "[FAIL]"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed! Production system is ready.")
        return 0
    else:
        print(f"\n[WARN] {total - passed} test(s) failed. Review logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
