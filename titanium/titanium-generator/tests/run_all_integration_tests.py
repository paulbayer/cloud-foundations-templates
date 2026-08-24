#!/usr/bin/env python3
"""
Run all integration tests for template naming standardization.
This script runs all integration tests and provides a comprehensive summary.
"""

import sys
import subprocess
from pathlib import Path

def run_test(test_script: str, test_name: str) -> bool:
    """Run a test script and return success status."""
    print(f"\n{'=' * 80}")
    print(f"Running: {test_name}")
    print(f"{'=' * 80}")
    
    try:
        result = subprocess.run(
            ['python3', test_script],
            cwd=Path(__file__).parent,
            capture_output=False,
            text=True
        )
        
        success = result.returncode == 0
        
        if success:
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
        
        return success
        
    except Exception as e:
        print(f"❌ {test_name} ERROR: {e}")
        return False

def main():
    """Run all integration tests."""
    
    print("=" * 80)
    print("Template Naming Standardization - Integration Test Suite")
    print("=" * 80)
    
    tests = [
        ("test_integration.py", "Deployment Guide Generation"),
        ("test_stack_commands.py", "Stack Command Generation"),
        ("test_stackset_commands.py", "StackSet Command Generation"),
        ("test_target_detection.py", "Target Account Detection"),
        ("test_parameter_resolution.py", "Parameter Resolution")
    ]
    
    results = {}
    
    for test_script, test_name in tests:
        results[test_name] = run_test(test_script, test_name)
    
    # Print summary
    print("\n" + "=" * 80)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("=" * 80)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)
    
    if passed == total:
        print("\n🎉 All integration tests PASSED!")
        print("\nThe template naming standardization is working correctly:")
        print("  ✅ Deployment guide generated with renamed templates")
        print("  ✅ Stack commands use correct CloudFormation stack syntax")
        print("  ✅ StackSet commands use correct CloudFormation StackSet syntax")
        print("  ✅ Target accounts correctly detected from naming patterns")
        print("  ✅ Parameters correctly resolved and included in commands")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
