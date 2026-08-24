"""
Tests for #68: the Control Tower template must not create the AWS Organization.

Control Tower requires a pre-existing organization, so the template treats the
org as a prerequisite: it no longer declares AWS::Organizations::Organization and
sources the hub OU's parent from the uOrganizationRootId parameter. The
deployment guide must prompt for that Root ID with `list-roots`.
"""

from pathlib import Path

import titanium_generator
from titanium_generator.mcp_tools.llm_agent_guide import LLMAgentGuideGenerator

CT_TEMPLATE = (
    Path(titanium_generator.__file__).parent
    / "mcp_tools" / "templates" / "controltower"
    / "01-controltower-stack-mgmt-setup.yaml"
)


def _template_text():
    return CT_TEMPLATE.read_text()


def test_template_does_not_create_organization():
    text = _template_text()
    assert "AWS::Organizations::Organization'" not in text
    assert "AWS::Organizations::Organization\"" not in text
    # The OrganizationalUnit / Account resources must still be present.
    assert "AWS::Organizations::OrganizationalUnit" in text


def test_template_declares_root_id_parameter():
    text = _template_text()
    assert "uOrganizationRootId:" in text


def test_hub_ou_parent_uses_root_id_parameter():
    text = _template_text()
    assert "ParentId: !Ref uOrganizationRootId" in text


class TestRootIdPrompt:
    def test_live_prompt_uses_list_roots(self):
        gen = LLMAgentGuideGenerator()
        prompt = gen._generate_live_parameter_prompt(
            "uOrganizationRootId", {"Type": "String"}
        )
        assert "list-roots" in prompt
        assert "describe-organization" not in prompt

    def test_parameter_prompt_uses_list_roots(self):
        gen = LLMAgentGuideGenerator()
        info = gen._generate_parameter_prompt(
            "uOrganizationRootId", {"Type": "String"}, "controltower"
        )
        assert "list-roots" in info["prompt"]
