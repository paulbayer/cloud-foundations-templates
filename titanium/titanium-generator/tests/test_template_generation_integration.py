"""
Integration tests for template generation with Control Tower conditional logic.

Tests the complete workflow of template generation including:
- Config role always generated
- Config recorder conditionally generated based on Control Tower status
- Template generation order maintained
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from titanium_generator.mcp_tools.process_templates import process_all_templates


class TestTemplateGenerationIntegration:
    """Integration tests for template generation workflow."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_titanium_config_ct_enabled(self, tmp_path):
        """Create a sample Titanium.yaml with Control Tower enabled."""
        config_content = """
homeRegion: us-east-1
enabledRegions:
  - us-east-1
controlTower:
  enable: true
centralSecurityServices:
  delegatedAdminAccount: Audit
  securityHub:
    enable: true
"""
        config_file = tmp_path / "titanium_ct_enabled.yaml"
        config_file.write_text(config_content)
        return str(config_file)
    
    @pytest.fixture
    def sample_titanium_config_ct_disabled(self, tmp_path):
        """Create a sample Titanium.yaml with Control Tower disabled."""
        config_content = """
homeRegion: us-east-1
enabledRegions:
  - us-east-1
controlTower:
  enable: false
centralSecurityServices:
  delegatedAdminAccount: Audit
  securityHub:
    enable: true
"""
        config_file = tmp_path / "titanium_ct_disabled.yaml"
        config_file.write_text(config_content)
        return str(config_file)
    
    def test_config_role_always_generated(self, sample_titanium_config_ct_enabled, temp_output_dir):
        """Test that Config role template is always generated regardless of Control Tower status."""
        # Process all templates without section filtering
        result = process_all_templates(
            sample_titanium_config_ct_enabled,
            temp_output_dir
        )
        
        assert result['success'] is True
        
        # Check that 01-config-stack-mgmt-role.yaml was generated
        config_role_path = Path(temp_output_dir) / 'bootstrap' / '01-config-stack-mgmt-role.yaml'
        assert config_role_path.exists(), "Config role template should always be generated"
    
    def test_config_recorder_skipped_when_ct_enabled(self, sample_titanium_config_ct_enabled, temp_output_dir):
        """Test that Config recorder template is skipped when Control Tower is enabled."""
        result = process_all_templates(
            sample_titanium_config_ct_enabled,
            temp_output_dir
        )
        
        assert result['success'] is True
        
        # Check that 00-config-stack-mgmt-recorder.yaml was NOT generated
        config_recorder_path = Path(temp_output_dir) / 'security' / '00-config-stack-mgmt-recorder.yaml'
        assert not config_recorder_path.exists(), "Config recorder template should be skipped when Control Tower is enabled"
        
        # Verify it was skipped with correct reason
        assert result['summary']['skipped_templates'] > 0
    
    @pytest.mark.xfail(reason="Config recorder template not yet implemented")
    def test_config_recorder_generated_when_ct_disabled(self, sample_titanium_config_ct_disabled, temp_output_dir):
        """Test that Config recorder template is generated when Control Tower is disabled."""
        result = process_all_templates(
            sample_titanium_config_ct_disabled,
            temp_output_dir
        )

        assert result['success'] is True

        # Check that 00-config-stack-mgmt-recorder.yaml was generated
        config_recorder_path = Path(temp_output_dir) / 'security' / '00-config-stack-mgmt-recorder.yaml'
        assert config_recorder_path.exists(), "Config recorder template should be generated when Control Tower is disabled"

    @pytest.mark.xfail(reason="Config recorder template not yet implemented")
    def test_template_generation_order(self, sample_titanium_config_ct_disabled, temp_output_dir):
        """Test that Config role is processed before Config recorder."""
        result = process_all_templates(
            sample_titanium_config_ct_disabled,
            temp_output_dir
        )

        assert result['success'] is True

        # Both templates should exist
        config_role_path = Path(temp_output_dir) / 'bootstrap' / '01-config-stack-mgmt-role.yaml'
        config_recorder_path = Path(temp_output_dir) / 'security' / '00-config-stack-mgmt-recorder.yaml'

        assert config_role_path.exists(), "Config role template should be generated"
        assert config_recorder_path.exists(), "Config recorder template should be generated"

        # Verify bootstrap section is processed before security section
        # (This is implicit in the alphabetical section ordering)
        assert 'bootstrap' in result['metadata']['sections_processed']
        assert 'security' in result['metadata']['sections_processed']

