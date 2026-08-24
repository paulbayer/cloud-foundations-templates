#!/usr/bin/env python3
"""
Test StackSet command generation for renamed templates.
Verifies that templates with -stackset- pattern generate correct StackSet commands.
"""

import sys
import re
from pathlib import Path

def test_stackset_commands():
    """Test that StackSet templates generate correct CloudFormation StackSet commands."""
    
    guide_path = Path(__file__).parent / "test_output" / "LLM_AGENT_DEPLOYMENT_GUIDE.md"
    
    if not guide_path.exists():
        print(f"Error: Guide not found at {guide_path}")
        return False
    
    print("=" * 80)
    print("Test: StackSet Command Generation")
    print("=" * 80)
    print()
    
    with open(guide_path, 'r') as f:
        content = f.read()
    
    # Expected StackSet templates with their target patterns
    stackset_templates = {
        "02-ipam-stackset-network-sharing.yaml": "stackset-network",
        "03-vpc-stackset-logarchive-flowlogs-bucket.yaml": "stackset-logarchive",
        "04-tgw-stackset-network-firewall.yaml": "stackset-network",
        "05-dns-stackset-network-resolver.yaml": "stackset-network",
        "01-guardduty-stackset-audit-detector.yaml": "stackset-audit",
        "02-securityhub-stackset-audit-enabler.yaml": "stackset-audit"
    }
    
    all_passed = True
    
    for template, expected_pattern in stackset_templates.items():
        print(f"Testing: {template}")
        print(f"  Expected pattern: {expected_pattern}")
        print("-" * 80)
        
        # Check if template is mentioned in the guide
        if template not in content:
            print(f"  ⚠️  SKIP: Template not found in guide (may not be generated)")
            print()
            continue
        
        # Extract the section for this template
        pattern = rf"Deploy {re.escape(template)}.*?(?=####|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            print(f"  ❌ FAIL: Deployment section not found")
            all_passed = False
            continue
        
        section = match.group(0)
        
        # Verify it uses create-stack-set (not create-stack)
        if "create-stack " in section and "create-stack-set" not in section:
            print(f"  ❌ FAIL: Uses create-stack instead of create-stack-set")
            all_passed = False
            continue
        
        if "create-stack-set" not in section:
            print(f"  ❌ FAIL: Does not use create-stack-set command")
            all_passed = False
            continue
        
        # Verify it has stack-set-name parameter
        if "--stack-set-name" not in section:
            print(f"  ❌ FAIL: Missing --stack-set-name parameter")
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
        
        # Verify it has permission-model
        if "--permission-model SERVICE_MANAGED" not in section:
            print(f"  ❌ FAIL: Missing SERVICE_MANAGED permission model")
            all_passed = False
            continue
        
        # Verify it has auto-deployment
        if "--auto-deployment" not in section:
            print(f"  ❌ FAIL: Missing --auto-deployment parameter")
            all_passed = False
            continue
        
        # Verify it has create-stack-instances command
        if "create-stack-instances" not in section:
            print(f"  ❌ FAIL: Missing create-stack-instances command")
            all_passed = False
            continue
        
        # Verify it has deployment-targets
        if "--deployment-targets" not in section:
            print(f"  ❌ FAIL: Missing --deployment-targets parameter")
            all_passed = False
            continue
        
        # Extract the actual commands
        create_cmd_match = re.search(r'aws cloudformation create-stack-set[^\n]+', section)
        instances_cmd_match = re.search(r'aws cloudformation create-stack-instances[^\n]+', section)
        
        if create_cmd_match and instances_cmd_match:
            create_cmd = create_cmd_match.group(0)
            instances_cmd = instances_cmd_match.group(0)
            print(f"  ✅ PASS: Correct StackSet commands found")
            print(f"     Create: {create_cmd[:80]}...")
            print(f"     Instances: {instances_cmd[:80]}...")
        else:
            print(f"  ❌ FAIL: Could not extract commands")
            all_passed = False
        
        print()
    
    print("=" * 80)
    if all_passed:
        print("✅ All StackSet command tests PASSED")
    else:
        print("❌ Some StackSet command tests FAILED")
    print("=" * 80)
    
    return all_passed

if __name__ == '__main__':
    success = test_stackset_commands()
    sys.exit(0 if success else 1)
