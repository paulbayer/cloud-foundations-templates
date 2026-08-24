"""
Tests for deploy-time policy target resolution in the LLM deployment guide
(issue #75).

The generator no longer resolves OU names to IDs; instead the guide turns each
u<Policy>Targets parameter into a ready-to-run value that looks up the OU ID from
SSM at deploy time (Root from .../root-id). These tests exercise that mapping and
value construction directly.
"""

from titanium_generator.mcp_tools.llm_agent_guide import LLMAgentGuideGenerator


def _generator_with_config(config):
    gen = LLMAgentGuideGenerator()
    gen._policy_targets = gen._build_policy_target_map(config)
    return gen


CONFIG = {
    "organization": {
        "serviceControlPolicies": [
            {"name": "PreventLeaveOrganization",
             "deploymentTargets": {"organizationalUnits": ["Root"]}},
        ],
        "taggingPolicies": [
            {"name": "RequiredTags",
             "deploymentTargets": {"organizationalUnits": ["Root"]}},
        ],
        "backupPolicies": [
            # Advisor name is plural; template param stem is singular.
            {"name": "DailyBackups",
             "deploymentTargets": {"organizationalUnits": ["Workloads"]}},
        ],
    }
}


def test_scp_root_target_resolves_to_root_id():
    gen = _generator_with_config(CONFIG)
    value = gen._resolve_targets_param_value("uPreventLeaveOrganizationTargets")
    assert value is not None
    assert "/titanium/organization/ou-ids/root-id" in value
    assert "aws ssm get-parameter" in value


def test_backup_target_resolves_to_ou_slug_despite_plural_mismatch():
    # Config policy 'DailyBackups' must match template param 'uDailyBackupTargets'.
    gen = _generator_with_config(CONFIG)
    value = gen._resolve_targets_param_value("uDailyBackupTargets")
    assert value is not None
    assert "/titanium/organization/ou-ids/workloads-ou-id" in value


def test_tagging_target_resolves():
    gen = _generator_with_config(CONFIG)
    value = gen._resolve_targets_param_value("uRequiredTagsTargets")
    assert value is not None
    assert "/titanium/organization/ou-ids/root-id" in value


def test_non_target_parameter_returns_none():
    gen = _generator_with_config(CONFIG)
    assert gen._resolve_targets_param_value("uOrganizationId") is None
    assert gen._resolve_targets_param_value("uLoggingAccountEmail") is None


def test_unknown_policy_returns_none():
    gen = _generator_with_config(CONFIG)
    # No such policy configured -> fall back to manual placeholder.
    assert gen._resolve_targets_param_value("uSomethingElseTargets") is None


def test_multiple_targets_are_comma_escaped():
    config = {
        "organization": {
            "backupPolicies": [
                {"name": "DevBackup",
                 "deploymentTargets": {"organizationalUnits": ["Development", "Sandbox"]}},
            ]
        }
    }
    gen = _generator_with_config(config)
    value = gen._resolve_targets_param_value("uDevBackupTargets")
    assert value is not None
    # Internal separator escaped so the CLI shorthand treats it as a list, not a
    # new key=value pair.
    assert "\\," in value
    assert "development-ou-id" in value
    assert "sandbox-ou-id" in value


def test_ou_ssm_slug_matches_processor_contract():
    # Must match SimpleOrganizationProcessor._ssm_slug.
    from titanium_generator.processors.organization_processor import (
        SimpleOrganizationProcessor,
    )
    for name in ["Workloads", "Log Archive", "Security-Prod", "Root"]:
        assert LLMAgentGuideGenerator._ou_ssm_slug(name) == SimpleOrganizationProcessor._ssm_slug(name)
