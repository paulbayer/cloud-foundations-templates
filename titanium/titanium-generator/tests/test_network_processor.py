"""
Unit tests for NetworkProcessor.

Tests focus on IPAM pool ID extraction and validation functionality.
"""

import pytest
from titanium_generator.processors.network_processor import NetworkProcessor


class TestIPAMPoolIDExtraction:
    """Tests for IPAM pool ID extraction functionality."""
    
    def test_extract_single_regional_pool_id(self):
        """Test extraction of a single regional IPAM pool ID."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'IPAM',
                'type': 'ipam',
                'enabled': True,
                'config': {
                    'region': 'us-west-2',
                    'pools': [
                        {
                            'name': 'global-pool',
                            'provisionedCidrs': ['10.100.0.0/16']
                        },
                        {
                            'name': 'regional-pool-us-west-2',
                            'id': 'ipam-pool-0a1b2c3d4e5f6789',
                            'provisionedCidrs': ['10.100.0.0/17']
                        }
                    ]
                }
            }
        ]
        
        updates = processor.generate_parameter_updates(config_items)
        
        assert 'tRegionalIPAMPoolId' in updates
        assert updates['tRegionalIPAMPoolId'] == 'ipam-pool-0a1b2c3d4e5f6789'
    
    def test_extract_multiple_regional_pool_ids(self):
        """Test extraction when multiple regional pools exist - should use first one."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'IPAM',
                'type': 'ipam',
                'enabled': True,
                'config': {
                    'region': 'us-west-2',
                    'pools': [
                        {
                            'name': 'regional-pool-us-west-2',
                            'id': 'ipam-pool-111111111111',
                            'provisionedCidrs': ['10.100.0.0/17']
                        },
                        {
                            'name': 'regional-pool-us-east-1',
                            'id': 'ipam-pool-222222222222',
                            'provisionedCidrs': ['10.100.128.0/17']
                        }
                    ]
                }
            }
        ]
        
        updates = processor.generate_parameter_updates(config_items)
        
        # Should use the first regional pool ID
        assert 'tRegionalIPAMPoolId' in updates
        assert updates['tRegionalIPAMPoolId'] == 'ipam-pool-111111111111'
    
    def test_no_pool_id_when_missing(self):
        """Test that no pool ID parameter is set when ID is missing."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'IPAM',
                'type': 'ipam',
                'enabled': True,
                'config': {
                    'region': 'us-west-2',
                    'pools': [
                        {
                            'name': 'regional-pool-us-west-2',
                            'provisionedCidrs': ['10.100.0.0/17']
                            # No 'id' field
                        }
                    ]
                }
            }
        ]
        
        updates = processor.generate_parameter_updates(config_items)
        
        # Should not have pool ID parameter
        assert 'tRegionalIPAMPoolId' not in updates
    
    def test_pool_id_with_empty_string(self):
        """Test that empty string pool ID is not added."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'IPAM',
                'type': 'ipam',
                'enabled': True,
                'config': {
                    'region': 'us-west-2',
                    'pools': [
                        {
                            'name': 'regional-pool-us-west-2',
                            'id': '',  # Empty string
                            'provisionedCidrs': ['10.100.0.0/17']
                        }
                    ]
                }
            }
        ]
        
        updates = processor.generate_parameter_updates(config_items)
        
        # Should not have pool ID parameter
        assert 'tRegionalIPAMPoolId' not in updates


