"""
Integration tests for backup and tagging policies.

Tests the complete workflow:
- Parse Titanium.yaml with backup/tagging policies
- Extract policy items from organization processor
- Modify templates with correct parameters
- Verify output matches expected structure
"""

import pytest
import tempfile
import shutil
import yaml
from pathlib import Path
from titanium_generator.config_parser import TitaniumConfigParser
from titanium_generator.processors.organization_processor import SimpleOrganizationProcessor  # noqa: F401
from titanium_generator.template_modifier import TemplateModifier  # noqa: F401
from titanium_generator.mcp_tools.process_templates import process_all_templates


def _cfn_yaml_load(stream):
    """Load YAML with CloudFormation intrinsic function tags."""
    loader = yaml.SafeLoader
    loader = type('CfnLoader', (loader,), {})
    cfn_tags = [
        'Ref', 'Condition', 'Equals', 'If', 'Not', 'And', 'Or',
        'GetAtt', 'Base64', 'Cidr', 'FindInMap', 'GetAZs',
        'ImportValue', 'Join', 'Select', 'Split', 'Sub',
        'Transform', 'Length', 'ToJsonString',
    ]
    for tag in cfn_tags:
        loader.add_constructor(f'!{tag}', lambda l, n: l.construct_sequence(n) if n.id == 'sequence' else l.construct_scalar(n))
    return yaml.load(stream, Loader=loader)


