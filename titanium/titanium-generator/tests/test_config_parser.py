"""
Unit tests for TitaniumConfigParser enhancements.

Tests focus on Control Tower detection functionality.
"""

import pytest
import yaml
from titanium_generator.config_parser import TitaniumConfigParser


class TestControlTowerDetection:
    """Tests for Control Tower detection functionality."""
    
    def test_control_tower_enabled_true(self):
        """Test detection when controlTower.enable is true."""
        parser = TitaniumConfigParser()
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1'],
            'controlTower': {
                'enable': True
            }
        }
        
        assert parser.get_control_tower_enabled(config) is True
    
    def test_control_tower_enabled_false(self):
        """Test detection when controlTower.enable is false."""
        parser = TitaniumConfigParser()
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1'],
            'controlTower': {
                'enable': False
            }
        }
        
        assert parser.get_control_tower_enabled(config) is False
    
    def test_control_tower_section_missing(self):
        """Test default to False when controlTower section is absent."""
        parser = TitaniumConfigParser()
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1']
        }
        
        assert parser.get_control_tower_enabled(config) is False
    
    def test_control_tower_enable_field_missing(self):
        """Test default to False when enable field is absent."""
        parser = TitaniumConfigParser()
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1'],
            'controlTower': {
                'landingZone': {
                    'version': '4.0'
                }
            }
        }
        
        assert parser.get_control_tower_enabled(config) is False
    
    def test_control_tower_not_dict(self):
        """Test handling when controlTower is not a dictionary."""
        parser = TitaniumConfigParser()
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1'],
            'controlTower': 'invalid'
        }
        
        assert parser.get_control_tower_enabled(config) is False
    
    def test_control_tower_enable_non_boolean(self):
        """Test handling when enable is not a boolean."""
        parser = TitaniumConfigParser()
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1'],
            'controlTower': {
                'enable': 'yes'
            }
        }
        
        # Should return the value as-is (truthy string)
        assert parser.get_control_tower_enabled(config) == 'yes'
    
    def test_control_tower_null_value(self):
        """Test with null value for controlTower."""
        parser = TitaniumConfigParser()
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1'],
            'controlTower': None
        }
        
        assert parser.get_control_tower_enabled(config) is False
    
    def test_control_tower_empty_dict(self):
        """Test with empty controlTower dictionary."""
        parser = TitaniumConfigParser()
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1'],
            'controlTower': {}
        }
        
        assert parser.get_control_tower_enabled(config) is False


class TestConfigurationParsingEdgeCases:
    """Tests for edge cases in configuration parsing."""
    
    def test_parse_full_yaml_with_control_tower_enabled(self):
        """Test parsing a complete YAML configuration with Control Tower enabled."""
        parser = TitaniumConfigParser()
        yaml_content = """
homeRegion: us-east-1
enabledRegions:
  - us-east-1
  - us-west-2
controlTower:
  enable: true
  landingZone:
    version: '4.0'
    logging:
      organizationTrail: true
"""
        
        config = parser.parse(yaml_content)
        assert parser.get_control_tower_enabled(config) is True
        assert config['controlTower']['landingZone']['version'] == '4.0'
    
    def test_parse_full_yaml_with_control_tower_disabled(self):
        """Test parsing a complete YAML configuration with Control Tower disabled."""
        parser = TitaniumConfigParser()
        yaml_content = """
homeRegion: us-east-1
enabledRegions:
  - us-east-1
controlTower:
  enable: false
"""
        
        config = parser.parse(yaml_content)
        assert parser.get_control_tower_enabled(config) is False
    
    def test_parse_yaml_without_control_tower(self):
        """Test parsing YAML without Control Tower section."""
        parser = TitaniumConfigParser()
        yaml_content = """
homeRegion: us-east-1
enabledRegions:
  - us-east-1
centralSecurityServices:
  delegatedAdminAccount: Audit
"""
        
        config = parser.parse(yaml_content)
        assert parser.get_control_tower_enabled(config) is False
    
    def test_parse_minimal_valid_config(self):
        """Test parsing minimal valid configuration."""
        parser = TitaniumConfigParser()
        yaml_content = """
homeRegion: us-east-1
enabledRegions:
  - us-east-1
"""
        
        config = parser.parse(yaml_content)
        assert parser.get_control_tower_enabled(config) is False
    
    def test_nested_structure_integrity(self):
        """Test that nested structures are preserved correctly."""
        parser = TitaniumConfigParser()
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1'],
            'controlTower': {
                'enable': True,
                'landingZone': {
                    'version': '4.0',
                    'logging': {
                        'organizationTrail': True
                    }
                }
            }
        }
        
        assert parser.get_control_tower_enabled(config) is True
        assert config['controlTower']['landingZone']['version'] == '4.0'
        assert config['controlTower']['landingZone']['logging']['organizationTrail'] is True
    
    def test_parse_file_integration(self, tmp_path):
        """Test parsing from file with Control Tower configuration."""
        yaml_content = """
homeRegion: us-east-1
enabledRegions:
  - us-east-1
controlTower:
  enable: true
"""
        
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(yaml_content)
        
        parser = TitaniumConfigParser()
        config = parser.parse_file(str(config_file))
        
        assert parser.get_control_tower_enabled(config) is True
