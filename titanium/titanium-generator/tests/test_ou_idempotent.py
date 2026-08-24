"""
Tests for #78: the OU template must be idempotent (adopt-or-create).

On a Control-Tower-managed or previously-configured org the OUs
(Infrastructure/Workloads/Sandbox/Exceptions) commonly already exist, so an
unconditional AWS::Organizations::OrganizationalUnit create fails with
DuplicateOrganizationalUnitException. The generator now provisions OUs through
the discovery Lambda (adopt existing by name, else create) and references the
returned IDs, so no native OU resources are emitted.
"""

from pathlib import Path

import titanium_generator
from titanium_generator.processors.organization_processor import (
    SimpleOrganizationProcessor,
)

OU_TEMPLATE = (
    Path(titanium_generator.__file__).parent
    / "mcp_tools" / "templates" / "organization"
    / "01-organizations-stack-mgmt-ous.yaml"
)


def _template_text():
    return OU_TEMPLATE.read_text()


class TestShippedTemplateAdoptsExistingOus:
    """The static template carries the adopt-or-create Lambda + inputs."""

    def test_lambda_adopts_or_creates(self):
        text = _template_text()
        assert "def adopt_or_create_ou(" in text
        # Adopting means listing first and only creating when absent.
        assert "list_organizational_units_for_parent" in text
        assert "create_organizational_unit" in text

    def test_role_can_create_ous(self):
        text = _template_text()
        assert "organizations:CreateOrganizationalUnit" in text

    def test_custom_resource_takes_ou_list(self):
        text = _template_text()
        assert "OrganizationalUnits: []" in text  # empty default in shipped template
        assert "generated-ou-list" in text


class TestGeneratedOuWiring:
    """With OUs configured, the injected block adopts-or-creates them."""

    def _inject(self, ou_names):
        processor = SimpleOrganizationProcessor()
        processor.set_full_config(
            {"controlTower": {"landingZone": {"security": {"name": "Security"}}}}
        )
        section = {"organizationalUnits": [{"name": n} for n in ou_names]}
        rendered, _ = processor._inject_organizational_units(_template_text(), section)
        return rendered

    def test_no_native_ou_resources_emitted(self):
        rendered = self._inject(["Infrastructure", "Workloads"])
        # OUs are adopted-or-created by the Lambda, never as native resources.
        assert "AWS::Organizations::OrganizationalUnit" not in rendered

    def test_ou_list_injected_into_custom_resource(self):
        rendered = self._inject(["Infrastructure", "Workloads"])
        assert "- Name: 'Infrastructure'" in rendered
        assert "LogicalId: 'Infrastructure'" in rendered
        assert "- Name: 'Workloads'" in rendered

    def test_no_native_enabled_baseline_resources(self):
        # #91: baseline enrollment moved into the discovery Lambda; the generator
        # must not emit non-idempotent AWS::ControlTower::EnabledBaseline resources.
        rendered = self._inject(["Workloads"])
        # No baseline resource is declared (comments referencing the type by name
        # are fine — they explain the absence).
        assert "Type: AWS::ControlTower::EnabledBaseline" not in rendered
        assert "WorkloadsOuBaseline:" not in rendered

    def test_output_resolves_lambda_returned_id(self):
        rendered = self._inject(["Workloads"])
        # The per-OU output still resolves the adopted-or-created OU ID.
        assert "!GetAtt OrganizationRootDiscovery.WorkloadsOuId" in rendered

    def test_hub_ou_excluded_from_provisioning(self):
        # 'Security' is the Control Tower hub OU; it is discovered, not provisioned.
        rendered = self._inject(["Infrastructure", "Security"])
        assert "- Name: 'Infrastructure'" in rendered
        assert "- Name: 'Security'" not in rendered

    def test_no_ous_configured_is_discovery_only(self):
        rendered = self._inject([])
        # Empty OU list => the Lambda performs discovery only, no enrollment.
        assert "OrganizationalUnits: []" in rendered
        assert "Type: AWS::ControlTower::EnabledBaseline" not in rendered


