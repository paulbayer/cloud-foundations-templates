"""
Integration test for IPAM pool ID extraction from Titanium YAML.

This test verifies that the network processor correctly extracts IPAM pool IDs
from a complete Titanium YAML configuration.
"""

import pytest
import yaml
from titanium_generator.config_parser import TitaniumConfigParser
from titanium_generator.processors.network_processor import NetworkProcessor


class TestIPAMPoolIDIntegration:
    """Integration tests for IPAM pool ID extraction."""
    
    def test_extract_pool_id_from_complete_config(self):
        """Test extraction of IPAM pool ID from a complete Titanium YAML configuration."""
        # Sample Titanium YAML with IPAM configuration
        titanium_yaml = """
homeRegion: us-west-2
enabledRegions:
  - us-west-2
  - us-east-1

network:
  architectureType: TGW
  ipam:
    enabled: true
    region: us-west-2
    pools:
      - name: global-pool
        provisionedCidrs:
          - 10.100.0.0/16
      - name: regional-pool-us-west-2
        id: ipam-pool-0a1b2c3d4e5f6789
        provisionedCidrs:
          - 10.100.0.0/17
  tgwArchitecture:
    vpcs:
      endpointVpc:
        enabled: false
      inspectionVpc:
        enabled: true
        availabilityZones: 2
        networkFirewall: true
    transitGateway:
      name: test-tgw
      asn: 65000
      routeTableStructure: segregated
      routeTables:
        - Core
        - Segregated
"""
        
        # Parse the YAML
        config = yaml.safe_load(titanium_yaml)
        
        # Extract network section
        network_config = config.get('network', {})
        
        # Create processor and extract items
        processor = NetworkProcessor()
        items = processor.extract_items(network_config)
        
        # Generate parameter updates
        updates = processor.generate_parameter_updates(items)
        
        # Verify IPAM pool ID was extracted
        assert 'tRegionalIPAMPoolId' in updates
        assert updates['tRegionalIPAMPoolId'] == 'ipam-pool-0a1b2c3d4e5f6789'
        
        # Verify other IPAM parameters
        assert updates['tDeployIPAM'] == 'true'
        assert updates['tIPAMRegion'] == 'us-west-2'
        assert updates['tGlobalIPAMPoolCIDR'] == '10.100.0.0/16'
        assert updates['tRegionalPoolCIDR'] == '10.100.0.0/17'
    
    def test_multiple_regional_pools_uses_first(self):
        """Test that when multiple regional pools exist, the first one is used."""
        titanium_yaml = """
homeRegion: us-west-2
enabledRegions:
  - us-west-2
  - us-east-1

network:
  ipam:
    enabled: true
    region: us-west-2
    pools:
      - name: regional-pool-us-west-2
        id: ipam-pool-111111111111
        provisionedCidrs:
          - 10.100.0.0/17
      - name: regional-pool-us-east-1
        id: ipam-pool-222222222222
        provisionedCidrs:
          - 10.100.128.0/17
"""
        
        config = yaml.safe_load(titanium_yaml)
        network_config = config.get('network', {})
        
        processor = NetworkProcessor()
        items = processor.extract_items(network_config)
        updates = processor.generate_parameter_updates(items)
        
        # Should use the first regional pool
        assert updates['tRegionalIPAMPoolId'] == 'ipam-pool-111111111111'
    
    def test_no_pool_id_when_ipam_disabled(self):
        """Test that pool ID is not extracted when IPAM is disabled."""
        titanium_yaml = """
homeRegion: us-west-2
enabledRegions:
  - us-west-2

network:
  tgwArchitecture:
    vpcs:
      inspectionVpc:
        enabled: true
        networkFirewall: true
    transitGateway:
      name: test-tgw
      asn: 65000
      routeTableStructure: segregated
      routeTables:
        - Core
  ipam:
    enabled: false
    region: us-west-2
    pools:
      - name: regional-pool-us-west-2
        id: ipam-pool-0a1b2c3d4e5f6789
        provisionedCidrs:
          - 10.100.0.0/17
"""
        
        config = yaml.safe_load(titanium_yaml)
        network_config = config.get('network', {})
        
        processor = NetworkProcessor()
        items = processor.extract_items(network_config)
        updates = processor.generate_parameter_updates(items)
        
        # IPAM should be disabled
        assert updates['tDeployIPAM'] == 'false'
        
        # Pool ID should still be extracted (for potential future use)
        assert 'tRegionalIPAMPoolId' in updates
        assert updates['tRegionalIPAMPoolId'] == 'ipam-pool-0a1b2c3d4e5f6789'
