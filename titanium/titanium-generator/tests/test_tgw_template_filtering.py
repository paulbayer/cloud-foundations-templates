"""
Unit tests for TGW template filtering logic.

Tests the template filtering logic in process_templates.py that selects
the correct TGW template (04a or 04b) based on Network Firewall configuration.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from titanium_generator.processors.network_processor import NetworkProcessor


class TestTGWTemplateFiltering:
    """Tests for TGW template filtering based on Network Firewall configuration."""
    
    def test_template_04a_selected_when_firewall_disabled(self):
        """Test that Template 04A is selected when Network Firewall is disabled."""
        processor = NetworkProcessor()
        
        section_config = {
            'tgwArchitecture': {
                'vpcs': {
                    'inspectionVpc': {
                        'enabled': True,
                        'networkFirewall': False  # Firewall disabled
                    }
                },
                'transitGateway': {
                    'name': 'test-tgw',
                    'asn': 65000
                }
            }
        }
        
        template_name = processor.get_tgw_template_name(section_config)
        assert template_name == '04a-tgw-stackset-network-egress-vpc.yaml'
    
    def test_template_04b_selected_when_firewall_enabled(self):
        """Test that Template 04B is selected when Network Firewall is enabled."""
        processor = NetworkProcessor()
        
        section_config = {
            'tgwArchitecture': {
                'vpcs': {
                    'inspectionVpc': {
                        'enabled': True,
                        'networkFirewall': True  # Firewall enabled
                    }
                },
                'transitGateway': {
                    'name': 'test-tgw',
                    'asn': 65000
                }
            }
        }
        
        template_name = processor.get_tgw_template_name(section_config)
        assert template_name == '04b-tgw-stackset-network-inspection-vpc-firewall.yaml'
    
    def test_no_template_when_tgw_disabled(self):
        """Test that no template is selected when Transit Gateway is absent."""
        processor = NetworkProcessor()
        
        section_config = {
            # No tgwArchitecture means no TGW
        }
        
        template_name = processor.get_tgw_template_name(section_config)
        assert template_name is None
    
    def test_no_template_when_inspection_vpc_disabled(self):
        """Test that no template is selected when Inspection VPC is disabled."""
        processor = NetworkProcessor()
        
        section_config = {
            'tgwArchitecture': {
                'vpcs': {
                    'inspectionVpc': {
                        'enabled': False  # Inspection VPC disabled
                    }
                },
                'transitGateway': {
                    'name': 'test-tgw',
                    'asn': 65000
                }
            }
        }
        
        template_name = processor.get_tgw_template_name(section_config)
        assert template_name is None
    
    def test_should_use_template_04a_returns_true(self):
        """Test should_use_template_04a returns True when conditions are met."""
        processor = NetworkProcessor()
        
        section_config = {
            'tgwArchitecture': {
                'vpcs': {
                    'inspectionVpc': {
                        'enabled': True,
                        'networkFirewall': False
                    }
                },
                'transitGateway': {
                    'name': 'test-tgw',
                    'asn': 65000
                }
            }
        }
        
        assert processor.should_use_template_04a(section_config) is True
    
    def test_should_use_template_04a_returns_false_when_firewall_enabled(self):
        """Test should_use_template_04a returns False when Network Firewall is enabled."""
        processor = NetworkProcessor()
        
        section_config = {
            'tgwArchitecture': {
                'vpcs': {
                    'inspectionVpc': {
                        'enabled': True,
                        'networkFirewall': True  # Firewall enabled
                    }
                },
                'transitGateway': {
                    'name': 'test-tgw',
                    'asn': 65000
                }
            }
        }
        
        assert processor.should_use_template_04a(section_config) is False
    
    def test_should_use_template_04b_returns_true(self):
        """Test should_use_template_04b returns True when conditions are met."""
        processor = NetworkProcessor()
        
        section_config = {
            'tgwArchitecture': {
                'vpcs': {
                    'inspectionVpc': {
                        'enabled': True,
                        'networkFirewall': True
                    }
                },
                'transitGateway': {
                    'name': 'test-tgw',
                    'asn': 65000
                }
            }
        }
        
        assert processor.should_use_template_04b(section_config) is True
    
    def test_should_use_template_04b_returns_false_when_firewall_disabled(self):
        """Test should_use_template_04b returns False when Network Firewall is disabled."""
        processor = NetworkProcessor()
        
        section_config = {
            'tgwArchitecture': {
                'vpcs': {
                    'inspectionVpc': {
                        'enabled': True,
                        'networkFirewall': False  # Firewall disabled
                    }
                },
                'transitGateway': {
                    'name': 'test-tgw',
                    'asn': 65000
                }
            }
        }
        
        assert processor.should_use_template_04b(section_config) is False
    
    def test_template_filtering_skip_reason_04a_when_firewall_enabled(self):
        """Test that Template 04A skip reason is correct when Network Firewall is enabled."""
        processor = NetworkProcessor()
        
        section_config = {
            'tgwArchitecture': {
                'vpcs': {
                    'inspectionVpc': {
                        'enabled': True,
                        'networkFirewall': True
                    }
                },
                'transitGateway': {
                    'name': 'test-tgw',
                    'asn': 65000
                }
            }
        }
        
        template_name = '04a-tgw-stackset-network-egress-vpc.yaml'
        correct_template = processor.get_tgw_template_name(section_config)
        
        if correct_template and template_name != correct_template:
            skip_reason = 'Network Firewall is enabled - using Template 04B instead'
        else:
            skip_reason = None
        
        assert skip_reason == 'Network Firewall is enabled - using Template 04B instead'
    
    def test_template_filtering_skip_reason_04b_when_firewall_disabled(self):
        """Test that Template 04B skip reason is correct when Network Firewall is disabled."""
        processor = NetworkProcessor()
        
        section_config = {
            'tgwArchitecture': {
                'vpcs': {
                    'inspectionVpc': {
                        'enabled': True,
                        'networkFirewall': False
                    }
                },
                'transitGateway': {
                    'name': 'test-tgw',
                    'asn': 65000
                }
            }
        }
        
        template_name = '04b-tgw-stackset-network-inspection-vpc-firewall.yaml'
        correct_template = processor.get_tgw_template_name(section_config)
        
        if correct_template and template_name != correct_template:
            skip_reason = 'Network Firewall is disabled - using Template 04A instead'
        else:
            skip_reason = None
        
        assert skip_reason == 'Network Firewall is disabled - using Template 04A instead'
    
    def test_template_filtering_skip_reason_when_tgw_not_enabled(self):
        """Test that skip reason is correct when Transit Gateway is not present."""
        processor = NetworkProcessor()
        
        section_config = {
            # No tgwArchitecture — TGW not deployed
        }
        
        template_name = '04a-tgw-stackset-network-egress-vpc.yaml'
        correct_template = processor.get_tgw_template_name(section_config)
        
        if correct_template is None:
            skip_reason = 'Transit Gateway or Inspection VPC not enabled in configuration'
        else:
            skip_reason = None
        
        assert skip_reason == 'Transit Gateway or Inspection VPC not enabled in configuration'