class TestIPAMPoolIDValidation:
    """Tests for IPAM pool ID format validation."""
    
    def test_valid_pool_id_format(self):
        """Test validation of valid IPAM pool ID formats."""
        processor = NetworkProcessor()
        
        # Valid formats
        assert processor._validate_ipam_pool_id('ipam-pool-0a1b2c3d4e5f6789') is True
        assert processor._validate_ipam_pool_id('ipam-pool-123456789abcdef') is True
        assert processor._validate_ipam_pool_id('ipam-pool-ABCDEF123456789') is True
        assert processor._validate_ipam_pool_id('ipam-pool-0') is True
    
    def test_invalid_pool_id_format(self):
        """Test validation rejects invalid IPAM pool ID formats."""
        processor = NetworkProcessor()
        
        # Invalid formats
        assert processor._validate_ipam_pool_id('') is False
        assert processor._validate_ipam_pool_id('ipam-pool-') is False
        assert processor._validate_ipam_pool_id('pool-0a1b2c3d4e5f6789') is False
        assert processor._validate_ipam_pool_id('ipam-0a1b2c3d4e5f6789') is False
        assert processor._validate_ipam_pool_id('ipam-pool-xyz') is False  # Non-hex characters
        assert processor._validate_ipam_pool_id('ipam-pool-0a1b2c3d-4e5f6789') is False  # Contains dash
    
    def test_invalid_pool_id_skipped(self, capsys):
        """Test that invalid pool IDs are skipped with warning."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'IPAM',
                'type': 'ipam',
                'enabled': True,
                'config': {
                    'region': 'us-west-2',
                    'pools': [
                        {
                            'name': 'regional-pool-us-west-2',
                            'id': 'invalid-pool-id',  # Invalid format
                            'provisionedCidrs': ['10.100.0.0/17']
                        }
                    ]
                }
            }
        ]
        
        updates = processor.generate_parameter_updates(config_items)
        
        # Should not have pool ID parameter
        assert 'tRegionalIPAMPoolId' not in updates
        
        # Should print warning
        captured = capsys.readouterr()
        assert 'Warning: Invalid IPAM pool ID format' in captured.out


class TestIPAMPoolIDWithCIDRExtraction:
    """Tests for IPAM pool ID extraction alongside CIDR extraction."""
    
    def test_extract_pool_id_and_cidrs(self):
        """Test that both pool ID and CIDRs are extracted correctly."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'IPAM',
                'type': 'ipam',
                'enabled': True,
                'config': {
                    'region': 'us-west-2',
                    'pools': [
                        {
                            'name': 'global-pool',
                            'provisionedCidrs': ['10.100.0.0/16']
                        },
                        {
                            'name': 'regional-pool-us-west-2',
                            'id': 'ipam-pool-0a1b2c3d4e5f6789',
                            'provisionedCidrs': ['10.100.0.0/17']
                        }
                    ]
                }
            }
        ]
        
        updates = processor.generate_parameter_updates(config_items)
        
        # All parameters should be present
        assert updates['tDeployIPAM'] == 'true'
        assert updates['tIPAMRegion'] == 'us-west-2'
        assert updates['tGlobalIPAMPoolCIDR'] == '10.100.0.0/16'
        assert updates['tRegionalPoolCIDR'] == '10.100.0.0/17'
        assert updates['tRegionalIPAMPoolId'] == 'ipam-pool-0a1b2c3d4e5f6789'
    
    def test_regional_pool_without_cidr_but_with_id(self):
        """Test extraction when regional pool has ID but no CIDR."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'IPAM',
                'type': 'ipam',
                'enabled': True,
                'config': {
                    'region': 'us-west-2',
                    'pools': [
                        {
                            'name': 'regional-pool-us-west-2',
                            'id': 'ipam-pool-0a1b2c3d4e5f6789'
                            # No provisionedCidrs
                        }
                    ]
                }
            }
        ]
        
        updates = processor.generate_parameter_updates(config_items)
        
        # Pool ID should still be extracted
        assert 'tRegionalIPAMPoolId' in updates
        assert updates['tRegionalIPAMPoolId'] == 'ipam-pool-0a1b2c3d4e5f6789'
        
        # CIDR should not be present
        assert 'tRegionalPoolCIDR' not in updates


class TestIPAMDefaultDeployment:
    """Tests for IPAM default deployment logic (from task 1)."""
    
    def test_ipam_defaults_to_true_when_config_exists(self):
        """Test that IPAM defaults to true when configuration exists."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'IPAM',
                'type': 'ipam',
                'enabled': True,  # Explicitly enabled
                'config': {
                    'region': 'us-west-2',
                    'pools': []
                }
            }
        ]
        
        updates = processor.generate_parameter_updates(config_items)
        assert updates['tDeployIPAM'] == 'true'
    
    def test_ipam_respects_explicit_false(self):
        """Test that IPAM respects explicit false setting."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'IPAM',
                'type': 'ipam',
                'enabled': False,  # Explicitly disabled
                'config': {
                    'region': 'us-west-2',
                    'pools': []
                }
            }
        ]
        
        updates = processor.generate_parameter_updates(config_items)
        assert updates['tDeployIPAM'] == 'false'



class TestNetworkDependencyValidation:
    """Tests for bidirectional dependency validation (TGW ↔ Egress/Inspection VPC)."""
    
    def test_network_firewall_requires_transit_gateway(self):
        """Test that Network Firewall validation requires Transit Gateway."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {'networkFirewall': True}
            }
            # Missing Transit Gateway
        ]
        
        with pytest.raises(ValueError) as exc_info:
            processor.generate_parameter_updates(config_items)
        
        # When Network Firewall is enabled, Inspection VPC is also enabled
        # So the error will be about Inspection VPC requiring Transit Gateway
        assert 'Inspection VPC requires Transit Gateway' in str(exc_info.value)
        assert 'transitGateway' in str(exc_info.value)
    
    def test_transit_gateway_without_egress_still_emits_tgw_toggle(self):
        """TGW with no Egress/Inspection VPC is a no-op, not an error (issue #99).

        It must not raise; the TGW deploy toggle is still emitted (the 04a/04b
        templates are separately skipped at generation time when no egress/
        inspection VPC exists, so nothing is actually deployed)."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'TransitGateway',
                'type': 'transit_gateway',
                'enabled': True,
                'config': {}
            }
            # No Egress/Inspection VPC — valid minimal/staged setup, not an error.
        ]

        updates = processor.generate_parameter_updates(config_items)
        assert updates['tDeployTransitGateway'] == 'true'
    
    def test_inspection_vpc_requires_transit_gateway(self):
        """Test that Inspection VPC requires Transit Gateway for routing."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {'networkFirewall': True}
            }
            # Missing Transit Gateway
        ]
        
        with pytest.raises(ValueError) as exc_info:
            processor.generate_parameter_updates(config_items)
        
        assert 'Inspection VPC requires Transit Gateway' in str(exc_info.value)
        assert 'transitGateway' in str(exc_info.value)
    
    def test_transit_gateway_without_egress_warns_not_raises(self, caplog):
        """TGW with no centralized egress logs a warning instead of raising (issue #99)."""
        import logging
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'TransitGateway',
                'type': 'transit_gateway',
                'enabled': True,
                'config': {}
            }
            # No Egress/Inspection VPC.
        ]

        with caplog.at_level(logging.WARNING):
            processor.generate_parameter_updates(config_items)

        assert any(
            'no Egress or Inspection VPC' in rec.message for rec in caplog.records
        )
    
    def test_valid_configuration_tgw_with_egress_vpc(self):
        """Test valid configuration: TGW + Egress VPC (Inspection VPC without firewall)."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'TransitGateway',
                'type': 'transit_gateway',
                'enabled': True,
                'config': {}
            },
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {'networkFirewall': False}  # Acts as Egress VPC
            }
        ]
        
        # Should not raise any errors
        updates = processor.generate_parameter_updates(config_items)
        assert updates['tDeployTransitGateway'] == 'true'
        assert updates['tDeployInspectionVpc'] == 'true'
        assert updates['tDeployNetworkFirewall'] == 'false'
    
    def test_valid_configuration_tgw_with_inspection_vpc_and_firewall(self):
        """Test valid configuration: TGW + Inspection VPC + Network Firewall."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'TransitGateway',
                'type': 'transit_gateway',
                'enabled': True,
                'config': {}
            },
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {'networkFirewall': True}
            }
        ]
        
        # Should not raise any errors
        updates = processor.generate_parameter_updates(config_items)
        assert updates['tDeployTransitGateway'] == 'true'
        assert updates['tDeployInspectionVpc'] == 'true'
        assert updates['tDeployNetworkFirewall'] == 'true'
    
    def test_egress_vpc_without_tgw_fails(self):
        """Test that Egress VPC (Inspection VPC without firewall) requires TGW."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {'networkFirewall': False}  # Acts as Egress VPC
            }
            # Missing Transit Gateway
        ]
        
        with pytest.raises(ValueError) as exc_info:
            processor.generate_parameter_updates(config_items)
        
        # Should fail because Egress VPC needs TGW for routing
        # Note: Egress VPC is represented as Inspection VPC without firewall
        assert 'Transit Gateway' in str(exc_info.value)
    
    def test_network_firewall_with_all_dependencies_succeeds(self):
        """Test that Network Firewall with all dependencies succeeds."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'TransitGateway',
                'type': 'transit_gateway',
                'enabled': True,
                'config': {
                    'routeTableStructure': 'segregated',
                    'routeTables': ['shared', 'isolated']
                }
            },
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {
                    'networkFirewall': True,
                    'availabilityZones': 2,
                    'subnetsPerAZ': 3
                }
            }
        ]
        
        # Should not raise any errors
        updates = processor.generate_parameter_updates(config_items)
        assert updates['tDeployTransitGateway'] == 'true'
        assert updates['tDeployInspectionVpc'] == 'true'
        assert updates['tDeployNetworkFirewall'] == 'true'
        assert updates['tTransitGatewayRouteTableStructure'] == 'segregated'
    
    def test_validation_error_messages_are_clear(self):
        """Test that validation error messages provide clear guidance."""
        processor = NetworkProcessor()
        
        # Test Network Firewall without TGW
        config_items = [
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {'networkFirewall': True}
            }
        ]
        
        with pytest.raises(ValueError) as exc_info:
            processor.generate_parameter_updates(config_items)
        
        error_message = str(exc_info.value)
        # Error message should be actionable
        assert 'Invalid network configuration' in error_message
        # When Network Firewall is enabled, Inspection VPC is also enabled
        # So the error will be about Inspection VPC requiring Transit Gateway
        assert 'Inspection VPC requires Transit Gateway' in error_message
        assert 'transitGateway' in error_message
        assert 'Titanium YAML' in error_message


