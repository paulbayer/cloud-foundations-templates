"""
Tests for the Identity Center assumption (issue #77).

At this phase Control Tower is a manually-provisioned prerequisite assumed to
manage IAM Identity Center. The landing zone manifest hardcodes
accessManagement.enabled: true, so:

  - every OU enrolled into the Control Tower baseline must carry the required
    IdentityCenterEnabledBaselineArn, and
  - the Control Tower processor no longer emits the dead EnableIdentityCenterAccess
    parameter (which the template never defined).

Since #91 moved baseline enrollment into the discovery Lambda, the ARN is attached
at runtime by that Lambda — which discovers whether the landing zone actually
manages Identity Center rather than assuming it in the generator (the future
direction the old generator-side gate's docstring called for).
"""

from pathlib import Path

import titanium_generator
from titanium_generator.processors.controltower_processor import ControlTowerProcessor

OU_TEMPLATE = (
    Path(titanium_generator.__file__).parent
    / "mcp_tools" / "templates" / "organization"
    / "01-organizations-stack-mgmt-ous.yaml"
)


class TestBaselineCarriesIdentityCenterArn:
    """The Lambda attaches the IdC ARN when enrolling an OU baseline."""

    def test_enroll_passes_identity_center_arn_when_discovered(self):
        text = OU_TEMPLATE.read_text()
        # The enrollment helper attaches the discovered ARN as an EnableBaseline
        # parameter, gated on it actually being present for this account.
        assert "IdentityCenterEnabledBaselineArn" in text
        assert "if identity_center_arn:" in text


class TestControlTowerSecurityParameterUpdates:
    """The dead EnableIdentityCenterAccess emission is gone; DenyRegion stays."""

    def _updates(self, security_config):
        processor = ControlTowerProcessor()
        item = {
            "name": "ControlTowerSecurity",
            "type": "control_tower_security",
            "enabled": True,
            "config": security_config,
        }
        return processor.generate_parameter_updates([item])

    def test_no_dead_identity_center_parameter(self):
        updates = self._updates({"enableIdentityCenterAccess": True, "denyRegion": True})
        assert "EnableIdentityCenterAccess" not in updates

    def test_deny_region_still_emitted(self):
        updates = self._updates({"enableIdentityCenterAccess": True, "denyRegion": False})
        assert updates.get("DenyRegion") == "false"
