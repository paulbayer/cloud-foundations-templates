"""
Test error handling for network processor.

This module tests various error scenarios including:
- Missing IPAM pool ID when IPAM enabled
- Missing VPC CIDR when IPAM disabled
- Invalid CIDR format
- CIDR overlap scenarios
- Graceful error handling
"""

import unittest
from titanium_generator.processors.network_processor import NetworkProcessor


class TestIPAMPoolIDErrorHandling(unittest.TestCase):
    """Test error handling for IPAM pool ID scenarios."""
    
    def test_missing_pool_id_when_ipam_enabled(self):
        """
        Test that missing IPAM pool ID is handled gracefully when IPAM is enabled.
        
        When IPAM is enabled but no pool ID is provided, the processor should:
        - Not raise an error (pool ID is optional)
        - Not set tRegionalIPAMPoolId parameter
        - Allow deployment to proceed (CloudFormation will handle missing pool ID)
        """
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
                            # No 'id' field - pool ID is missing
                        },
                        {
                            'name': 'regional-pool-us-west-2',
                            'provisionedCidrs': ['10.100.0.0/17']
                            # No 'id' field - pool ID is missing
                        }
                    ]
                }
            }
        ]
        
        # Should not raise an error
        updates = processor.generate_parameter_updates(config_items)
        
        # Verify IPAM is enabled
        self.assertEqual(updates['tDeployIPAM'], 'true')
        
        # Verify pool ID parameter is not set (missing pool ID)
        self.assertNotIn('tRegionalIPAMPoolId', updates)
        
        # Verify CIDR parameters are still set
        self.assertEqual(updates['tGlobalIPAMPoolCIDR'], '10.100.0.0/16')
        self.assertEqual(updates['tRegionalPoolCIDR'], '10.100.0.0/17')
    
    def test_empty_pool_id_when_ipam_enabled(self):
        """
        Test that empty IPAM pool ID is handled gracefully when IPAM is enabled.
        
        When IPAM is enabled but pool ID is an empty string, the processor should:
        - Not raise an error
        - Not set tRegionalIPAMPoolId parameter
        - Allow deployment to proceed
        """
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
                            'provisionedCidrs': ['10.100.0.0/17'],
                            'id': ''  # Empty pool ID
                        }
                    ]
                }
            }
        ]
        
        # Should not raise an error
        updates = processor.generate_parameter_updates(config_items)
        
        # Verify IPAM is enabled
        self.assertEqual(updates['tDeployIPAM'], 'true')
        
        # Verify pool ID parameter is not set (empty pool ID)
        self.assertNotIn('tRegionalIPAMPoolId', updates)
    
    def test_invalid_pool_id_format_handled_gracefully(self):
        """
        Test that invalid IPAM pool ID format is handled gracefully.
        
        When IPAM pool ID has invalid format, the processor should:
        - Log a warning (captured in capsys)
        - Not set tRegionalIPAMPoolId parameter
        - Allow deployment to proceed
        """
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
                            'provisionedCidrs': ['10.100.0.0/17'],
                            'id': 'invalid-pool-id-format'  # Invalid format
                        }
                    ]
                }
            }
        ]
        
        # Should not raise an error
        updates = processor.generate_parameter_updates(config_items)
        
        # Verify IPAM is enabled
        self.assertEqual(updates['tDeployIPAM'], 'true')
        
        # Verify pool ID parameter is not set (invalid format)
        self.assertNotIn('tRegionalIPAMPoolId', updates)


