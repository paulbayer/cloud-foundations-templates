"""
Unit tests for OrganizationProcessor.

Deployment targets are no longer resolved at generation time (issue #75): OU IDs
only exist after the OUs are created at deploy time, so u<Policy>Targets is left
for the deployment guide to populate from SSM. These tests assert the processor
emits the deploy toggle + description and never emits target parameters.
"""

from titanium_generator.processors.organization_processor import SimpleOrganizationProcessor


class TestBackupPolicyParameterGeneration:
    """Tests for backup policy parameter generation functionality."""

    # Policy names must be the SINGULAR forms the backup template declares
    # (tDeployDailyBackup / tDeployWeeklyBackup / tDeployMonthlyBackup). A plural
    # name emits tDeployWeeklyBackups, which no-ops against the template (#97).
    def test_generate_backup_policy_parameters_enabled(self):
        processor = SimpleOrganizationProcessor()
        item = {
            "name": "WeeklyBackup",
            "type": "backup_policy",
            "enabled": True,
            "config": {"description": "Weekly backups with 90-day retention"},
        }

        parameters = processor._generate_policy_parameters(item)

        assert parameters["tDeployWeeklyBackup"] == "true"
        assert parameters["tWeeklyBackupDescription"] == "Weekly backups with 90-day retention"
        assert "uWeeklyBackupTargets" not in parameters

    def test_generate_backup_policy_parameters_disabled(self):
        processor = SimpleOrganizationProcessor()
        item = {
            "name": "DailyBackup",
            "type": "backup_policy",
            "enabled": False,
            "config": {"description": "Daily backups with 30-day retention"},
        }

        parameters = processor._generate_policy_parameters(item)

        assert parameters["tDeployDailyBackup"] == "false"
        assert parameters["tDailyBackupDescription"] == "Daily backups with 30-day retention"
        assert "uDailyBackupTargets" not in parameters

    def test_generate_backup_policy_parameters_no_description(self):
        processor = SimpleOrganizationProcessor()
        item = {
            "name": "WeeklyBackup",
            "type": "backup_policy",
            "enabled": True,
            "config": {},  # No description
        }

        parameters = processor._generate_policy_parameters(item)

        assert parameters["tDeployWeeklyBackup"] == "true"
        assert "tWeeklyBackupDescription" not in parameters
        assert "uWeeklyBackupTargets" not in parameters


class TestTaggingPolicyParameterGeneration:
    """Tests for tagging policy parameter generation functionality."""

    def test_generate_tagging_policy_parameters_enabled(self):
        processor = SimpleOrganizationProcessor()
        item = {
            "name": "RequiredTags",
            "type": "tagging_policy",
            "enabled": True,
            "config": {"description": "Required tags for all resources"},
        }

        parameters = processor._generate_policy_parameters(item)

        assert parameters["tDeployRequiredTags"] == "true"
        assert parameters["tRequiredTagsDescription"] == "Required tags for all resources"
        assert "uRequiredTagsTargets" not in parameters

    def test_generate_tagging_policy_parameters_disabled(self):
        processor = SimpleOrganizationProcessor()
        item = {
            "name": "OptionalTags",
            "type": "tagging_policy",
            "enabled": False,
            "config": {"description": "Optional tags with validation"},
        }

        parameters = processor._generate_policy_parameters(item)

        assert parameters["tDeployOptionalTags"] == "false"
        assert parameters["tOptionalTagsDescription"] == "Optional tags with validation"
        assert "uOptionalTagsTargets" not in parameters

    def test_generate_tagging_policy_parameters_no_description(self):
        processor = SimpleOrganizationProcessor()
        item = {
            "name": "RequiredTags",
            "type": "tagging_policy",
            "enabled": True,
            "config": {},  # No description
        }

        parameters = processor._generate_policy_parameters(item)

        assert parameters["tDeployRequiredTags"] == "true"
        assert "tRequiredTagsDescription" not in parameters
        assert "uRequiredTagsTargets" not in parameters


