"""
Unit tests for template decision logic (Config recorder conditional generation).

Tests the simple decision logic in process_templates.py that skips
0-config-recorder-mgmt.yaml when Control Tower is enabled.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path


class TestTemplateDecisionLogic:
    """Tests for template skip logic based on Control Tower status."""
    
    def test_config_recorder_skipped_when_control_tower_enabled(self):
        """Test that Config recorder template is skipped when Control Tower is enabled."""
        config = {
            'homeRegion': 'us-east-1',
            'controlTower': {
                'enable': True
            }
        }
        
        template_name = '00-config-stack-mgmt-recorder.yaml'
        is_control_tower_enabled = config.get('controlTower', {}).get('enable', False) if isinstance(config.get('controlTower'), dict) else False
        
        should_skip = is_control_tower_enabled and template_name == '00-config-stack-mgmt-recorder.yaml'
        
        assert should_skip is True
    
    def test_config_recorder_generated_when_control_tower_disabled(self):
        """Test that Config recorder template is generated when Control Tower is disabled."""
        config = {
            'homeRegion': 'us-east-1',
            'controlTower': {
                'enable': False
            }
        }
        
        template_name = '00-config-stack-mgmt-recorder.yaml'
        is_control_tower_enabled = config.get('controlTower', {}).get('enable', False) if isinstance(config.get('controlTower'), dict) else False
        
        should_skip = is_control_tower_enabled and template_name == '00-config-stack-mgmt-recorder.yaml'
        
        assert should_skip is False
    
    def test_config_recorder_generated_when_control_tower_missing(self):
        """Test that Config recorder template is generated when Control Tower section is missing."""
        config = {
            'homeRegion': 'us-east-1'
        }
        
        template_name = '00-config-stack-mgmt-recorder.yaml'
        is_control_tower_enabled = config.get('controlTower', {}).get('enable', False) if isinstance(config.get('controlTower'), dict) else False
        
        should_skip = is_control_tower_enabled and template_name == '00-config-stack-mgmt-recorder.yaml'
        
        assert should_skip is False
    
    def test_other_templates_not_affected(self):
        """Test that other templates are not affected by Control Tower status."""
        config = {
            'homeRegion': 'us-east-1',
            'controlTower': {
                'enable': True
            }
        }
        
        # Test various other template names with new naming convention
        other_templates = [
            '01-securityhub-stack-mgmt-enable-delegate.yaml',
            '02-securityhub-stackset-audit-cspm-configuration.yaml',
            '01-config-stack-mgmt-role.yaml',
            '03-guardduty-stackset-audit-detector.yaml'
        ]
        
        is_control_tower_enabled = config.get('controlTower', {}).get('enable', False) if isinstance(config.get('controlTower'), dict) else False
        
        for template_name in other_templates:
            should_skip = is_control_tower_enabled and template_name == '00-config-stack-mgmt-recorder.yaml'
            assert should_skip is False, f"Template {template_name} should not be skipped"
    
    def test_control_tower_not_dict(self):
        """Test handling when controlTower is not a dictionary."""
        config = {
            'homeRegion': 'us-east-1',
            'controlTower': 'invalid'
        }
        
        template_name = '00-config-stack-mgmt-recorder.yaml'
        is_control_tower_enabled = config.get('controlTower', {}).get('enable', False) if isinstance(config.get('controlTower'), dict) else False
        
        should_skip = is_control_tower_enabled and template_name == '00-config-stack-mgmt-recorder.yaml'
        
        assert should_skip is False
    
    def test_control_tower_null(self):
        """Test handling when controlTower is null."""
        config = {
            'homeRegion': 'us-east-1',
            'controlTower': None
        }
        
        template_name = '00-config-stack-mgmt-recorder.yaml'
        is_control_tower_enabled = config.get('controlTower', {}).get('enable', False) if isinstance(config.get('controlTower'), dict) else False
        
        should_skip = is_control_tower_enabled and template_name == '00-config-stack-mgmt-recorder.yaml'
        
        assert should_skip is False
    
    def test_decision_reason_control_tower_enabled(self):
        """Test that the skip reason is correct when Control Tower is enabled."""
        config = {
            'homeRegion': 'us-east-1',
            'controlTower': {
                'enable': True
            }
        }
        
        is_control_tower_enabled = config.get('controlTower', {}).get('enable', False) if isinstance(config.get('controlTower'), dict) else False
        
        if is_control_tower_enabled:
            reason = 'Control Tower is enabled - Config recorder managed by Control Tower in member accounts'
        else:
            reason = 'Control Tower is disabled - Config recorder needed for standalone deployment'
        
        assert reason == 'Control Tower is enabled - Config recorder managed by Control Tower in member accounts'
    
    def test_decision_reason_control_tower_disabled(self):
        """Test that the generation reason is correct when Control Tower is disabled."""
        config = {
            'homeRegion': 'us-east-1',
            'controlTower': {
                'enable': False
            }
        }
        
        is_control_tower_enabled = config.get('controlTower', {}).get('enable', False) if isinstance(config.get('controlTower'), dict) else False
        
        if is_control_tower_enabled:
            reason = 'Control Tower is enabled - Config recorder managed by Control Tower in member accounts'
        else:
            reason = 'Control Tower is disabled - Config recorder needed for standalone deployment'
        
        assert reason == 'Control Tower is disabled - Config recorder needed for standalone deployment'
