"""
Tests for #79: Control Tower setup retention parameters must carry a default.

controltower/01-controltower-stack-mgmt-setup.yaml declares
tLoggingBucketRetentionPeriod / tAccessLoggingBucketRetentionPeriod as
Type: Number with no Default. The deployment guide does not pass t* parameters,
so a greenfield deploy failed with "Parameters must have values". The generator
now injects the configured retention values as the parameters' Default (the
value is sourced from the Titanium config, never hardcoded in the template).
"""

from pathlib import Path

import yaml

import titanium_generator
from titanium_generator.processors.controltower_processor import ControlTowerProcessor
from titanium_generator.template_modifier import TemplateModifier

CT_TEMPLATE = (
    Path(titanium_generator.__file__).parent
    / "mcp_tools" / "templates" / "controltower"
    / "01-controltower-stack-mgmt-setup.yaml"
)


class _CfnLoader(yaml.SafeLoader):
    pass


_CfnLoader.add_multi_constructor("!", lambda loader, suffix, node: None)


def _params(rendered):
    return yaml.load(rendered, Loader=_CfnLoader)["Parameters"]


class TestRetentionDefaultsFromConfig:
    def _render(self, logging):
        tpl = CT_TEMPLATE.read_text()
        section = {"enable": True, "landingZone": {"logging": logging}}
        return ControlTowerProcessor().process(tpl, section)

    def test_configured_values_become_defaults(self):
        params = _params(
            self._render(
                {
                    "loggingBucketRetentionDays": 400,
                    "accessLoggingBucketRetentionDays": 1825,
                }
            )
        )
        assert params["tLoggingBucketRetentionPeriod"]["Default"] == 400
        assert params["tAccessLoggingBucketRetentionPeriod"]["Default"] == 1825

    def test_fallbacks_used_when_fields_absent(self):
        # Logging block present but retention omitted → processor fallbacks.
        params = _params(self._render({"controlTowerOrganizationTrail": True}))
        assert params["tLoggingBucketRetentionPeriod"]["Default"] == 365
        assert params["tAccessLoggingBucketRetentionPeriod"]["Default"] == 3650

    def test_template_ships_without_hardcoded_default(self):
        # The value comes from config at generation time, not a template literal.
        text = CT_TEMPLATE.read_text()
        block = text.split("tLoggingBucketRetentionPeriod:", 1)[1].split("tAccessLoggingBucketRetentionPeriod:", 1)[0]
        assert "Default:" not in block


class TestTemplateModifierInsertsMissingDefault:
    """The insert path is a general capability, not CT-specific."""

    def test_inserts_default_when_absent(self):
        tm = TemplateModifier()
        tpl = "Parameters:\n  tFoo:\n    Type: Number\n    Description: d\n"
        out, _ = tm.update_parameter_defaults(tpl, {"tFoo": "42"})
        assert yaml.safe_load(out)["Parameters"]["tFoo"]["Default"] == 42

    def test_targets_real_param_not_metadata_label(self):
        # A ParameterLabels entry shares the name but has no Type: — must be skipped.
        tm = TemplateModifier()
        tpl = (
            "Metadata:\n"
            "  AWS::CloudFormation::Interface:\n"
            "    ParameterLabels:\n"
            "      tFoo:\n"
            "        default: \"Foo label\"\n"
            "Parameters:\n"
            "  tFoo:\n"
            "    Type: String\n"
            "    Default: \"false\"\n"
        )
        out, _ = tm.update_parameter_defaults(tpl, {"tFoo": "true"})
        doc = yaml.safe_load(out)
        assert doc["Parameters"]["tFoo"]["Default"] == "true"
        # The label block is untouched.
        assert doc["Metadata"]["AWS::CloudFormation::Interface"]["ParameterLabels"]["tFoo"]["default"] == "Foo label"