class TestBackupPoliciesIntegration:
    """Integration tests for backup policies workflow."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def backup_policies_config_path(self):
        """Path to test backup policies config."""
        return str(Path(__file__).parent / "test_data" / "test_backup_policies.yaml")

    def test_parse_backup_policies(self, backup_policies_config_path):
        """Test parsing Titanium.yaml with backup policies."""
        parser = TitaniumConfigParser()
        config = parser.parse_file(backup_policies_config_path)

        assert "organization" in config
        assert "backupPolicies" in config["organization"]
        assert len(config["organization"]["backupPolicies"]) == 2

        # Verify first policy
        daily_backup = config["organization"]["backupPolicies"][0]
        assert daily_backup["name"] == "DailyBackup"
        assert daily_backup["description"] == "Daily backups with 30-day retention"
        assert "policy" in daily_backup
        assert "deploymentTargets" in daily_backup
        assert daily_backup["deploymentTargets"]["organizationalUnits"] == ["Workloads"]

        # Verify second policy
        weekly_backup = config["organization"]["backupPolicies"][1]
        assert weekly_backup["name"] == "WeeklyBackup"
        assert weekly_backup["description"] == "Weekly backups with 90-day retention"
        assert weekly_backup["deploymentTargets"]["organizationalUnits"] == ["Security"]

    def test_extract_backup_policies(self, backup_policies_config_path):
        """Test extracting backup policy items from organization processor."""
        parser = TitaniumConfigParser()
        config = parser.parse_file(backup_policies_config_path)

        processor = SimpleOrganizationProcessor()
        org_config = config["organization"]
        items = processor.extract_items(org_config)

        # Filter backup policy items
        backup_items = [item for item in items if item["type"] == "backup_policy"]
        assert len(backup_items) == 2

        # Verify DailyBackup item
        daily_item = next(item for item in backup_items if item["name"] == "DailyBackup")
        assert daily_item["enabled"] is True
        assert "config" in daily_item
        assert daily_item["config"]["description"] == "Daily backups with 30-day retention"
        # Targets are no longer resolved at generation time (issue #75); the raw
        # intent stays on config.deploymentTargets for the deployment guide.
        assert "resolved_targets" not in daily_item
        assert "original_targets" not in daily_item
        assert daily_item["config"]["deploymentTargets"]["organizationalUnits"] == ["Workloads"]

    def test_generate_backup_policy_parameters(self, backup_policies_config_path):
        """Test parameter generation for backup policies."""
        parser = TitaniumConfigParser()
        config = parser.parse_file(backup_policies_config_path)

        processor = SimpleOrganizationProcessor()
        org_config = config["organization"]
        items = processor.extract_items(org_config)

        backup_items = [item for item in items if item["type"] == "backup_policy"]
        daily_item = next(item for item in backup_items if item["name"] == "DailyBackup")

        parameters = processor.generate_parameter_updates([daily_item])

        # Verify parameter names follow convention
        assert "tDeployDailyBackup" in parameters
        assert parameters["tDeployDailyBackup"] == "true"

        assert "tDailyBackupDescription" in parameters
        assert parameters["tDailyBackupDescription"] == "Daily backups with 30-day retention"

    def test_end_to_end_backup_policies(self, backup_policies_config_path, temp_output_dir):
        """Test complete end-to-end flow for backup policies."""
        result = process_all_templates(backup_policies_config_path, temp_output_dir, sections=["organization"])

        assert result["success"] is True

        # Verify backup policies template was generated
        backup_template_path = (
            Path(temp_output_dir) / "organization" / "03-organizations-stack-mgmt-backup-policies.yaml"
        )
        assert backup_template_path.exists(), "Backup policies template should be generated"

        # Load and verify template content
        with open(backup_template_path, "r") as f:
            template = _cfn_yaml_load(f)

        # Verify parameters exist
        assert "Parameters" in template
        params = template["Parameters"]

        # Check DailyBackup parameters
        assert "tDeployDailyBackup" in params
        assert str(params["tDeployDailyBackup"]["Default"]).lower() == "true"

        assert "tDailyBackupDescription" in params
        assert params["tDailyBackupDescription"]["Default"] == "Daily backups with 30-day retention"

        assert "uDailyBackupTargets" in params

        # Check WeeklyBackup parameters
        assert "tDeployWeeklyBackup" in params
        assert str(params["tDeployWeeklyBackup"]["Default"]).lower() == "true"

        assert "tWeeklyBackupDescription" in params
        assert params["tWeeklyBackupDescription"]["Default"] == "Weekly backups with 90-day retention"


class TestTaggingPoliciesIntegration:
    """Integration tests for tagging policies workflow."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def tagging_policies_config_path(self):
        """Path to test tagging policies config."""
        return str(Path(__file__).parent / "test_data" / "test_tagging_policies.yaml")

    def test_parse_tagging_policies(self, tagging_policies_config_path):
        """Test parsing Titanium.yaml with tagging policies."""
        parser = TitaniumConfigParser()
        config = parser.parse_file(tagging_policies_config_path)

        assert "organization" in config
        assert "taggingPolicies" in config["organization"]
        assert len(config["organization"]["taggingPolicies"]) == 2

        # Verify first policy
        required_tags = config["organization"]["taggingPolicies"][0]
        assert required_tags["name"] == "RequiredTags"
        assert required_tags["description"] == "Required tags for all resources"
        assert "policy" in required_tags
        assert required_tags["deploymentTargets"]["organizationalUnits"] == ["Root"]

        # Verify second policy
        cost_center = config["organization"]["taggingPolicies"][1]
        assert cost_center["name"] == "CostCenterTags"
        assert cost_center["deploymentTargets"]["organizationalUnits"] == ["Workloads"]

    def test_extract_tagging_policies(self, tagging_policies_config_path):
        """Test extracting tagging policy items from organization processor."""
        parser = TitaniumConfigParser()
        config = parser.parse_file(tagging_policies_config_path)

        processor = SimpleOrganizationProcessor()
        org_config = config["organization"]
        items = processor.extract_items(org_config)

        # Filter tagging policy items
        tagging_items = [item for item in items if item["type"] == "tagging_policy"]
        assert len(tagging_items) == 2

        # Verify RequiredTags item
        required_item = next(item for item in tagging_items if item["name"] == "RequiredTags")
        assert required_item["enabled"] is True
        assert required_item["config"]["description"] == "Required tags for all resources"
        assert required_item["config"]["deploymentTargets"]["organizationalUnits"] == ["Root"]

    def test_generate_tagging_policy_parameters(self, tagging_policies_config_path):
        """Test parameter generation for tagging policies."""
        parser = TitaniumConfigParser()
        config = parser.parse_file(tagging_policies_config_path)

        processor = SimpleOrganizationProcessor()
        org_config = config["organization"]
        items = processor.extract_items(org_config)

        tagging_items = [item for item in items if item["type"] == "tagging_policy"]
        required_item = next(item for item in tagging_items if item["name"] == "RequiredTags")

        parameters = processor.generate_parameter_updates([required_item])

        # Verify parameter names follow convention
        assert "tDeployRequiredTags" in parameters
        assert parameters["tDeployRequiredTags"] == "true"

        assert "tRequiredTagsDescription" in parameters
        assert parameters["tRequiredTagsDescription"] == "Required tags for all resources"

    @pytest.mark.xfail(reason="Template parameters are static; dynamic policy names not yet supported")
    def test_end_to_end_tagging_policies(self, tagging_policies_config_path, temp_output_dir):
        """Test complete end-to-end flow for tagging policies."""
        result = process_all_templates(tagging_policies_config_path, temp_output_dir, sections=["organization"])

        assert result["success"] is True

        # Verify tagging policies template was generated
        tagging_template_path = (
            Path(temp_output_dir) / "organization" / "04-organizations-stack-mgmt-tagging-policies.yaml"
        )
        assert tagging_template_path.exists(), "Tagging policies template should be generated"

        # Load and verify template content
        with open(tagging_template_path, "r") as f:
            template = _cfn_yaml_load(f)

        # Verify parameters exist
        assert "Parameters" in template
        params = template["Parameters"]

        # Check RequiredTags parameters
        assert "tDeployRequiredTags" in params
        assert str(params["tDeployRequiredTags"]["Default"]).lower() == "true"

        assert "tRequiredTagsDescription" in params
        assert params["tRequiredTagsDescription"]["Default"] == "Required tags for all resources"

        assert "uRequiredTagsTargets" in params

        # Check CostCenterTags parameters
        assert "tDeployCostCenterTags" in params
        assert str(params["tDeployCostCenterTags"]["Default"]).lower() == "true"