class TestLambdaManagedBaselineEnrollment:
    """#91: the discovery Lambda enrolls OUs idempotently (adopt-or-enable)."""

    def test_lambda_adopts_already_enrolled_ous(self):
        text = _template_text()
        # Detects existing enrollment (adopt) before attempting a create.
        assert "def get_enabled_baseline(" in text
        assert "list_enabled_baselines" in text
        assert "targetIdentifiers" in text

    def test_lambda_fires_enable_baseline(self):
        text = _template_text()
        assert "def enroll_ou_baseline(" in text
        assert "enable_baseline(" in text

    def test_role_can_enable_baseline(self):
        text = _template_text()
        assert "controltower:EnableBaseline" in text

    def test_custom_resource_passes_baseline_config(self):
        text = _template_text()
        assert "BaselineArn: !Sub" in text
        assert "BaselineVersion:" in text

    def test_template_baseline_matches_generator_constants(self):
        # The template's static baseline id/version must not drift from the
        # generator's canonical constants.
        text = _template_text()
        assert SimpleOrganizationProcessor.CONTROL_TOWER_BASELINE_ID in text
        assert (
            f"BaselineVersion: '{SimpleOrganizationProcessor.CONTROL_TOWER_BASELINE_VERSION}'"
            in text
        )


class TestSerializedBaselineEnrollment:
    """#114: baseline enrollment is serialized/retried and FAILED baselines re-attempted."""

    def test_role_can_poll_and_reset_baselines(self):
        text = _template_text()
        assert "controltower:GetBaselineOperation" in text
        assert "controltower:ResetEnabledBaseline" in text

    def test_handler_waits_for_each_baseline_operation(self):
        # Serialize: poll get_baseline_operation until terminal before the next OU.
        text = _template_text()
        assert "def wait_for_baseline_operation(" in text
        assert "get_baseline_operation(" in text

    def test_handler_retries_conflict_exception(self):
        # Concurrent baseline ops raise ConflictException; the start is retried.
        text = _template_text()
        assert "def start_baseline_op(" in text
        assert "ConflictException" in text

    def test_failed_baseline_is_reset_not_adopted(self):
        # A FAILED EnabledBaseline must be re-attempted (reset), not adopted as done.
        text = _template_text()
        assert "reset_enabled_baseline(" in text
        assert "'FAILED'" in text
        assert "statusSummary" in text

    def test_enroll_uses_a_deadline(self):
        # A wall-clock deadline from the Lambda's remaining time guards against
        # timing out mid-operation before sending a cfnresponse.
        text = _template_text()
        assert "get_remaining_time_in_millis" in text
        assert "baseline_deadline" in text

    def test_lambda_timeout_has_headroom(self):
        text = _template_text()
        assert "Timeout: 900" in text
        assert "Timeout: 60\n" not in text


class TestBaselineScpPermissions:
    """#114 Round-4: the CT baseline applies its guardrail SCPs using the caller's
    credentials, so the OrgDiscovery role needs Organizations SCP-management
    permissions (CloudTrail proved organizations:CreatePolicy was denied). Without
    them EnableBaseline/ResetEnabledBaseline land FAILED and the OUs stay unenrolled.
    """

    def test_role_can_create_and_attach_scps(self):
        text = _template_text()
        # The complete, bounded SCP lifecycle an enroll/reset performs.
        for action in (
            "organizations:CreatePolicy",
            "organizations:UpdatePolicy",
            "organizations:DeletePolicy",
            "organizations:AttachPolicy",
            "organizations:DetachPolicy",
            "organizations:EnablePolicyType",
            "organizations:TagResource",
        ):
            assert action in text, action

    def test_role_can_read_scps_for_idempotency(self):
        text = _template_text()
        for action in (
            "organizations:DescribePolicy",
            "organizations:ListPolicies",
            "organizations:ListPoliciesForTarget",
            "organizations:ListTargetsForPolicy",
        ):
            assert action in text, action


class TestBaselineServiceCatalogPermissions:
    """#114 Round-5: CT provisions the baseline via a Service Catalog product using
    the caller's credentials, so after the SCP gap was closed enrollment then failed
    on servicecatalog:ListProvisioningArtifacts (CloudTrail-proven). The OrgDiscovery
    role needs the Service Catalog provisioning lifecycle.
    """

    def test_role_has_proven_denied_action(self):
        # The exact action CloudTrail proved denied.
        assert "servicecatalog:ListProvisioningArtifacts" in _template_text()

    def test_role_can_provision_and_manage_products(self):
        text = _template_text()
        # The bounded provisioning lifecycle a baseline enroll/reset performs.
        for action in (
            "servicecatalog:DescribeProduct",
            "servicecatalog:DescribeProvisioningParameters",
            "servicecatalog:ProvisionProduct",
            "servicecatalog:DescribeProvisionedProduct",
            "servicecatalog:DescribeRecord",
            "servicecatalog:UpdateProvisionedProduct",
            "servicecatalog:TerminateProvisionedProduct",
        ):
            assert action in text, action


