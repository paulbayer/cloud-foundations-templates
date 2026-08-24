"""
Test IPAM pool ID extraction with Titanium.yaml that includes pool IDs.

This test demonstrates how the network processor would handle the Titanium.yaml
after IPAM has been deployed and pool IDs have been added to the configuration.
"""

import pytest
import yaml
from pathlib import Path
from titanium_generator.processors.network_processor import NetworkProcessor


class TestTitaniumYAMLWithPoolIDs:
    """Tests simulating Titanium.yaml after IPAM deployment with pool IDs."""
    
    def test_extract_with_pool_ids_added(self):
        """Test extraction when pool IDs are added to the configuration."""
        # Load the actual Titanium.yaml and modify it to include pool IDs
        titanium_yaml_path = Path(__file__).parent.parent.parent / "Titanium.yaml"
        
        with open(titanium_yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Simulate adding pool IDs after IPAM deployment
        # This is what the configuration would look like after running IPAM CloudFormation
        network_config = config.get('network', {})
        ipam_config = network_config.get('ipam', {})
        
        # Add pool IDs to the pools (simulating post-deployment state)
        for pool in ipam_config.get('pools', []):
            if pool['name'] == 'global-pool':
                pool['id'] = 'ipam-pool-0a1b2c3d4e5f6789'
            elif 'regional-pool' in pool['name']:
                pool['id'] = 'ipam-pool-1234567890abcdef'
        
        # Create processor and extract items
        processor = NetworkProcessor()
        items = processor.extract_items(network_config)
        updates = processor.generate_parameter_updates(items)
        
        # Verify IPAM parameters including pool ID
        assert updates['tDeployIPAM'] == 'true'
        assert updates['tIPAMRegion'] == 'us-east-1'
        assert updates['tGlobalIPAMPoolCIDR'] == '10.218.0.0/18'
        assert updates['tRegionalPoolCIDR'] == '10.218.0.0/19'
        
        # Verify pool ID was extracted
        assert 'tRegionalIPAMPoolId' in updates
        assert updates['tRegionalIPAMPoolId'] == 'ipam-pool-1234567890abcdef'
    
    def test_multiple_regional_pools_with_ids(self):
        """Test extraction when multiple regional pools have IDs."""
        titanium_yaml_path = Path(__file__).parent.parent.parent / "Titanium.yaml"
        
        with open(titanium_yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        network_config = config.get('network', {})
        ipam_config = network_config.get('ipam', {})
        
        # Add ID to existing regional pool first
        pools = ipam_config.get('pools', [])
        for pool in pools:
            if 'regional-pool' in pool.get('name', ''):
                pool['id'] = 'ipam-pool-1111111111111111'
        
        # Add a second regional pool with ID
        pools.append({
            'name': 'regional-pool-us-west-2',
            'description': 'Regional pool for us-west-2',
            'locale': 'us-west-2',
            'sourceIpamPool': 'global-pool',
            'id': 'ipam-pool-9999999999999999',
            'provisionedCidrs': ['10.218.32.0/19']
        })
        
        processor = NetworkProcessor()
        items = processor.extract_items(network_config)
        updates = processor.generate_parameter_updates(items)
        
        # Should use the first regional pool ID encountered
        # The processor iterates through pools in order, so it will use the first one
        assert 'tRegionalIPAMPoolId' in updates
        # The first regional pool in the list gets used
        assert updates['tRegionalIPAMPoolId'] == 'ipam-pool-1111111111111111'
    
    def test_invalid_pool_id_handling(self, capsys):
        """Test that invalid pool IDs are handled gracefully."""
        titanium_yaml_path = Path(__file__).parent.parent.parent / "Titanium.yaml"
        
        with open(titanium_yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        network_config = config.get('network', {})
        ipam_config = network_config.get('ipam', {})
        
        # Add an invalid pool ID
        for pool in ipam_config.get('pools', []):
            if 'regional-pool' in pool['name']:
                pool['id'] = 'invalid-pool-format'
        
        processor = NetworkProcessor()
        items = processor.extract_items(network_config)
        updates = processor.generate_parameter_updates(items)
        
        # Pool ID should not be present due to invalid format
        assert 'tRegionalIPAMPoolId' not in updates
        
        # Should have printed a warning
        captured = capsys.readouterr()
        assert 'Warning: Invalid IPAM pool ID format' in captured.out
    
    def test_pool_id_extraction_for_vpc_templates(self):
        """Test that pool ID is correctly formatted for VPC template usage."""
        titanium_yaml_path = Path(__file__).parent.parent.parent / "Titanium.yaml"
        
        with open(titanium_yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        network_config = config.get('network', {})
        ipam_config = network_config.get('ipam', {})
        
        # Add pool ID
        for pool in ipam_config.get('pools', []):
            if 'regional-pool' in pool['name']:
                pool['id'] = 'ipam-pool-abcdef1234567890'
        
        processor = NetworkProcessor()
        items = processor.extract_items(network_config)
        updates = processor.generate_parameter_updates(items)
        
        # Verify the pool ID is in the correct format for VPC templates
        pool_id = updates.get('tRegionalIPAMPoolId')
        assert pool_id is not None
        assert pool_id.startswith('ipam-pool-')
        
        # Verify it's a valid hex string after the prefix
        hex_part = pool_id.replace('ipam-pool-', '')
        try:
            int(hex_part, 16)
            valid_hex = True
        except ValueError:
            valid_hex = False
        
        assert valid_hex, f"Pool ID hex portion is not valid: {hex_part}"
        
        print(f"\nExtracted pool ID for VPC templates: {pool_id}")
        print(f"This will be used as tRegionalIPAMPoolId parameter in VPC CloudFormation templates")
