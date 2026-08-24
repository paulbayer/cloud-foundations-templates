"""
Tests for #80: the identity password-policy StackSet must get a deploy step.

identity/01-iam-stackset-org-password-policy.yaml is produced by
process_all_templates, but the deployment-guide generator's phase_order omitted
'identity', so the guide had no deploy step for it and the configured
iamPasswordPolicy was never deployed (orphaned template). 'identity' is now a
guide phase.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from titanium_generator.mcp_tools.llm_agent_guide import LLMAgentGuideGenerator
from titanium_generator.mcp_tools.process_templates import process_all_templates


@pytest.fixture
def temp_output_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


@pytest.fixture
def config_with_password_policy(tmp_path):
    cfg = tmp_path / "titanium.yaml"
    cfg.write_text(
        "homeRegion: us-east-1\n"
        "enabledRegions: [us-east-1]\n"
        "controlTower:\n"
        "  enable: true\n"
        "iamPasswordPolicy:\n"
        "  minimumPasswordLength: 16\n"
        "  maxPasswordAge: 60\n"
    )
    return str(cfg)


def test_identity_phase_registered():
    gen = LLMAgentGuideGenerator()
    # The phase must have a human-readable description (used in the guide header).
    assert gen._get_phase_description("identity") != "Deploy identity infrastructure"
    assert "password policy" in gen._get_phase_description("identity").lower()


def test_password_policy_gets_deploy_step(config_with_password_policy, temp_output_dir):
    process_all_templates(config_with_password_policy, temp_output_dir, sections=["identity"])

    steps = json.loads((Path(temp_output_dir) / "llm_agent_steps.json").read_text())["steps"]
    identity_steps = [s for s in steps if s.get("phase") == "identity"]

    # A deploy step for the password-policy StackSet must exist.
    titles = " ".join(s["title"].lower() for s in identity_steps)
    assert identity_steps, "identity phase produced no steps"
    assert "password policy" in titles

    guide = (Path(temp_output_dir) / "LLM_AGENT_DEPLOYMENT_GUIDE.md").read_text()
    assert "01-iam-stackset-org-password-policy" in guide