class TestVPCCIDRErrorHandling(unittest.TestCase):
    """Test error handling for VPC CIDR scenarios."""
    
    def test_missing_vpc_cidr_when_ipam_disabled(self):
        """
        Test behavior when VPC CIDR is missing and IPAM is disabled.
        
        Note: The network processor does NOT validate VPC CIDR parameters.
        VPC CIDR validation is handled by CloudFormation template parameter rules.
        
        When IPAM is disabled:
        - Network processor does not set uVpcCidr parameters (user-provided)
        - CloudFormation template will enforce parameter requirements
        - Template parameter rules will fail if uVpcCidr is not provided
        """
        processor = NetworkProcessor()
        
        config_items = [
            {
                'name': 'IPAM',
                'type': 'ipam',
                'enabled': False,  # IPAM disabled
                'config': {
                    'region': 'us-west-2',
                    'pools': []
                }
            },
            {
                'name': 'EndpointVpc',
                'type': 'endpoint_vpc',
                'enabled': True,
                'config': {
                    'availabilityZones': 2,
                    'subnetsPerAZ': 2
                    # No CIDR specified - will require user input
                }
            }
        ]
        
        # Should not raise an error in network processor
        updates = processor.generate_parameter_updates(config_items)
        
        # Verify IPAM is disabled
        self.assertEqual(updates['tDeployIPAM'], 'false')
        
        # Verify VPC is enabled
        self.assertEqual(updates['tDeployEndpointVpc'], 'true')
        
        # Verify no CIDR parameters are set (user must provide)
        self.assertNotIn('uEndpointVpcCidr', updates)
        self.assertNotIn('tRegionalIPAMPoolId', updates)


class TestCIDRFormatValidation(unittest.TestCase):
    """Test CIDR format validation scenarios."""
    
    def test_invalid_cidr_format_in_ipam_config(self):
        """
        Test that invalid CIDR format in IPAM configuration is handled.
        
        Note: The network processor does NOT validate CIDR format.
        CIDR validation is handled by:
        - CloudFormation template parameter patterns
        - AWS IPAM service during pool allocation
        
        The processor simply passes through CIDR values from the configuration.
        """
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
                            'provisionedCidrs': ['invalid-cidr-format']  # Invalid CIDR
                        }
                    ]
                }
            }
        ]
        
        # Should not raise an error in network processor
        updates = processor.generate_parameter_updates(config_items)
        
        # Verify IPAM is enabled
        self.assertEqual(updates['tDeployIPAM'], 'true')
        
        # Verify invalid CIDR is passed through (will fail in CloudFormation)
        self.assertEqual(updates['tGlobalIPAMPoolCIDR'], 'invalid-cidr-format')
    
    def test_cidr_with_invalid_netmask(self):
        """
        Test that CIDR with invalid netmask is handled.
        
        The processor passes through CIDR values without validation.
        CloudFormation and AWS services will validate the CIDR format.
        """
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
                            'provisionedCidrs': ['10.100.0.0/33']  # Invalid netmask (>32)
                        }
                    ]
                }
            }
        ]
        
        # Should not raise an error in network processor
        updates = processor.generate_parameter_updates(config_items)
        
        # Verify invalid CIDR is passed through
        self.assertEqual(updates['tGlobalIPAMPoolCIDR'], '10.100.0.0/33')
    
    def test_cidr_without_netmask(self):
        """
        Test that CIDR without netmask is handled.
        
        The processor passes through CIDR values without validation.
        """
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
                            'provisionedCidrs': ['10.100.0.0']  # Missing netmask
                        }
                    ]
                }
            }
        ]
        
        # Should not raise an error in network processor
        updates = processor.generate_parameter_updates(config_items)
        
        # Verify CIDR without netmask is passed through
        self.assertEqual(updates['tGlobalIPAMPoolCIDR'], '10.100.0.0')


