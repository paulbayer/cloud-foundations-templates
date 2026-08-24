"""
Tests for #89: the GuardDuty detector stack gets a pre-flight existence check.

GuardDuty allows one detector per account/region, and org-auto-enabled detectors
survive stack deletion, so a plain create fails with AlreadyExists on a
non-greenfield account. Deployment assumes greenfield; rather than add an
adopt-or-create custom resource, the deployment guide prepends a pre-flight
`list-detectors` check to the detector stack so the agent skips it (instead of
hard-failing) when a detector already exists.
"""

from titanium_generator.mcp_tools.llm_agent_guide import LLMAgentGuideGenerator

DETECTOR_TEMPLATE = "03-guardduty-stackset-audit-detector.yaml"


def _deploy_step(template_name):
    gen = LLMAgentGuideGenerator()
    return gen._generate_deployment_step(
        template_name,
        {"output_path": f"/tmp/out/security/{template_name}"},
        "security",
        "us-east-1",
        {},
        {},
        {},
    )


class TestGuardDutyPreflight:
    def test_preflight_check_defined_for_detector(self):
        gen = LLMAgentGuideGenerator()
        check = gen._preflight_check(DETECTOR_TEMPLATE, "us-west-2")
        assert check is not None
        assert "list-detectors" in check["command"]
        assert "us-west-2" in check["command"]
        assert "skip" in check["skip_guidance"].lower()

    def test_no_preflight_for_other_templates(self):
        gen = LLMAgentGuideGenerator()
        assert gen._preflight_check("01-iam-stackset-org-password-policy.yaml", "us-east-1") is None

    def test_detector_step_starts_with_preflight(self):
        step = _deploy_step(DETECTOR_TEMPLATE)
        assert step["commands"][0]["description"].startswith("Pre-flight")
        assert "list-detectors" in step["commands"][0]["command"]
        # The skip guidance is surfaced to the agent up front.
        assert any("SKIP" in instr or "skip" in instr for instr in step["agent_instructions"])

    def test_other_step_has_no_preflight(self):
        step = _deploy_step("01-iam-stackset-org-password-policy.yaml")
        assert not any(
            "Pre-flight" in c.get("description", "") for c in step["commands"]
        )
