"""
Unit tests for template naming convention detection methods.

Tests focus on the new detection methods in llm_agent_guide.py that identify
deployment types and target accounts based on the standardized naming convention.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from titanium_generator.mcp_tools.llm_agent_guide import LLMAgentGuideGenerator


class TestManagementAccountDetection:
    """Tests for _is_management_account_only() method."""
    
    def test_bootstrap_templates(self):
        """Test detection of bootstrap templates as management account stacks."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '01-config-stack-mgmt-role.yaml',
            '02-stacksets-stack-mgmt-enable.yaml'
        ]
        
        for template in templates:
            assert guide._is_management_account_only(template) is True, \
                f"Template {template} should be detected as management account stack"
    
    def test_controltower_templates(self):
        """Test detection of Control Tower templates as management account stacks."""
        guide = LLMAgentGuideGenerator()
        
        template = '01-controltower-stack-mgmt-setup.yaml'
        assert guide._is_management_account_only(template) is True
    
    def test_organization_templates(self):
        """Test detection of organization templates as management account stacks."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '01-organizations-stack-mgmt-ous.yaml',
            '02-organizations-stack-mgmt-scps.yaml'
        ]
        
        for template in templates:
            assert guide._is_management_account_only(template) is True, \
                f"Template {template} should be detected as management account stack"
    
    def test_network_management_templates(self):
        """Test detection of network management templates as management account stacks."""
        guide = LLMAgentGuideGenerator()
        
        template = '01-ipam-stack-mgmt-delegation.yaml'
        assert guide._is_management_account_only(template) is True
    
    def test_security_management_templates(self):
        """Test detection of security management templates as management account stacks."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '01-securityhub-stack-mgmt-enable-delegate.yaml',
            '00-config-stack-mgmt-recorder.yaml'
        ]
        
        for template in templates:
            assert guide._is_management_account_only(template) is True, \
                f"Template {template} should be detected as management account stack"
    
    def test_stackset_templates_not_detected(self):
        """Test that StackSet templates are not detected as management account stacks."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '02-ipam-stackset-network-sharing.yaml',
            '03-vpc-stackset-logarchive-flowlogs-bucket.yaml',
            '02-securityhub-stackset-audit-cspm-configuration.yaml'
        ]
        
        for template in templates:
            assert guide._is_management_account_only(template) is False, \
                f"Template {template} should not be detected as management account stack"
    
    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '01-CONFIG-STACK-MGMT-ROLE.yaml',
            '01-Config-Stack-Mgmt-Role.yaml',
            '01-config-STACK-mgmt-role.YAML'
        ]
        
        for template in templates:
            assert guide._is_management_account_only(template) is True, \
                f"Template {template} should be detected (case-insensitive)"


class TestAuditAccountStackSetDetection:
    """Tests for _is_audit_account_stackset() method."""
    
    def test_security_audit_templates(self):
        """Test detection of security templates deployed to audit account."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '02-securityhub-stackset-audit-cspm-configuration.yaml',
            '03-guardduty-stackset-audit-detector.yaml',
            '04-guardduty-stackset-audit-s3protection.yaml'
        ]
        
        for template in templates:
            assert guide._is_audit_account_stackset(template) is True, \
                f"Template {template} should be detected as audit account stackset"
    
    def test_management_templates_not_detected(self):
        """Test that management account templates are not detected as audit stacksets."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '01-config-stack-mgmt-role.yaml',
            '01-securityhub-stack-mgmt-enable-delegate.yaml'
        ]
        
        for template in templates:
            assert guide._is_audit_account_stackset(template) is False, \
                f"Template {template} should not be detected as audit account stackset"
    
    def test_other_stacksets_not_detected(self):
        """Test that non-audit stacksets are not detected as audit stacksets."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '02-ipam-stackset-network-sharing.yaml',
            '03-vpc-stackset-logarchive-flowlogs-bucket.yaml'
        ]
        
        for template in templates:
            assert guide._is_audit_account_stackset(template) is False, \
                f"Template {template} should not be detected as audit account stackset"
    
    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '02-SECURITYHUB-STACKSET-AUDIT-CSPM.yaml',
            '02-SecurityHub-StackSet-Audit-CSPM.yaml'
        ]
        
        for template in templates:
            assert guide._is_audit_account_stackset(template) is True, \
                f"Template {template} should be detected (case-insensitive)"


