#!/usr/bin/env python3
"""
Test target account detection for renamed templates.
Verifies that StackSet templates correctly identify their target accounts.
"""

import sys
import re
from pathlib import Path

def test_target_detection():
    """Test that StackSet templates correctly detect target accounts."""
    
    guide_path = Path(__file__).parent / "test_output" / "LLM_AGENT_DEPLOYMENT_GUIDE.md"
    
    if not guide_path.exists():
        print(f"Error: Guide not found at {guide_path}")
        return False
    
    print("=" * 80)
    print("Test: Target Account Detection")
    print("=" * 80)
    print()
    
    with open(guide_path, 'r') as f:
        content = f.read()
    
    # Expected StackSet templates with their target accounts
    test_cases = {
        "02-ipam-stackset-network-sharing.yaml": {
            "pattern": "stackset-network",
            "expected_account": "NETWORK_ACCOUNT_ID",
            "description": "Network account for IPAM sharing"
        },
        "03-vpc-stackset-logarchive-flowlogs-bucket.yaml": {
            "pattern": "stackset-logarchive",
            "expected_account": "LOGARCHIVE_ACCOUNT_ID",
            "description": "Log Archive account for VPC Flow Logs bucket"
        },
        "04-tgw-stackset-network-firewall.yaml": {
            "pattern": "stackset-network",
            "expected_account": "NETWORK_ACCOUNT_ID",
            "description": "Network account for Transit Gateway"
        },
        "05-dns-stackset-network-resolver.yaml": {
            "pattern": "stackset-network",
            "expected_account": "NETWORK_ACCOUNT_ID",
            "description": "Network account for DNS resolver"
        }
    }
    
    all_passed = True
    
    for template, test_info in test_cases.items():
        print(f"Testing: {template}")
        print(f"  Pattern: {test_info['pattern']}")
        print(f"  Expected target: {test_info['expected_account']}")
        print(f"  Description: {test_info['description']}")
        print("-" * 80)
        
        # Check if template is mentioned in the guide
        if template not in content:
            print(f"  ⚠️  SKIP: Template not found in guide")
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
        
        # Check for parameter collection that includes the expected account ID
        expected_account = test_info['expected_account']
        
        # Look for the account ID in parameter collection or deployment targets
        if expected_account not in section:
            print(f"  ❌ FAIL: Expected account ID '{expected_account}' not found in section")
            all_passed = False
            continue
        
        # Verify the create-stack-instances command uses the correct account
        instances_pattern = r'aws cloudformation create-stack-instances[^\n]+'
        instances_match = re.search(instances_pattern, section)
        
        if not instances_match:
            print(f"  ❌ FAIL: create-stack-instances command not found")
            all_passed = False
            continue
        
        instances_cmd = instances_match.group(0)
        
        # Check if the command references the expected account
        if f"<{expected_account}>" not in instances_cmd:
            print(f"  ❌ FAIL: Command does not reference <{expected_account}>")
            print(f"     Command: {instances_cmd[:100]}...")
            all_passed = False
            continue
        
        # Verify deployment-targets includes the account
        if "--deployment-targets" not in instances_cmd:
            print(f"  ❌ FAIL: Missing --deployment-targets in command")
            all_passed = False
            continue
        
        # Check for Accounts parameter in deployment-targets
        if "Accounts=<" not in instances_cmd:
            print(f"  ❌ FAIL: Missing Accounts parameter in deployment-targets")
            all_passed = False
            continue
        
        print(f"  ✅ PASS: Correct target account detection")
        print(f"     Command includes: Accounts=<{expected_account}>")
        print()
    
    print("=" * 80)
    if all_passed:
        print("✅ All target account detection tests PASSED")
    else:
        print("❌ Some target account detection tests FAILED")
    print("=" * 80)
    
    return all_passed

if __name__ == '__main__':
    success = test_target_detection()
    sys.exit(0 if success else 1)
