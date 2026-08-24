"""
Tests for full verbose Titanium.yaml configuration format (issue #13).

Verifies that the generator correctly handles configs where ALL sections
are present with disabled features marked as enabled: false / enable: false,
rather than being omitted entirely.
"""

import pytest
import tempfile
import shutil
import yaml
from pathlib import Path
from titanium_generator.config_parser import TitaniumConfigParser
from titanium_generator.processors.network_processor import NetworkProcessor
from titanium_generator.mcp_tools.process_templates import process_all_templates


FULL_VERBOSE_MINIMAL_CONFIG = """
homeRegion: us-east-1
enabledRegions:
  - us-east-1
managementAccountAccessRole: AWSControlTowerExecution

controlTower:
  enable: true
  landingZone:
    version: '4.0'
    logging:
      controlTowerOrganizationTrail: true
      loggingBucketRetentionDays: 365
      accessLoggingBucketRetentionDays: 3650
      organizationTrail: true
    security:
      enableIdentityCenterAccess: false
      denyRegion: true
    network:
      networkFactoryConfiguration: null

organization:
  enable: true
  organizationalUnits:
    - name: Security
    - name: Infrastructure
    - name: Workloads
    - name: Sandbox
  serviceControlPolicies:
    - name: PreventLeaveOrganization
      description: Prevents accounts from leaving the organization
      policy: service-control-policies/prevent-leave-org.json
      type: customerManaged
      deploymentTargets:
        organizationalUnits:
          - Root
  taggingPolicies: []
  backupPolicies:
    - name: DailyBackups
      enable: false
      description: Daily backups with 30-day retention
      policy: backup-policies/daily-backups.json
      deploymentTargets:
        organizationalUnits:
          - Workloads
  resourceControlPolicies: []

accounts:
  mandatoryAccounts:
    - name: Management
      email: management@example.com
      organizationalUnit: Root
    - name: LogArchive
      email: log-archive@example.com
      organizationalUnit: Security
    - name: Audit
      email: audit@example.com
      organizationalUnit: Security
  infrastructureAccounts: []

network:
  architectureType: TGW
  defaultVpc:
    delete: true
    excludeAccounts: []
  tgwArchitecture:
    networkAccount: Network
    region: us-east-1
    vpcs:
      endpointVpc:
        enabled: false
      inspectionVpc:
        enabled: false
        availabilityZones: 2
        networkFirewall: false
        firewallLogging: false
  workloadVpcs:
    enabled: false
    availabilityZones: 2
    subnetsPerAZ: 2
    deploymentTargets:
      organizational_units:
        - Workloads
      accounts: []
  hybridConnectivity:
    enabled: false
    type: DirectConnect
  ipam:
    enabled: false
    region: us-east-1
    operatingRegions:
      - us-east-1
    pools:
      - name: global-pool
        provisionedCidrs:
          - 10.100.0.0/16
      - name: regional-pool-us-east-1
        locale: us-east-1
        sourceIpamPool: global-pool
        provisionedCidrs:
          - 10.100.0.0/17
        shareTargets:
          organizationalUnits:
            - Infrastructure
            - Workloads

vpcFlowLogs:
  trafficType: ALL
  accounts: []
  regions:
    - us-east-1
  maxAggregationInterval: 600
  destinations:
    - s3
  destinationsConfig:
    s3:
      bucketName: vpc-flow-logs-example
  defaultFormat: false

centralSecurityServices:
  delegatedAdminAccount: Audit
  guardduty:
    enable: true
    excludeRegions: []
    s3Protection:
      enable: false
  macie:
    enable: false
  detective:
    enable: false
  securityHub:
    enable: true
    regionAggregation: false
    excludeRegions: []
    standards:
      - name: AWS Foundational Security Best Practices v1.0.0
        enable: true
      - name: CIS AWS Foundations Benchmark v1.4.0
        enable: false

cloudFinancialManagement:
  budgets:
    - deploymentTargets:
        accounts:
          - Management
      name: example-monthly-budget
      timeUnit: MONTHLY
      type: COST
      amount: 2000
      unit: USD
      notifications:
        - type: ACTUAL
          threshold: 80
          thresholdType: PERCENTAGE
          comparisonOperator: GREATER_THAN
          subscriberEmailAddresses:
            - budget-alerts@example.com
  computeOptimizer:
    enable: true
  costOptimizationHub:
    enable: true
"""