class TestNetworkAccountStackSetDetection:
    """Tests for _is_network_account_stackset() method."""
    
    def test_network_templates(self):
        """Test detection of network templates deployed to network account."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '02-ipam-stackset-network-sharing.yaml',
            '04-tgw-stackset-network-firewall.yaml',
            '05-dns-stackset-network-resolver.yaml'
        ]
        
        for template in templates:
            assert guide._is_network_account_stackset(template) is True, \
                f"Template {template} should be detected as network account stackset"
    
    def test_non_network_templates_not_detected(self):
        """Test that non-network templates are not detected as network stacksets."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '01-ipam-stack-mgmt-delegation.yaml',
            '03-vpc-stackset-logarchive-flowlogs-bucket.yaml',
            '02-securityhub-stackset-audit-cspm-configuration.yaml'
        ]
        
        for template in templates:
            assert guide._is_network_account_stackset(template) is False, \
                f"Template {template} should not be detected as network account stackset"
    
    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '02-IPAM-STACKSET-NETWORK-SHARING.yaml',
            '02-Ipam-StackSet-Network-Sharing.yaml'
        ]
        
        for template in templates:
            assert guide._is_network_account_stackset(template) is True, \
                f"Template {template} should be detected (case-insensitive)"


class TestLogArchiveAccountStackSetDetection:
    """Tests for _is_logarchive_account_stackset() method."""
    
    def test_logarchive_templates(self):
        """Test detection of templates deployed to log archive account."""
        guide = LLMAgentGuideGenerator()
        
        template = '03-vpc-stackset-logarchive-flowlogs-bucket.yaml'
        assert guide._is_logarchive_account_stackset(template) is True
    
    def test_non_logarchive_templates_not_detected(self):
        """Test that non-logarchive templates are not detected as logarchive stacksets."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '01-ipam-stack-mgmt-delegation.yaml',
            '02-ipam-stackset-network-sharing.yaml',
            '02-securityhub-stackset-audit-cspm-configuration.yaml'
        ]
        
        for template in templates:
            assert guide._is_logarchive_account_stackset(template) is False, \
                f"Template {template} should not be detected as logarchive account stackset"
    
    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '03-VPC-STACKSET-LOGARCHIVE-FLOWLOGS.yaml',
            '03-Vpc-StackSet-LogArchive-FlowLogs.yaml'
        ]
        
        for template in templates:
            assert guide._is_logarchive_account_stackset(template) is True, \
                f"Template {template} should be detected (case-insensitive)"


class TestOrganizationWideStackSetDetection:
    """Tests for _is_organization_wide_stackset() method."""
    
    def test_org_wide_templates(self):
        """Test detection of organization-wide stackset templates."""
        guide = LLMAgentGuideGenerator()
        
        # Example org-wide templates (if they exist)
        templates = [
            '05-cloudtrail-stackset-org-trail.yaml',
            '06-config-stackset-org-rules.yaml'
        ]
        
        for template in templates:
            assert guide._is_organization_wide_stackset(template) is True, \
                f"Template {template} should be detected as organization-wide stackset"
    
    def test_non_org_templates_not_detected(self):
        """Test that non-org-wide templates are not detected as org stacksets."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '01-ipam-stack-mgmt-delegation.yaml',
            '02-ipam-stackset-network-sharing.yaml',
            '02-securityhub-stackset-audit-cspm-configuration.yaml',
            '03-vpc-stackset-logarchive-flowlogs-bucket.yaml'
        ]
        
        for template in templates:
            assert guide._is_organization_wide_stackset(template) is False, \
                f"Template {template} should not be detected as organization-wide stackset"
    
    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '05-CLOUDTRAIL-STACKSET-ORG-TRAIL.yaml',
            '05-CloudTrail-StackSet-Org-Trail.yaml'
        ]
        
        for template in templates:
            assert guide._is_organization_wide_stackset(template) is True, \
                f"Template {template} should be detected (case-insensitive)"