class TestVPCFlowLogsRetentionFallback:
    """Tests for VPC Flow Logs retention fallback logic (task 4)."""
    
    def test_retention_from_vpc_flow_logs_section(self):
        """Test that retention is extracted from vpcFlowLogs.retentionDays when present."""
        processor = NetworkProcessor()
        
        # Set full config with vpcFlowLogs section
        full_config = {
            'vpcFlowLogs': {
                'enable': True,
                'trafficType': 'ALL',
                'retentionDays': 2555
            }
        }
        processor.set_full_config(full_config)
        
        # Config items that trigger VPC Flow Logs bucket deployment
        config_items = [
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {'networkFirewall': True}
            },
            {
                'name': 'TransitGateway',
                'type': 'transit_gateway',
                'enabled': True,
                'config': {}
            }
        ]
        
        updates = processor.generate_parameter_updates(config_items)
        
        assert updates['tDeployVPCFlowLogsBucket'] == 'true'
        assert updates['tBucketRetentionDays'] == '2555'
    
    def test_retention_fallback_to_pattern_variable(self):
        """Test that retention falls back to pattern variable when vpcFlowLogs section missing."""
        processor = NetworkProcessor()
        
        # Set full config WITHOUT vpcFlowLogs section
        full_config = {}
        processor.set_full_config(full_config)
        
        # Set pattern variables with vpc_flow_retention
        pattern_variables = {
            'vpc_flow_retention': 365
        }
        processor.set_pattern_variables(pattern_variables)
        
        # Config items that trigger VPC Flow Logs bucket deployment
        config_items = [
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {'networkFirewall': True}
            },
            {
                'name': 'TransitGateway',
                'type': 'transit_gateway',
                'enabled': True,
                'config': {}
            }
        ]
        
        updates = processor.generate_parameter_updates(config_items)
        
        assert updates['tDeployVPCFlowLogsBucket'] == 'true'
        assert updates['tBucketRetentionDays'] == '365'
    
    def test_retention_default_when_both_sources_missing(self):
        """Test that retention defaults to 90 days when both sources missing."""
        processor = NetworkProcessor()
        
        # Set full config WITHOUT vpcFlowLogs section
        full_config = {}
        processor.set_full_config(full_config)
        
        # No pattern variables set
        
        # Config items that trigger VPC Flow Logs bucket deployment
        config_items = [
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {'networkFirewall': True}
            },
            {
                'name': 'TransitGateway',
                'type': 'transit_gateway',
                'enabled': True,
                'config': {}
            }
        ]
        
        updates = processor.generate_parameter_updates(config_items)
        
        assert updates['tDeployVPCFlowLogsBucket'] == 'true'
        assert updates['tBucketRetentionDays'] == '90'
    
    def test_retention_prefers_vpc_flow_logs_over_pattern_variable(self):
        """Test that vpcFlowLogs.retentionDays takes precedence over pattern variable."""
        processor = NetworkProcessor()
        
        # Set full config with vpcFlowLogs section
        full_config = {
            'vpcFlowLogs': {
                'enable': True,
                'trafficType': 'ALL',
                'retentionDays': 2555
            }
        }
        processor.set_full_config(full_config)
        
        # Set pattern variables with different retention value
        pattern_variables = {
            'vpc_flow_retention': 365
        }
        processor.set_pattern_variables(pattern_variables)
        
        # Config items that trigger VPC Flow Logs bucket deployment
        config_items = [
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {'networkFirewall': True}
            },
            {
                'name': 'TransitGateway',
                'type': 'transit_gateway',
                'enabled': True,
                'config': {}
            }
        ]
        
        updates = processor.generate_parameter_updates(config_items)
        
        # Should use vpcFlowLogs value (2555), not pattern variable (365)
        assert updates['tDeployVPCFlowLogsBucket'] == 'true'
        assert updates['tBucketRetentionDays'] == '2555'
    
    def test_retention_fallback_when_lifecycle_rules_empty(self):
        """Test fallback to pattern variable when lifecycle rules exist but are empty."""
        processor = NetworkProcessor()
        
        # Set full config with vpcFlowLogs section but empty lifecycle rules
        full_config = {
            'vpcFlowLogs': {
                'destinations': ['s3'],
                'destinationsConfig': {
                    's3': {
                        'lifecycleRules': []  # Empty list
                    }
                }
            }
        }
        processor.set_full_config(full_config)
        
        # Set pattern variables
        pattern_variables = {
            'vpc_flow_retention': 730
        }
        processor.set_pattern_variables(pattern_variables)
        
        # Config items that trigger VPC Flow Logs bucket deployment
        config_items = [
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {'networkFirewall': True}
            },
            {
                'name': 'TransitGateway',
                'type': 'transit_gateway',
                'enabled': True,
                'config': {}
            }
        ]
        
        updates = processor.generate_parameter_updates(config_items)
        
        # Should fall back to pattern variable
        assert updates['tDeployVPCFlowLogsBucket'] == 'true'
        assert updates['tBucketRetentionDays'] == '730'
    
    def test_retention_fallback_when_lifecycle_rule_disabled(self):
        """Test fallback when lifecycle rule exists but is disabled."""
        processor = NetworkProcessor()
        
        # Set full config with disabled lifecycle rule
        full_config = {
            'vpcFlowLogs': {
                'destinations': ['s3'],
                'destinationsConfig': {
                    's3': {
                        'lifecycleRules': [
                            {
                                'enabled': False,  # Disabled
                                'expiration': 2555
                            }
                        ]
                    }
                }
            }
        }
        processor.set_full_config(full_config)
        
        # Set pattern variables
        pattern_variables = {
            'vpc_flow_retention': 1000
        }
        processor.set_pattern_variables(pattern_variables)
        
        # Config items that trigger VPC Flow Logs bucket deployment
        config_items = [
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {'networkFirewall': True}
            },
            {
                'name': 'TransitGateway',
                'type': 'transit_gateway',
                'enabled': True,
                'config': {}
            }
        ]
        
        updates = processor.generate_parameter_updates(config_items)
        
        # Should fall back to pattern variable since rule is disabled
        assert updates['tDeployVPCFlowLogsBucket'] == 'true'
        assert updates['tBucketRetentionDays'] == '1000'
    
    def test_no_retention_parameter_when_bucket_not_deployed(self):
        """Test that retention parameter is not set when bucket is not deployed."""
        processor = NetworkProcessor()
        
        # Set pattern variables
        pattern_variables = {
            'vpc_flow_retention': 365
        }
        processor.set_pattern_variables(pattern_variables)
        
        # Config items that do NOT trigger VPC Flow Logs bucket deployment
        config_items = [
            {
                'name': 'EndpointVpc',
                'type': 'endpoint_vpc',
                'enabled': True,
                'config': {}
            }
        ]
        
        updates = processor.generate_parameter_updates(config_items)
        
        # Bucket should not be deployed
        assert updates['tDeployVPCFlowLogsBucket'] == 'false'
        # Retention parameter should not be set
        assert 'tBucketRetentionDays' not in updates



