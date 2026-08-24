#!/usr/bin/env python3
"""
Test parameter resolution for renamed templates.
Verifies that templates correctly identify and prompt for parameters.
"""

import sys
import re
from pathlib import Path

def test_parameter_resolution():
    """Test that templates correctly handle parameter resolution."""
    
    guide_path = Path(__file__).parent / "test_output" / "LLM_AGENT_DEPLOYMENT_GUIDE.md"
    
    if not guide_path.exists():
        print(f"Error: Guide not found at {guide_path}")
        return False
    
    print("=" * 80)
    print("Test: Parameter Resolution")
    print("=" * 80)
    print()
    
    with open(guide_path, 'r') as f:
        content = f.read()
    
    # Test cases: templates that should have parameters
    test_cases = {
        "01-controltower-stack-mgmt-setup.yaml": {
            "should_have_params": True,
            "expected_params": ["uLoggingAccountEmail", "uLoggingAccountName", 
                              "uSecurityAccountEmail", "uSecurityAccountName"],
            "description": "Control Tower setup requires account parameters"
        },
        "01-config-stack-mgmt-role.yaml": {
            "should_have_params": False,
            "expected_params": [],
            "description": "Config role should not require user parameters"
        },
        "02-stacksets-stack-mgmt-enable.yaml": {
            "should_have_params": False,
            "expected_params": [],
            "description": "StackSets enable should not require user parameters"
        }
    }
    
    all_passed = True
    
    for template, test_info in test_cases.items():
        print(f"Testing: {template}")
        print(f"  Should have params: {test_info['should_have_params']}")
        print(f"  Description: {test_info['description']}")
        print("-" * 80)
        
        # Check if template is mentioned in the guide
        if template not in content:
            print(f"  ⚠️  SKIP: Template not found in guide")
            print()
            continue
        
        # Look for parameter resolution step for this template
        param_pattern = rf"Resolve Parameters for {re.escape(template)}.*?(?=####|\Z)"
        param_match = re.search(param_pattern, content, re.DOTALL)
        
        has_param_section = param_match is not None
        
        if test_info['should_have_params']:
            # Should have parameter resolution section
            if not has_param_section:
                print(f"  ❌ FAIL: Expected parameter resolution section but not found")
                all_passed = False
                continue
            
            param_section = param_match.group(0)
            
            # Check for expected parameters
            missing_params = []
            for expected_param in test_info['expected_params']:
                if expected_param not in param_section:
                    missing_params.append(expected_param)
            
            if missing_params:
                print(f"  ❌ FAIL: Missing expected parameters: {missing_params}")
                all_passed = False
                continue
            
            # Verify parameter prompts exist
            if "parameter(s) that need user input" not in param_section:
                print(f"  ❌ FAIL: Missing parameter prompt text")
                all_passed = False
                continue
            
            print(f"  ✅ PASS: Correct parameter resolution")
            print(f"     Found parameters: {test_info['expected_params']}")
            
        else:
            # Should NOT have parameter resolution section
            if has_param_section:
                print(f"  ❌ FAIL: Unexpected parameter resolution section found")
                all_passed = False
                continue
            
            print(f"  ✅ PASS: No parameter resolution (as expected)")
        
        # Now check the deployment command
        deploy_pattern = rf"Deploy {re.escape(template)}.*?(?=####|\Z)"
        deploy_match = re.search(deploy_pattern, content, re.DOTALL)
        
        if not deploy_match:
            print(f"  ❌ FAIL: Deployment section not found")
            all_passed = False
            continue
        
        deploy_section = deploy_match.group(0)
        
        # Extract the create command
        if "create-stack " in deploy_section:
            cmd_pattern = r'aws cloudformation create-stack[^\n]+'
        else:
            cmd_pattern = r'aws cloudformation create-stack-set[^\n]+'
        
        cmd_match = re.search(cmd_pattern, deploy_section)
        
        if not cmd_match:
            print(f"  ❌ FAIL: Could not find deployment command")
            all_passed = False
            continue
        
        command = cmd_match.group(0)
        
        # Check if command has parameters when expected
        has_params_in_cmd = "--parameters" in command
        
        if test_info['should_have_params']:
            if not has_params_in_cmd:
                print(f"  ❌ FAIL: Command missing --parameters flag")
                all_passed = False
                continue
            
            # Verify parameter placeholders
            for expected_param in test_info['expected_params']:
                if f"<{expected_param}>" not in command:
                    print(f"  ❌ FAIL: Command missing placeholder for {expected_param}")
                    all_passed = False
                    continue
            
            print(f"  ✅ PASS: Command includes parameter placeholders")
        else:
            if has_params_in_cmd:
                print(f"  ⚠️  WARNING: Command has --parameters but none expected")
            else:
                print(f"  ✅ PASS: Command has no parameters (as expected)")
        
        print()
    
    print("=" * 80)
    if all_passed:
        print("✅ All parameter resolution tests PASSED")
    else:
        print("❌ Some parameter resolution tests FAILED")
    print("=" * 80)
    
    return all_passed

if __name__ == '__main__':
    success = test_parameter_resolution()
    sys.exit(0 if success else 1)