class TestBaselineFailureSurfacing:
    """#114 Round-4: a FAILED baseline op must be surfaced, not hidden behind
    CREATE_COMPLETE (the OU stays un-enrolled with SCPs unenforced)."""

    def test_enroll_returns_outcome_status(self):
        text = _template_text()
        # enroll_ou_baseline returns a status the caller can act on.
        assert "failed_baselines" in text
        assert "pending_baselines" in text

    def test_failed_baselines_logged_with_marker(self):
        text = _template_text()
        assert "BASELINE-FAILED" in text

    def test_failed_baselines_recorded_and_output(self):
        text = _template_text()
        # Recorded in an SSM param and in the resource outputs for visibility.
        assert "baseline-failed-ous" in text
        assert "BaselineFailedOus" in text

    def test_stack_still_succeeds_on_failed_baseline(self):
        # Eventually-consistent re-run model: surface but do NOT fail the stack.
        text = _template_text()
        # The success response is still sent after the surfacing block.
        idx_marker = text.index("BASELINE-FAILED")
        idx_success = text.index("cfnresponse.SUCCESS, response_data")
        assert idx_success > idx_marker


class TestRollbackLeaveAndLog:
    """#94: OUs are never auto-deleted; SSM params are cleaned and creations logged."""

    def test_delete_handler_does_not_delete_ous(self):
        text = _template_text()
        # Leave-and-log: the Delete path must not delete organizational units.
        assert "delete_organizational_unit" not in text
        assert "leave-and-log" in text.lower()

    def test_delete_handler_cleans_ssm_params(self):
        text = _template_text()
        # SSM cleanup by path is retained (also clears any prior partial-run params).
        assert "get_parameters_by_path" in text
        assert "delete_parameter" in text

    def test_created_ous_are_flagged_as_orphan_risk(self):
        text = _template_text()
        # Created (not adopted) OUs are tracked and logged for manual cleanup.
        assert "created_ous" in text
        assert "ORPHAN-RISK" in text

    def test_adopt_or_create_reports_creation(self):
        text = _template_text()
        # adopt_or_create_ou returns whether it created the OU so the caller can flag it.
        assert "return ou['Id'], False" in text
        assert "return ou_id, True" in text


class TestDiscoveryRoleNameLength:
    """#90: the discovery role name must stay within IAM's 64-char limit."""

    # The generator names this stack Titanium-<template-without-.yaml>.
    STACK_NAME = "Titanium-01-organizations-stack-mgmt-ous"

    def test_role_name_uses_stackname_then_suffix(self):
        text = _template_text()
        # Suffix-after-stackname ordering keeps the name short (issue #90).
        assert "RoleName: !Sub '${AWS::StackName}-OrgDiscovery'" in text
        # The old overflowing form must not come back.
        assert "Titanium-OrgDiscovery-${AWS::StackName}-Role" not in text

    def test_resolved_role_name_within_iam_limit(self):
        resolved = f"{self.STACK_NAME}-OrgDiscovery"
        assert len(resolved) <= 64, f"{resolved} is {len(resolved)} chars (>64)"


class TestBuilderUnits:
    """Direct builder-level assertions."""

    def test_build_ou_list_lines(self):
        processor = SimpleOrganizationProcessor()
        lines = processor._build_ou_list_lines(["Infrastructure"])
        assert lines[0] == "      OrganizationalUnits:"
        assert "        - Name: 'Infrastructure'" in lines
        assert "          LogicalId: 'Infrastructure'" in lines

    def test_build_ou_list_lines_empty(self):
        processor = SimpleOrganizationProcessor()
        assert processor._build_ou_list_lines([]) == ["      OrganizationalUnits: []"]

    def test_resource_lines_have_no_ssm_parameter(self):
        processor = SimpleOrganizationProcessor()
        lines = "\n".join(processor._build_ou_resource_lines(["Workloads"]))
        # SSM ID params are written by the Lambda (idempotent), not as resources.
        assert "AWS::SSM::Parameter" not in lines