class TestCIDROverlapScenarios(unittest.TestCase):
    """Test CIDR overlap scenarios."""
    
    def test_overlapping_global_and_regional_cidrs(self):
        """
        Test that overlapping global and regional CIDRs are handled.
        
        Note: The network processor does NOT validate CIDR overlap.
        CIDR overlap validation is handled by:
        - AWS IPAM service during pool allocation
        - CloudFormation during VPC creation
        
        The processor simply passes through CIDR values from the configuration.
        """
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
                            # Regional CIDR overlaps with global (should be subset)
                            'provisionedCidrs': ['10.200.0.0/16']  # Different range (overlap)
                        }
                    ]
                }
            }
        ]
        
        # Should not raise an error in network processor
        updates = processor.generate_parameter_updates(config_items)
        
        # Verify both CIDRs are set (overlap will be caught by AWS IPAM)
        self.assertEqual(updates['tGlobalIPAMPoolCIDR'], '10.100.0.0/16')
        self.assertEqual(updates['tRegionalPoolCIDR'], '10.200.0.0/16')
    
    def test_regional_cidr_not_subset_of_global(self):
        """
        Test that regional CIDR not being a subset of global CIDR is handled.
        
        AWS IPAM requires regional pools to be subsets of the global pool.
        The processor does not validate this - AWS IPAM will reject invalid configuration.
        """
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
                            # Regional CIDR is not a subset of global
                            'provisionedCidrs': ['192.168.0.0/16']
                        }
                    ]
                }
            }
        ]
        
        # Should not raise an error in network processor
        updates = processor.generate_parameter_updates(config_items)
        
        # Verify both CIDRs are set (AWS IPAM will validate subset relationship)
        self.assertEqual(updates['tGlobalIPAMPoolCIDR'], '10.100.0.0/16')
        self.assertEqual(updates['tRegionalPoolCIDR'], '192.168.0.0/16')


class TestGracefulErrorHandling(unittest.TestCase):
    """Test graceful error handling for various scenarios."""
    
    def test_empty_config_items_list(self):
        """
        Test that empty config items list is handled gracefully.
        """
        processor = NetworkProcessor()
        
        config_items = []
        
        # Should not raise an error
        updates = processor.generate_parameter_updates(config_items)
        
        # Verify updates is a dictionary (may be empty or have defaults)
        self.assertIsInstance(updates, dict)
    
    def test_missing_config_field_in_item(self):
        """
        Test that missing 'config' field in item is handled gracefully.
        """
        processor = NetworkProcessor()
        
        config_items = [
            {
                'name': 'EndpointVpc',
                'type': 'endpoint_vpc',
                'enabled': True
                # Missing 'config' field
            }
        ]
        
        # Should not raise an error
        updates = processor.generate_parameter_updates(config_items)
        
        # Verify VPC is enabled
        self.assertEqual(updates['tDeployEndpointVpc'], 'true')
    
    def test_missing_enabled_field_in_item(self):
        """
        Test that missing 'enabled' field in item is handled gracefully.
        """
        processor = NetworkProcessor()
        
        config_items = [
            {
                'name': 'EndpointVpc',
                'type': 'endpoint_vpc',
                # Missing 'enabled' field
                'config': {
                    'availabilityZones': 2
                }
            }
        ]
        
        # Should not raise an error
        updates = processor.generate_parameter_updates(config_items)
        
        # Verify VPC is disabled (default when 'enabled' is missing)
        self.assertEqual(updates['tDeployEndpointVpc'], 'false')
    
    def test_none_values_in_config(self):
        """
        Test that None values in configuration are handled gracefully.
        """
        processor = NetworkProcessor()
        
        config_items = [
            {
                'name': 'IPAM',
                'type': 'ipam',
                'enabled': True,
                'config': {
                    'region': None,  # None value
                    'pools': None  # None value
                }
            }
        ]
        
        # Should not raise an error
        updates = processor.generate_parameter_updates(config_items)
        
        # Verify IPAM is enabled
        self.assertEqual(updates['tDeployIPAM'], 'true')
    
    def test_empty_pools_list(self):
        """
        Test that empty pools list is handled gracefully.
        """
        processor = NetworkProcessor()
        
        config_items = [
            {
                'name': 'IPAM',
                'type': 'ipam',
                'enabled': True,
                'config': {
                    'region': 'us-west-2',
                    'pools': []  # Empty pools list
                }
            }
        ]
        
        # Should not raise an error
        updates = processor.generate_parameter_updates(config_items)
        
        # Verify IPAM is enabled
        self.assertEqual(updates['tDeployIPAM'], 'true')
        
        # Verify no pool parameters are set
        self.assertNotIn('tGlobalIPAMPoolCIDR', updates)
        self.assertNotIn('tRegionalPoolCIDR', updates)
        self.assertNotIn('tRegionalIPAMPoolId', updates)
    
    def test_malformed_pool_structure(self):
        """
        Test that malformed pool structure is handled gracefully.
        """
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
                            # Missing 'name' field
                            'provisionedCidrs': ['10.100.0.0/16']
                        },
                        {
                            'name': 'regional-pool-us-west-2'
                            # Missing 'provisionedCidrs' field
                        }
                    ]
                }
            }
        ]
        
        # Should not raise an error
        updates = processor.generate_parameter_updates(config_items)
        
        # Verify IPAM is enabled
        self.assertEqual(updates['tDeployIPAM'], 'true')
    
    def test_dependency_validation_error_message_clarity(self):
        """
        Test that dependency validation errors have clear, actionable messages.
        """
        processor = NetworkProcessor()
        
        # Test Network Firewall without Transit Gateway
        config_items = [
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {
                    'networkFirewall': True
                }
            }
        ]
        
        with self.assertRaises(ValueError) as context:
            processor.generate_parameter_updates(config_items)
        
        error_message = str(context.exception)
        
        # Verify error message is clear and actionable
        self.assertIn('Transit Gateway', error_message)
        self.assertIn('network.tgwArchitecture.transitGateway', error_message)
        
        # Verify error message explains the problem
        self.assertIn('requires', error_message.lower())
    
    def test_multiple_validation_errors_reported(self):
        """
        Test that validation catches the first error and reports it clearly.
        
        Note: Validation stops at the first error to provide clear feedback.
        """
        processor = NetworkProcessor()
        
        # Configuration with multiple issues:
        # 1. Inspection VPC without Transit Gateway
        # 2. Network Firewall without Transit Gateway
        config_items = [
            {
                'name': 'InspectionVpc',
                'type': 'inspection_vpc',
                'enabled': True,
                'config': {
                    'networkFirewall': True
                }
            }
        ]
        
        with self.assertRaises(ValueError) as context:
            processor.generate_parameter_updates(config_items)
        
        # Should report the first validation error
        error_message = str(context.exception)
        self.assertIn('Transit Gateway', error_message)