class TestMultiplePoliciesIntegration:
    """Integration tests for multiple policies of the same type."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def multiple_backup_policies_config(self, tmp_path):
        """Create config with multiple backup policies."""
        config_content = """
organizationName: TestOrg
domain: example.com
homeRegion: us-east-1
enabledRegions:
  - us-east-1

organization:
  organizationalUnits:
    - name: Workloads
      parent: Root
    - name: Security
      parent: Root
    - name: Infrastructure
      parent: Root

  backupPolicies:
    - name: DailyBackup
      description: Daily backups
      policy: '{"plans": {}}'
      deploymentTargets:
        organizationalUnits: [Workloads]

    - name: WeeklyBackup
      description: Weekly backups
      policy: '{"plans": {}}'
      deploymentTargets:
        organizationalUnits: [Security]

    - name: MonthlyBackup
      description: Monthly backups
      policy: '{"plans": {}}'
      deploymentTargets:
        organizationalUnits: [Infrastructure]
"""
        config_file = tmp_path / "multiple_backups.yaml"
        config_file.write_text(config_content)
        return str(config_file)

    def test_multiple_backup_policies(self, multiple_backup_policies_config, temp_output_dir):
        """Test handling multiple backup policies."""
        result = process_all_templates(multiple_backup_policies_config, temp_output_dir, sections=["organization"])

        assert result["success"] is True

        # Load template
        backup_template_path = (
            Path(temp_output_dir) / "organization" / "03-organizations-stack-mgmt-backup-policies.yaml"
        )
        assert backup_template_path.exists()

        with open(backup_template_path, "r") as f:
            template = _cfn_yaml_load(f)

        params = template["Parameters"]

        # Verify all three policies have parameters
        assert "tDeployDailyBackup" in params
        assert "tDeployWeeklyBackup" in params
        assert "tDeployMonthlyBackup" in params

        assert "tDailyBackupDescription" in params
        assert "tWeeklyBackupDescription" in params
        assert "tMonthlyBackupDescription" in params

        assert "uDailyBackupTargets" in params
        assert "uWeeklyBackupTargets" in params
        assert "uMonthlyBackupTargets" in params


class TestDifferentOUTargetsIntegration:
    """Integration tests for policies targeting different OUs."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def different_ou_targets_config(self, tmp_path):
        """Create config with policies targeting different OUs."""
        config_content = """
organizationName: TestOrg
domain: example.com
homeRegion: us-east-1
enabledRegions:
  - us-east-1

organization:
  organizationalUnits:
    - name: Production
      parent: Root
    - name: Development
      parent: Root
    - name: Sandbox
      parent: Root

  backupPolicies:
    - name: ProductionBackup
      description: Production backup policy
      policy: '{"plans": {}}'
      deploymentTargets:
        organizationalUnits: [Production]

    - name: DevBackup
      description: Development backup policy
      policy: '{"plans": {}}'
      deploymentTargets:
        organizationalUnits: [Development, Sandbox]

  taggingPolicies:
    - name: ProductionTags
      description: Production tagging policy
      policy: '{"tags": {}}'
      deploymentTargets:
        organizationalUnits: [Production]

    - name: AllEnvironmentTags
      description: Tags for all environments
      policy: '{"tags": {}}'
      deploymentTargets:
        organizationalUnits: [Root]
"""
        config_file = tmp_path / "different_ous.yaml"
        config_file.write_text(config_content)
        return str(config_file)

    @pytest.mark.xfail(reason="Template parameters are static; dynamic policy names not yet supported")
    def test_policies_with_different_ou_targets(self, different_ou_targets_config, temp_output_dir):
        """Test policies targeting different OUs."""
        result = process_all_templates(different_ou_targets_config, temp_output_dir, sections=["organization"])

        assert result["success"] is True

        # Verify backup policies template
        backup_template_path = (
            Path(temp_output_dir) / "organization" / "03-organizations-stack-mgmt-backup-policies.yaml"
        )
        assert backup_template_path.exists()

        with open(backup_template_path, "r") as f:
            backup_template = _cfn_yaml_load(f)

        # Verify ProductionBackup targets single OU
        assert "uProductionBackupTargets" in backup_template["Parameters"]

        # Verify DevBackup targets multiple OUs
        assert "uDevBackupTargets" in backup_template["Parameters"]

        # Verify tagging policies template
        tagging_template_path = (
            Path(temp_output_dir) / "organization" / "04-organizations-stack-mgmt-tagging-policies.yaml"
        )
        assert tagging_template_path.exists()

        with open(tagging_template_path, "r") as f:
            tagging_template = _cfn_yaml_load(f)

        # Verify ProductionTags targets single OU
        assert "uProductionTagsTargets" in tagging_template["Parameters"]

        # Verify AllEnvironmentTags targets Root
        assert "uAllEnvironmentTagsTargets" in tagging_template["Parameters"]

    def test_parameter_extraction_for_different_targets(self, different_ou_targets_config):
        """Test parameter extraction handles different OU targets correctly."""
        parser = TitaniumConfigParser()
        config = parser.parse_file(different_ou_targets_config)

        processor = SimpleOrganizationProcessor()
        org_config = config["organization"]
        items = processor.extract_items(org_config)

        # Find DevBackup with multiple targets
        backup_items = [item for item in items if item["type"] == "backup_policy"]
        dev_backup = next(item for item in backup_items if item["name"] == "DevBackup")

        # Target intent stays on config.deploymentTargets (resolved at deploy time, #75)
        assert dev_backup["config"]["deploymentTargets"]["organizationalUnits"] == ["Development", "Sandbox"]

        # Find AllEnvironmentTags targeting Root
        tagging_items = [item for item in items if item["type"] == "tagging_policy"]
        all_env_tags = next(item for item in tagging_items if item["name"] == "AllEnvironmentTags")

        assert all_env_tags["config"]["deploymentTargets"]["organizationalUnits"] == ["Root"]


