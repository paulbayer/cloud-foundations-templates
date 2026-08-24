#!/usr/bin/env python3
"""
Test Stack command generation for renamed templates.
Verifies that templates with -stack-mgmt- pattern generate correct Stack commands.
"""

import sys
import re
from pathlib import Path

def test_stack_commands():
    """Test that Stack templates generate correct CloudFormation stack commands."""
    
    guide_path = Path(__file__).parent / "test_output" / "LLM_AGENT_DEPLOYMENT_GUIDE.md"
    
    if not guide_path.exists():
        print(f"Error: Guide not found at {guide_path}")
        return False
    
    print("=" * 80)
    print("Test: Stack Command Generation")
    print("=" * 80)
    print()
    
    with open(guide_path, 'r') as f:
        content = f.read()
    
    # Expected Stack templates (with -stack-mgmt- pattern)
    stack_templates = [
        "01-config-stack-mgmt-role.yaml",
        "02-stacksets-stack-mgmt-enable.yaml",
        "01-controltower-stack-mgmt-setup.yaml",
        "01-organizations-stack-mgmt-ous.yaml",
        "02-organizations-stack-mgmt-scps.yaml",
        "01-ipam-stack-mgmt-delegation.yaml"
    ]
    
    all_passed = True
    
    for template in stack_templates:
        print(f"Testing: {template}")
        print("-" * 80)
        
        # Check if template is mentioned in the guide
        if template not in content:
            print(f"  ❌ FAIL: Template not found in guide")
            all_passed = False
            continue
        
        # Extract the section for this template
        # Look for the deployment step
        pattern = rf"Deploy {re.escape(template)}.*?(?=####|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            print(f"  ❌ FAIL: Deployment section not found")
            all_passed = False
            continue
        
        section = match.group(0)
        
        # Verify it uses create-stack (not create-stack-set)
        if "create-stack-set" in section:
            print(f"  ❌ FAIL: Uses create-stack-set instead of create-stack")
            all_passed = False
            continue
        
        if "create-stack " not in section:
            print(f"  ❌ FAIL: Does not use create-stack command")
            all_passed = False
            continue
        
        # Verify it has stack-name parameter
        if "--stack-name" not in section:
            print(f"  ❌ FAIL: Missing --stack-name parameter")
            all_passed = False
            continue
        
        # Verify it has template-body parameter
        if "--template-body" not in section:
            print(f"  ❌ FAIL: Missing --template-body parameter")
            all_passed = False
            continue
        
        # Verify it has capabilities
        if "--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM" not in section:
            print(f"  ❌ FAIL: Missing IAM capabilities")
            all_passed = False
            continue
        
        # Verify it has region parameter
        if "--region" not in section:
            print(f"  ❌ FAIL: Missing --region parameter")
            all_passed = False
            continue
        
        # Verify it has wait command
        if "wait stack-create-complete" not in section:
            print(f"  ❌ FAIL: Missing wait stack-create-complete command")
            all_passed = False
            continue
        
        # Extract the actual command
        cmd_match = re.search(r'aws cloudformation create-stack[^\n]+', section)
        if cmd_match:
            command = cmd_match.group(0)
            print(f"  ✅ PASS: Correct Stack command found")
            print(f"     Command: {command[:100]}...")
        else:
            print(f"  ❌ FAIL: Could not extract command")
            all_passed = False
        
        print()
    
    print("=" * 80)
    if all_passed:
        print("✅ All Stack command tests PASSED")
    else:
        print("❌ Some Stack command tests FAILED")
    print("=" * 80)
    
    return all_passed

if __name__ == '__main__':
    success = test_stack_commands()
    sys.exit(0 if success else 1)