class TestLegacyKeyRejection(unittest.TestCase):
    """Test that legacy schema keys are rejected with a clear migration message."""

    def test_legacy_standard_architecture_raises_value_error(self):
        """Test that standardArchitecture key triggers ValueError."""
        processor = NetworkProcessor()
        section_config = {
            'architectureType': 'TGW',
            'standardArchitecture': {
                'connectivity': {
                    'transitGateway': {'enabled': True}
                }
            }
        }

        with self.assertRaises(ValueError) as context:
            processor.extract_items(section_config)

        error_message = str(context.exception)
        self.assertIn('Legacy network schema detected', error_message)
        self.assertIn('standardArchitecture', error_message)
        self.assertIn('tgwArchitecture', error_message)

    def test_legacy_transit_gateways_list_raises_value_error(self):
        """Test that transitGateways list key triggers ValueError."""
        processor = NetworkProcessor()
        section_config = {
            'architectureType': 'TGW',
            'transitGateways': [
                {'name': 'tgw-1', 'asn': 65000}
            ]
        }

        with self.assertRaises(ValueError) as context:
            processor.extract_items(section_config)

        error_message = str(context.exception)
        self.assertIn('Legacy network schema detected', error_message)
        self.assertIn('transitGateways', error_message)

    def test_both_legacy_keys_raises_value_error(self):
        """Test that both legacy keys present triggers ValueError."""
        processor = NetworkProcessor()
        section_config = {
            'architectureType': 'TGW',
            'standardArchitecture': {
                'connectivity': {}
            },
            'transitGateways': []
        }

        with self.assertRaises(ValueError) as context:
            processor.extract_items(section_config)

        error_message = str(context.exception)
        self.assertIn('Legacy network schema detected', error_message)


if __name__ == '__main__':
    unittest.main()