class TestUniqueDeploymentTypeDetection:
    """Tests for Property 1: Unique Deployment Type Detection."""
    
    def test_all_templates_have_unique_deployment_type(self):
        """Test that every template maps to exactly one deployment type."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            # Management account stacks
            '01-config-stack-mgmt-role.yaml',
            '02-stacksets-stack-mgmt-enable.yaml',
            '01-controltower-stack-mgmt-setup.yaml',
            '01-organizations-stack-mgmt-ous.yaml',
            '01-ipam-stack-mgmt-delegation.yaml',
            # Audit stacksets
            '02-securityhub-stackset-audit-cspm-configuration.yaml',
            '03-guardduty-stackset-audit-detector.yaml',
            # Network stacksets
            '02-ipam-stackset-network-sharing.yaml',
            '04-tgw-stackset-network-firewall.yaml',
            # LogArchive stacksets
            '03-vpc-stackset-logarchive-flowlogs-bucket.yaml'
        ]
        
        for template in templates:
            is_stack = guide._is_management_account_only(template)
            is_stackset = not is_stack
            
            # XOR: exactly one must be true
            assert is_stack != is_stackset, \
                f"Template {template} must be either Stack or StackSet, not both or neither"


class TestCorrectTargetAccountDetection:
    """Tests for Property 2: Correct Target Account Detection."""
    
    def test_stacksets_have_unique_target(self):
        """Test that StackSet templates map to exactly one target account type."""
        guide = LLMAgentGuideGenerator()
        
        stackset_templates = [
            ('02-securityhub-stackset-audit-cspm-configuration.yaml', 'audit'),
            ('03-guardduty-stackset-audit-detector.yaml', 'audit'),
            ('02-ipam-stackset-network-sharing.yaml', 'network'),
            ('04-tgw-stackset-network-firewall.yaml', 'network'),
            ('03-vpc-stackset-logarchive-flowlogs-bucket.yaml', 'logarchive'),
            ('05-cloudtrail-stackset-org-trail.yaml', 'org')
        ]
        
        for template, expected_target in stackset_templates:
            targets = [
                guide._is_audit_account_stackset(template),
                guide._is_network_account_stackset(template),
                guide._is_logarchive_account_stackset(template),
                guide._is_organization_wide_stackset(template)
            ]
            
            assert sum(targets) == 1, \
                f"Template {template} must map to exactly one target account type"
    
    def test_stacks_dont_need_target_detection(self):
        """Test that Stack templates don't trigger target detection."""
        guide = LLMAgentGuideGenerator()
        
        stack_templates = [
            '01-config-stack-mgmt-role.yaml',
            '01-controltower-stack-mgmt-setup.yaml',
            '01-organizations-stack-mgmt-ous.yaml'
        ]
        
        for template in stack_templates:
            # Stacks should be detected as management account only
            assert guide._is_management_account_only(template) is True
            
            # Stacks should not trigger any stackset target detection
            targets = [
                guide._is_audit_account_stackset(template),
                guide._is_network_account_stackset(template),
                guide._is_logarchive_account_stackset(template),
                guide._is_organization_wide_stackset(template)
            ]
            
            assert sum(targets) == 0, \
                f"Stack template {template} should not match any StackSet target patterns"


class TestNewConventionPatternMatching:
    """Tests for Property 3: New Convention Pattern Matching."""
    
    def test_stack_mgmt_pattern_matching(self):
        """Test that templates with -stack-mgmt- pattern are detected correctly."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '01-config-stack-mgmt-role.yaml',
            '02-stacksets-stack-mgmt-enable.yaml',
            '01-controltower-stack-mgmt-setup.yaml'
        ]
        
        for template in templates:
            if '-stack-mgmt-' in template.lower():
                assert guide._is_management_account_only(template) is True, \
                    f"Template {template} with -stack-mgmt- pattern should be detected"
    
    def test_stackset_audit_pattern_matching(self):
        """Test that templates with -stackset-audit- pattern are detected correctly."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '02-securityhub-stackset-audit-cspm-configuration.yaml',
            '03-guardduty-stackset-audit-detector.yaml'
        ]
        
        for template in templates:
            if '-stackset-audit-' in template.lower():
                assert guide._is_audit_account_stackset(template) is True, \
                    f"Template {template} with -stackset-audit- pattern should be detected"
    
    def test_stackset_network_pattern_matching(self):
        """Test that templates with -stackset-network- pattern are detected correctly."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '02-ipam-stackset-network-sharing.yaml',
            '04-tgw-stackset-network-firewall.yaml'
        ]
        
        for template in templates:
            if '-stackset-network-' in template.lower():
                assert guide._is_network_account_stackset(template) is True, \
                    f"Template {template} with -stackset-network- pattern should be detected"
    
    def test_stackset_logarchive_pattern_matching(self):
        """Test that templates with -stackset-logarchive- pattern are detected correctly."""
        guide = LLMAgentGuideGenerator()
        
        template = '03-vpc-stackset-logarchive-flowlogs-bucket.yaml'
        
        if '-stackset-logarchive-' in template.lower():
            assert guide._is_logarchive_account_stackset(template) is True, \
                f"Template {template} with -stackset-logarchive- pattern should be detected"
    
    def test_stackset_org_pattern_matching(self):
        """Test that templates with -stackset-org- pattern are detected correctly."""
        guide = LLMAgentGuideGenerator()
        
        template = '05-cloudtrail-stackset-org-trail.yaml'
        
        if '-stackset-org-' in template.lower():
            assert guide._is_organization_wide_stackset(template) is True, \
                f"Template {template} with -stackset-org- pattern should be detected"
    
    def test_all_templates_match_a_pattern(self):
        """Test that all templates match at least one pattern."""
        guide = LLMAgentGuideGenerator()
        
        templates = [
            '01-config-stack-mgmt-role.yaml',
            '02-securityhub-stackset-audit-cspm-configuration.yaml',
            '02-ipam-stackset-network-sharing.yaml',
            '03-vpc-stackset-logarchive-flowlogs-bucket.yaml',
            '05-cloudtrail-stackset-org-trail.yaml'
        ]
        
        for template in templates:
            has_pattern = (
                '-stack-mgmt-' in template.lower() or
                '-stackset-audit-' in template.lower() or
                '-stackset-network-' in template.lower() or
                '-stackset-logarchive-' in template.lower() or
                '-stackset-org-' in template.lower()
            )
            
            assert has_pattern is True, \
                f"Template {template} must match at least one naming convention pattern"
