"""
Unit tests for Control Tower detection at processor level.

Tests focus on the is_control_tower_enabled() method in SimpleProcessor.
"""

import pytest
import logging
from titanium_generator.base_processor import SimpleProcessor


class TestProcessorControlTowerDetection:
    """Tests for Control Tower detection in SimpleProcessor."""
    
    def test_control_tower_enabled_true(self):
        """Test detection when controlTower.enable is true."""
        processor = SimpleProcessor(section_name='test')
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1'],
            'controlTower': {
                'enable': True
            }
        }
        
        processor.set_full_config(config)
        assert processor.is_control_tower_enabled() is True
    
    def test_control_tower_enabled_false(self):
        """Test detection when controlTower.enable is false."""
        processor = SimpleProcessor(section_name='test')
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1'],
            'controlTower': {
                'enable': False
            }
        }
        
        processor.set_full_config(config)
        assert processor.is_control_tower_enabled() is False
    
    def test_control_tower_section_missing(self):
        """Test default to False when controlTower section is absent."""
        processor = SimpleProcessor(section_name='test')
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1']
        }
        
        processor.set_full_config(config)
        assert processor.is_control_tower_enabled() is False
    
    def test_control_tower_enable_field_missing(self):
        """Test default to False when enable field is absent."""
        processor = SimpleProcessor(section_name='test')
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1'],
            'controlTower': {
                'landingZone': {
                    'version': '4.0'
                }
            }
        }
        
        processor.set_full_config(config)
        assert processor.is_control_tower_enabled() is False
    
    def test_control_tower_not_dict(self):
        """Test handling when controlTower is not a dictionary."""
        processor = SimpleProcessor(section_name='test')
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1'],
            'controlTower': 'invalid'
        }
        
        processor.set_full_config(config)
        assert processor.is_control_tower_enabled() is False
    
    def test_control_tower_null_value(self):
        """Test with null value for controlTower."""
        processor = SimpleProcessor(section_name='test')
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1'],
            'controlTower': None
        }
        
        processor.set_full_config(config)
        assert processor.is_control_tower_enabled() is False
    
    def test_control_tower_empty_dict(self):
        """Test with empty controlTower dictionary."""
        processor = SimpleProcessor(section_name='test')
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1'],
            'controlTower': {}
        }
        
        processor.set_full_config(config)
        assert processor.is_control_tower_enabled() is False
    
    def test_error_when_config_not_set(self):
        """Test that RuntimeError is raised when full_config is not set."""
        processor = SimpleProcessor(section_name='test')
        
        with pytest.raises(RuntimeError, match="Full configuration has not been set"):
            processor.is_control_tower_enabled()
    
    def test_flag_consistency(self):
        """Test that flag value remains consistent across multiple calls."""
        processor = SimpleProcessor(section_name='test')
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1'],
            'controlTower': {
                'enable': True
            }
        }
        
        processor.set_full_config(config)
        
        # Call multiple times and verify consistency
        result1 = processor.is_control_tower_enabled()
        result2 = processor.is_control_tower_enabled()
        result3 = processor.is_control_tower_enabled()
        
        assert result1 is True
        assert result2 is True
        assert result3 is True
    
    def test_detection_logging(self, caplog):
        """Test that detection status is logged with timestamp."""
        processor = SimpleProcessor(section_name='security')
        config = {
            'homeRegion': 'us-east-1',
            'enabledRegions': ['us-east-1'],
            'controlTower': {
                'enable': True
            }
        }
        
        processor.set_full_config(config)
        
        with caplog.at_level(logging.INFO):
            processor.is_control_tower_enabled()
        
        # Verify log contains expected information
        assert len(caplog.records) > 0
        log_message = caplog.records[0].message
        assert 'Control Tower Detection' in log_message
        assert 'security' in log_message
        assert 'enabled=True' in log_message
        assert 'timestamp=' in log_message