class TestFullVerboseConfig:
    """Tests for full verbose config format with disabled sections."""

    @pytest.fixture
    def temp_output_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def minimal_config_path(self, tmp_path):
        config_file = tmp_path / "minimal_verbose.yaml"
        config_file.write_text(FULL_VERBOSE_MINIMAL_CONFIG)
        return str(config_file)

    def test_parser_accepts_full_verbose_format(self, minimal_config_path):
        """Full verbose config with disabled sections should parse without error."""
        parser = TitaniumConfigParser()
        config = parser.parse_file(minimal_config_path)

        assert "network" in config
        assert "organization" in config
        assert "controlTower" in config
        assert "centralSecurityServices" in config
        assert "cloudFinancialManagement" in config
        assert "vpcFlowLogs" in config

    def test_disabled_network_sections_present(self, minimal_config_path):
        """Disabled network sub-sections should be present but flagged disabled."""
        parser = TitaniumConfigParser()
        config = parser.parse_file(minimal_config_path)
        network = config["network"]

        assert network["tgwArchitecture"]["vpcs"]["endpointVpc"]["enabled"] is False
        assert network["tgwArchitecture"]["vpcs"]["inspectionVpc"]["enabled"] is False
        assert network["hybridConnectivity"]["enabled"] is False
        assert network["ipam"]["enabled"] is False
        assert network["workloadVpcs"]["enabled"] is False

    def test_network_processor_handles_all_disabled(self, minimal_config_path):
        """Network processor should handle config with all sub-features disabled."""
        parser = TitaniumConfigParser()
        config = parser.parse_file(minimal_config_path)
        network = config["network"]

        processor = NetworkProcessor()
        items = processor.extract_items(network)

        # No TGW item (transitGateway key absent)
        tgw_items = [i for i in items if i["type"] == "transit_gateway"]
        assert len(tgw_items) == 0

        # No VPCs enabled
        vpc_items = [i for i in items if i["type"] in ("endpoint_vpc", "inspection_vpc")]
        assert len(vpc_items) == 0

        # No hybrid connectivity
        hybrid_items = [i for i in items if i["type"] == "hybrid_connectivity"]
        assert len(hybrid_items) == 0

        # No IPAM items extracted (no advanced path without transitGateway)
        ipam_items = [i for i in items if i["type"] == "ipam"]
        assert len(ipam_items) == 0

    def test_network_processor_minimal_only_handles_default_vpc(self, minimal_config_path):
        """Minimal config (no TGW) should only process default VPC deletion."""
        parser = TitaniumConfigParser()
        config = parser.parse_file(minimal_config_path)
        network = config["network"]

        processor = NetworkProcessor()
        items = processor.extract_items(network)

        # Only default VPC deletion should be extracted
        assert len(items) == 1
        assert items[0]["type"] == "default_vpc"

    def test_disabled_backup_policy_extracted(self, minimal_config_path):
        """Disabled backup policy should be extractable with enable=false."""
        parser = TitaniumConfigParser()
        config = parser.parse_file(minimal_config_path)

        from titanium_generator.processors.organization_processor import SimpleOrganizationProcessor
        processor = SimpleOrganizationProcessor()
        org_config = config["organization"]
        items = processor.extract_items(org_config)

        backup_items = [i for i in items if i["type"] == "backup_policy"]
        assert len(backup_items) == 1
        assert backup_items[0]["name"] == "DailyBackups"
        assert backup_items[0]["enabled"] is False

    def test_process_all_templates_with_minimal_verbose(self, minimal_config_path, temp_output_dir):
        """Generator should successfully process a full verbose config with disabled features."""
        result = process_all_templates(minimal_config_path, temp_output_dir)

        assert result["success"] is True
        assert result["summary"]["failed_modifications"] == 0

    def test_has_advanced_network_features_all_disabled(self):
        """Config with all sub-features explicitly disabled should not trigger advanced path."""
        config = {
            "tgwArchitecture": {
                "vpcs": {
                    "endpointVpc": {"enabled": False},
                    "inspectionVpc": {"enabled": False}
                }
            },
            "ipam": {"enabled": False},
            "hybridConnectivity": {"enabled": False},
            "workloadVpcs": {"enabled": False}
        }
        assert NetworkProcessor.has_advanced_network_features(config) is False

    def test_has_advanced_network_features_truly_minimal(self):
        """Truly minimal config with no advanced sections should return False."""
        config = {
            "defaultVpc": {"delete": True}
        }
        assert NetworkProcessor.has_advanced_network_features(config) is False