class TestGenerateParameterUpdatesIntegration:
    """Tests for generate_parameter_updates with backup, tagging, and SCP policies."""

    def test_generate_parameter_updates_backup_policy(self):
        processor = SimpleOrganizationProcessor()
        item = {
            "name": "WeeklyBackup",
            "type": "backup_policy",
            "enabled": True,
            "config": {"description": "Weekly backups with 90-day retention"},
        }

        parameters = processor.generate_parameter_updates([item])

        assert parameters["tDeployWeeklyBackup"] == "true"
        assert parameters["tWeeklyBackupDescription"] == "Weekly backups with 90-day retention"
        assert "uWeeklyBackupTargets" not in parameters

    def test_generate_parameter_updates_tagging_policy(self):
        processor = SimpleOrganizationProcessor()
        item = {
            "name": "RequiredTags",
            "type": "tagging_policy",
            "enabled": True,
            "config": {"description": "Required tags for all resources"},
        }

        parameters = processor.generate_parameter_updates([item])

        assert parameters["tDeployRequiredTags"] == "true"
        assert parameters["tRequiredTagsDescription"] == "Required tags for all resources"
        assert "uRequiredTagsTargets" not in parameters

    def test_generate_parameter_updates_scp_no_targets_or_orgid(self):
        """SCPs no longer emit u<Name>Targets (deploy-time) or OrganizationId from targets."""
        processor = SimpleOrganizationProcessor()
        item = {
            "name": "PreventLeaveOrganization",
            "type": "scp",
            "enabled": True,
            "config": {"deploymentTargets": {"organizationalUnits": ["Root"]}},
        }

        parameters = processor.generate_parameter_updates([item])

        assert "uPreventLeaveOrganizationTargets" not in parameters
        assert "OrganizationId" not in parameters


class TestExtractItemsWithPolicies:
    """Tests for extract_items — no target resolution, no resolved/original targets."""

    def test_extract_backup_policies(self):
        processor = SimpleOrganizationProcessor()
        section_config = {
            "backupPolicies": [
                {
                    "name": "WeeklyBackups",
                    "description": "Weekly backups with 90-day retention",
                    "enable": True,
                    "deploymentTargets": {"organizationalUnits": ["Workloads"]},
                }
            ]
        }

        items = processor.extract_items(section_config)

        assert len(items) == 1
        assert items[0]["name"] == "WeeklyBackups"
        assert items[0]["type"] == "backup_policy"
        assert items[0]["enabled"] is True
        assert "resolved_targets" not in items[0]
        assert "original_targets" not in items[0]

    def test_extract_tagging_policies(self):
        processor = SimpleOrganizationProcessor()
        section_config = {
            "taggingPolicies": [
                {
                    "name": "RequiredTags",
                    "description": "Required tags for all resources",
                    "deploymentTargets": {"organizationalUnits": ["Root"]},
                }
            ]
        }

        items = processor.extract_items(section_config)

        assert len(items) == 1
        assert items[0]["name"] == "RequiredTags"
        assert items[0]["type"] == "tagging_policy"
        assert items[0]["enabled"] is True
        assert "resolved_targets" not in items[0]

    def test_extract_mixed_policies(self):
        processor = SimpleOrganizationProcessor()
        section_config = {
            "serviceControlPolicies": [
                {"name": "DenyRootUser", "deploymentTargets": {"organizationalUnits": ["Workloads"]}}
            ],
            "backupPolicies": [
                {"name": "WeeklyBackups", "enable": True, "deploymentTargets": {"organizationalUnits": ["Workloads"]}}
            ],
            "taggingPolicies": [{"name": "RequiredTags", "deploymentTargets": {"organizationalUnits": ["Root"]}}],
        }

        items = processor.extract_items(section_config)

        assert len(items) == 3
        assert {item["type"] for item in items} == {"scp", "backup_policy", "tagging_policy"}
        assert {item["name"] for item in items} == {"DenyRootUser", "WeeklyBackups", "RequiredTags"}
