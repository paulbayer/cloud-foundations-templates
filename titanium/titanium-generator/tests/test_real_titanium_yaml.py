"""
Test IPAM pool ID extraction with the actual Titanium.yaml file.

This test verifies that the network processor correctly handles the real
Titanium YAML configuration from the project.
"""

import pytest
import yaml
from pathlib import Path
from titanium_generator.processors.network_processor import NetworkProcessor


class TestRealTitaniumYAML:
    """Tests using the actual Titanium.yaml file from the project."""
    
    def test_extract_from_real_titanium_yaml(self):
        """Test extraction of IPAM configuration from the real Titanium.yaml file."""
        # Load the actual Titanium.yaml file
        titanium_yaml_path = Path(__file__).parent.parent.parent / "Titanium.yaml"
        
        with open(titanium_yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Extract network section
        network_config = config.get('network', {})
        
        # Verify network configuration exists
        assert network_config is not None
        assert 'ipam' in network_config
        
        # Create processor and extract items
        processor = NetworkProcessor()
        items = processor.extract_items(network_config)
        
        # Verify IPAM item was extracted
        ipam_items = [item for item in items if item.get('type') == 'ipam']
        assert len(ipam_items) == 1
        
        ipam_item = ipam_items[0]
        assert ipam_item['enabled'] is True
        assert ipam_item['config']['region'] == 'us-east-1'
        
        # Generate parameter updates
        updates = processor.generate_parameter_updates(items)
        
        # Verify IPAM parameters
        assert updates['tDeployIPAM'] == 'true'
        assert updates['tIPAMRegion'] == 'us-east-1'
        assert updates['tGlobalIPAMPoolCIDR'] == '10.218.0.0/18'
        assert updates['tRegionalPoolCIDR'] == '10.218.0.0/19'
        
        # Note: The real Titanium.yaml doesn't have pool IDs yet
        # This is expected - pool IDs are generated after IPAM deployment
        # The parameter should not be present if no pool ID exists
        if 'tRegionalIPAMPoolId' in updates:
            # If it exists, verify it's a valid format
            pool_id = updates['tRegionalIPAMPoolId']
            assert pool_id.startswith('ipam-pool-')
        else:
            # This is the expected case for the current Titanium.yaml
            print("Note: No IPAM pool ID found in Titanium.yaml (expected for new deployments)")
    
    def test_network_architecture_extraction(self):
        """Test extraction of network architecture settings from real Titanium.yaml."""
        titanium_yaml_path = Path(__file__).parent.parent.parent / "Titanium.yaml"
        
        with open(titanium_yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        network_config = config.get('network', {})
        processor = NetworkProcessor()
        items = processor.extract_items(network_config)
        updates = processor.generate_parameter_updates(items)
        
        # Verify architecture type
        assert updates['tNetworkArchitectureType'] == 'TGW'
        
        # Verify Transit Gateway is enabled
        assert updates['tDeployTransitGateway'] == 'true'
        
        # Workload VPCs are no longer extracted or deployed (#87): their template
        # is never generated and workloadVpcs derives from a Control Tower
        # account-vending setting this solution does not act on.
        assert 'tDeployWorkloadVpcs' not in updates

        # Endpoint VPC should be disabled in the real config
        assert updates.get('tDeployEndpointVpc', 'false') == 'false'
        
        # Inspection VPC should be enabled in the real config
        assert updates['tDeployInspectionVpc'] == 'true'
        
        # Verify Route53 Resolver is enabled
        assert updates['tDeployHybridDNS'] == 'true'
        assert updates['tOnPremDomains'] == 'corp.example.com'
        assert updates['tOnPremDnsServers'] == '192.168.0.10,192.168.0.11'
    
    def test_ipam_pool_structure(self):
        """Test that IPAM pool structure is correctly parsed from real Titanium.yaml."""
        titanium_yaml_path = Path(__file__).parent.parent.parent / "Titanium.yaml"
        
        with open(titanium_yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        network_config = config.get('network', {})
        ipam_config = network_config.get('ipam', {})
        
        # Verify IPAM structure
        assert ipam_config['enabled'] is True
        assert ipam_config['region'] == 'us-east-1'
        assert 'us-east-1' in ipam_config['operatingRegions']
        
        # Verify pools
        pools = ipam_config.get('pools', [])
        assert len(pools) == 2
        
        # Verify global pool
        global_pool = next((p for p in pools if p['name'] == 'global-pool'), None)
        assert global_pool is not None
        assert '10.218.0.0/18' in global_pool['provisionedCidrs']
        
        # Verify regional pool
        regional_pool = next((p for p in pools if 'regional-pool' in p['name']), None)
        assert regional_pool is not None
        assert '10.218.0.0/19' in regional_pool['provisionedCidrs']
        assert regional_pool['locale'] == 'us-east-1'
        assert regional_pool['sourceIpamPool'] == 'global-pool'
        
        # Verify share targets
        assert 'shareTargets' in regional_pool
        assert 'organizationalUnits' in regional_pool['shareTargets']
        assert 'Infrastructure' in regional_pool['shareTargets']['organizationalUnits']
        assert 'Workloads' in regional_pool['shareTargets']['organizationalUnits']
    
    def test_default_vpc_deletion(self):
        """Test default VPC deletion configuration from real Titanium.yaml."""
        titanium_yaml_path = Path(__file__).parent.parent.parent / "Titanium.yaml"
        
        with open(titanium_yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        network_config = config.get('network', {})
        processor = NetworkProcessor()
        items = processor.extract_items(network_config)
        updates = processor.generate_parameter_updates(items)
        
        # Verify default VPC deletion is enabled
        assert updates['tDeployDefaultVpcDeletion'] == 'true'