class TestMixedPoliciesIntegration:
    """Integration tests for mixed backup and tagging policies."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mixed_policies_config(self, tmp_path):
        """Create config with both backup and tagging policies."""
        config_content = """
organizationName: TestOrg
domain: example.com
homeRegion: us-east-1
enabledRegions:
  - us-east-1

organization:
  organizationalUnits:
    - name: Workloads
      parent: Root

  backupPolicies:
    - name: StandardBackup
      description: Standard backup policy
      policy: '{"plans": {}}'
      deploymentTargets:
        organizationalUnits: [Workloads]

  taggingPolicies:
    - name: StandardTags
      description: Standard tagging policy
      policy: '{"tags": {}}'
      deploymentTargets:
        organizationalUnits: [Workloads]
"""
        config_file = tmp_path / "mixed_policies.yaml"
        config_file.write_text(config_content)
        return str(config_file)

    @pytest.mark.xfail(reason="Template parameters are static; dynamic policy names not yet supported")
    def test_mixed_backup_and_tagging_policies(self, mixed_policies_config, temp_output_dir):
        """Test processing both backup and tagging policies together."""
        result = process_all_templates(mixed_policies_config, temp_output_dir, sections=["organization"])

        assert result["success"] is True

        # Verify both templates generated
        backup_template_path = (
            Path(temp_output_dir) / "organization" / "03-organizations-stack-mgmt-backup-policies.yaml"
        )
        tagging_template_path = (
            Path(temp_output_dir) / "organization" / "04-organizations-stack-mgmt-tagging-policies.yaml"
        )

        assert backup_template_path.exists(), "Backup policies template should be generated"
        assert tagging_template_path.exists(), "Tagging policies template should be generated"

        # Verify backup template has correct parameters
        with open(backup_template_path, "r") as f:
            backup_template = _cfn_yaml_load(f)

        assert "tDeployStandardBackup" in backup_template["Parameters"]
        assert "tStandardBackupDescription" in backup_template["Parameters"]

        # Verify tagging template has correct parameters
        with open(tagging_template_path, "r") as f:
            tagging_template = _cfn_yaml_load(f)

        assert "tDeployStandardTags" in tagging_template["Parameters"]
        assert "tStandardTagsDescription" in tagging_template["Parameters"]