class TestTemplateSelection:
    """Tests for template selection logic."""
    
    def test_should_use_template_04a_with_egress_vpc(self):
        """Test that Template 04A is selected for TGW + Egress VPC (no firewall)."""
        processor = NetworkProcessor()
        section_config = {
            'tgwArchitecture': {
                'transitGateway': {
                    'name': 'example-tgw',
                    'asn': 65000
                },
                'vpcs': {
                    'inspectionVpc': {
                        'enabled': True,
                        'networkFirewall': False  # No firewall = Egress VPC
                    }
                }
            }
        }
        
        assert processor.should_use_template_04a(section_config) is True
        assert processor.should_use_template_04b(section_config) is False
        assert processor.get_tgw_template_name(section_config) == "04a-tgw-stackset-network-egress-vpc.yaml"
    
    def test_should_use_template_04b_with_network_firewall(self):
        """Test that Template 04B is selected for TGW + Inspection VPC + Network Firewall."""
        processor = NetworkProcessor()
        section_config = {
            'tgwArchitecture': {
                'transitGateway': {
                    'name': 'example-tgw',
                    'asn': 65000
                },
                'vpcs': {
                    'inspectionVpc': {
                        'enabled': True,
                        'networkFirewall': True  # With firewall = Inspection VPC
                    }
                }
            }
        }
        
        assert processor.should_use_template_04a(section_config) is False
        assert processor.should_use_template_04b(section_config) is True
        assert processor.get_tgw_template_name(section_config) == "04b-tgw-stackset-network-inspection-vpc-firewall.yaml"
    
    def test_no_template_when_tgw_absent(self):
        """Test that no template is selected when tgwArchitecture is absent."""
        processor = NetworkProcessor()
        section_config = {
            'architectureType': 'CloudWan'
            # No tgwArchitecture — TGW is not deployed
        }
        
        assert processor.should_use_template_04a(section_config) is False
        assert processor.should_use_template_04b(section_config) is False
        assert processor.get_tgw_template_name(section_config) is None
    
    def test_no_template_when_inspection_vpc_disabled(self):
        """Test that no template is selected when Inspection VPC is disabled."""
        processor = NetworkProcessor()
        section_config = {
            'tgwArchitecture': {
                'transitGateway': {
                    'name': 'example-tgw',
                    'asn': 65000
                },
                'vpcs': {
                    'inspectionVpc': {
                        'enabled': False,
                        'networkFirewall': False
                    }
                }
            }
        }
        
        assert processor.should_use_template_04a(section_config) is False
        assert processor.should_use_template_04b(section_config) is False
        assert processor.get_tgw_template_name(section_config) is None
    
    def test_template_04b_takes_precedence_when_firewall_enabled(self):
        """Test that Template 04B is selected when Network Firewall is enabled."""
        processor = NetworkProcessor()
        section_config = {
            'tgwArchitecture': {
                'transitGateway': {
                    'name': 'example-tgw',
                    'asn': 65000
                },
                'vpcs': {
                    'inspectionVpc': {
                        'enabled': True,
                        'networkFirewall': True
                    }
                }
            }
        }
        
        # Template 04B should be selected (has precedence)
        assert processor.should_use_template_04b(section_config) is True
        assert processor.should_use_template_04a(section_config) is False
        assert processor.get_tgw_template_name(section_config) == "04b-tgw-stackset-network-inspection-vpc-firewall.yaml"
    
    def test_template_selection_with_missing_network_firewall_key(self):
        """Test template selection when networkFirewall key is missing (defaults to False)."""
        processor = NetworkProcessor()
        section_config = {
            'tgwArchitecture': {
                'transitGateway': {
                    'name': 'example-tgw',
                    'asn': 65000
                },
                'vpcs': {
                    'inspectionVpc': {
                        'enabled': True
                        # networkFirewall key missing - defaults to False
                    }
                }
            }
        }
        
        # Should select Template 04A (Egress VPC without firewall)
        assert processor.should_use_template_04a(section_config) is True
        assert processor.should_use_template_04b(section_config) is False
        assert processor.get_tgw_template_name(section_config) == "04a-tgw-stackset-network-egress-vpc.yaml"
    
    def test_template_selection_with_empty_tgw_architecture(self):
        """Test template selection with empty tgwArchitecture section."""
        processor = NetworkProcessor()
        section_config = {
            'tgwArchitecture': {}
        }
        
        assert processor.should_use_template_04a(section_config) is False
        assert processor.should_use_template_04b(section_config) is False
        assert processor.get_tgw_template_name(section_config) is None
    
    def test_template_selection_with_missing_sections(self):
        """Test template selection with missing configuration sections."""
        processor = NetworkProcessor()
        section_config = {}
        
        assert processor.should_use_template_04a(section_config) is False
        assert processor.should_use_template_04b(section_config) is False
        assert processor.get_tgw_template_name(section_config) is None
    
    def test_get_template_selection_criteria_includes_template_info(self):
        """Test that template selection criteria includes relevant information."""
        processor = NetworkProcessor()
        section_config = {
            'architectureType': 'TGW',
            'tgwArchitecture': {
                'transitGateway': {
                    'name': 'example-tgw',
                    'asn': 65000
                },
                'vpcs': {
                    'inspectionVpc': {
                        'enabled': True,
                        'networkFirewall': True
                    },
                    'endpointVpc': {
                        'enabled': True
                    }
                }
            },
            'ipam': {
                'enabled': True
            }
        }
        
        criteria = processor.get_template_selection_criteria(section_config)
        
        assert criteria['architecture_type'] == 'TGW'
        assert criteria['has_transit_gateway'] is True
        assert criteria['has_inspection_vpc'] is True
        assert criteria['has_endpoint_vpc'] is True
        assert criteria['has_ipam'] is True
    
    def test_template_selection_integration_with_parameter_generation(self):
        """Test that template selection works correctly with parameter generation."""
        processor = NetworkProcessor()
        
        # Config for Template 04A (Egress VPC without firewall)
        config_items = [
            {
                'name': 'TransitGateway',
                'type': 'transit_gateway',
                'enabled': True,
                'config': {}
            },
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {'networkFirewall': False}
            }
        ]
        
        # Generate parameters
        updates = processor.generate_parameter_updates(config_items)
        
        # Verify parameters are set correctly
        assert updates['tDeployTransitGateway'] == 'true'
        assert updates['tDeployInspectionVpc'] == 'true'
        assert updates['tDeployNetworkFirewall'] == 'false'
        
        # Verify template selection
        section_config = {
            'tgwArchitecture': {
                'transitGateway': {
                    'name': 'example-tgw',
                    'asn': 65000
                },
                'vpcs': {
                    'inspectionVpc': {
                        'enabled': True,
                        'networkFirewall': False
                    }
                }
            }
        }
        
        assert processor.get_tgw_template_name(section_config) == "04a-tgw-stackset-network-egress-vpc.yaml"
    
    def test_template_selection_validates_dependencies(self):
        """Test that template selection respects dependency validation."""
        processor = NetworkProcessor()
        
        # Config that should fail validation (Network Firewall without TGW)
        config_items = [
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {'networkFirewall': True}
            }
            # Missing Transit Gateway
        ]
        
        # Should raise validation error
        with pytest.raises(ValueError) as exc_info:
            processor.generate_parameter_updates(config_items)
        
        # When Network Firewall is enabled, Inspection VPC is also enabled
        # So the error will be about Inspection VPC requiring Transit Gateway
        assert 'Inspection VPC requires Transit Gateway' in str(exc_info.value)


class TestTransitGatewayNameAndAsn:
    """Tests for TGW name and ASN parameter emission (schema refactor)."""

    def test_tgw_name_and_asn_emitted(self):
        """Test that tTransitGatewayName and tTransitGatewayAsn are emitted."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'TransitGateway',
                'type': 'transit_gateway',
                'enabled': True,
                'config': {
                    'name': 'my-tgw',
                    'asn': 64512,
                    'routeTableStructure': 'segregated',
                    'routeTables': ['Core', 'Segregated']
                }
            },
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {'networkFirewall': True}
            }
        ]

        updates = processor.generate_parameter_updates(config_items)

        assert updates['tTransitGatewayName'] == 'my-tgw'
        assert updates['tTransitGatewayAsn'] == '64512'

    def test_tgw_name_and_asn_omitted_when_absent(self):
        """Test that name/asn params are not emitted when fields are missing."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'TransitGateway',
                'type': 'transit_gateway',
                'enabled': True,
                'config': {
                    'routeTableStructure': 'segregated',
                    'routeTables': ['Core']
                    # No name or asn
                }
            },
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {'networkFirewall': True}
            }
        ]

        updates = processor.generate_parameter_updates(config_items)

        assert 'tTransitGatewayName' not in updates
        assert 'tTransitGatewayAsn' not in updates
        assert updates['tDeployTransitGateway'] == 'true'

    def test_tgw_asn_emitted_as_string(self):
        """Test that ASN is emitted as a string representation of the integer."""
        processor = NetworkProcessor()
        config_items = [
            {
                'name': 'TransitGateway',
                'type': 'transit_gateway',
                'enabled': True,
                'config': {
                    'name': 'test-tgw',
                    'asn': 65000
                }
            },
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {'networkFirewall': False}
            }
        ]

        updates = processor.generate_parameter_updates(config_items)

        assert updates['tTransitGatewayAsn'] == '65000'
        assert isinstance(updates['tTransitGatewayAsn'], str)
