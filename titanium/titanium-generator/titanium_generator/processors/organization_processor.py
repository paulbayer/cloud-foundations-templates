"""
Enhanced organization processor for Titanium Template Modifier.

This module handles organization section processing with support for
organization ID mapping from bootstrap configuration.
"""

import re
from typing import Dict, Any, List
from ..base_processor import SimpleProcessor
from ..naming import ssm_slug
from ..processor_registry import register_processor


@register_processor("organization")
class SimpleOrganizationProcessor(SimpleProcessor):
    """
    Enhanced processor for the Organization section.

    This processor handles SCPs, OUs, tagging policies, and backup policies
    with organization ID mapping support from bootstrap configuration.
    """

    def __init__(self, section_name: str = "organization"):
        super().__init__(section_name)

    # Control Tower's AWSControlTowerBaseline. Registering an OU against this
    # baseline is what enrolls it into the landing zone; creating the OU with AWS
    # Organizations alone leaves it ungoverned and invisible to Control Tower.
    CONTROL_TOWER_BASELINE_ID = "17BSJV3IGJ2QSGA2"

    # Baseline version paired with Landing Zone 4.0.
    CONTROL_TOWER_BASELINE_VERSION = "5.0"

    OU_MARKER = "generated-organizational-units"
    OU_OUTPUT_MARKER = "generated-ou-outputs"
    OU_LIST_MARKER = "generated-ou-list"

    # Global-service control-plane region. IAM, CloudFront, Route53, STS and other
    # global services route through us-east-1, so the LimitRegionUsage SCP must
    # always allow it or those calls would be denied even when the deny SCP's
    # NotAction list is bypassed. Always appended to the derived allowed-regions.
    _GLOBAL_SERVICE_REGION = "us-east-1"

    def finalize_parameters(self, config_items, updates):
        """Derive the LimitRegionUsage SCP allowed-regions from enabledRegions.

        The SCP template ships a hardcoded default (us-east-1,us-west-2) that the
        deploy guide auto-resolves and hides, so the SCP silently allowed regions
        the user never selected (#101). Derive tLimitRegionUsageAllowedRegions
        from the config's enabledRegions instead, always including us-east-1 for
        global-service reachability (see _GLOBAL_SERVICE_REGION). When the config
        has no enabledRegions, leave the template default untouched.
        """
        enabled_regions = (self.full_config or {}).get("enabledRegions", []) or []
        if not enabled_regions:
            return
        allowed = list(enabled_regions)
        if self._GLOBAL_SERVICE_REGION not in allowed:
            allowed.append(self._GLOBAL_SERVICE_REGION)
        updates["tLimitRegionUsageAllowedRegions"] = ",".join(allowed)

    def process(self, template_yaml: str, section_config: Dict[str, Any]) -> str:
        """
        Process an organization template.

        Extends the base parameter-substitution behaviour with generated OU resources.
        The base implementation returns early when a section yields no parameter
        updates, so OU injection is applied independently of it — 01-*-ous.yaml needs
        resources injected but has no parameters to substitute.

        Args:
            template_yaml: CloudFormation template YAML content
            section_config: Configuration dictionary for the organization section

        Returns:
            Modified template YAML content
        """
        modified = super().process(template_yaml, section_config)
        base_modifications = list(self.modifications)

        modified, ou_modifications = self._inject_organizational_units(modified, section_config)

        self.modifications = base_modifications + ou_modifications
        return modified

    def _landing_zone(self) -> Dict[str, Any]:
        """
        The Control Tower landing zone config block.

        Both the section key and the nesting matter: the config uses `controlTower`
        (capital T) and everything this processor needs sits under `landingZone`, which
        is also how controltower_processor.extract_items reaches it. Reading
        `controltower` or a top-level key instead silently yields {} and every caller
        falls through to a default, which hides a misconfiguration rather than
        surfacing it.
        """
        controltower = (self.full_config or {}).get("controlTower", {}) or {}
        return controltower.get("landingZone", {}) or {}

    def _hub_ou_name(self) -> str:
        """
        Name of the OU that Control Tower creates for its own service accounts.

        Under Landing Zone 4.0 the hub OU is declared in the Control Tower manifest,
        so this template must not also create it — doing so would collide on the OU
        name. It is discovered at deploy time instead.
        """
        org_structure = self._landing_zone().get("organizationStructure", {}) or {}

        # Must agree with controltower_processor, which derives tSecurityOuName — the
        # name the Control Tower template gives the hub OU — from the same key. If the
        # two disagree, this template generates a second OU with the hub's name and the
        # deployment fails on a duplicate OU name.
        if isinstance(org_structure, str):
            # Tolerate a plain string, which is what the shape looks like at a glance.
            return org_structure
        security = org_structure.get("security", {}) or {}
        return security.get("name", "Security") if isinstance(security, dict) else "Security"

    @staticmethod
    def _logical_id(ou_name: str) -> str:
        """Convert an OU name into a CloudFormation logical ID fragment."""
        parts = [p for p in re.split(r"[^A-Za-z0-9]+", ou_name) if p]
        return "".join(part[:1].upper() + part[1:] for part in parts)

    @staticmethod
    def _ssm_slug(ou_name: str) -> str:
        """
        Convert an OU name into an SSM-parameter-safe path segment.

        Delegates to the shared ``ssm_slug`` helper so these paths stay
        byte-identical to the ones the deployment-guide generator reads back.
        """
        return ssm_slug(ou_name)

    def _inject_organizational_units(
        self, template_yaml: str, section_config: Dict[str, Any]
    ) -> tuple:
        """
        Inject OU adopt-or-create wiring for every configured OU.

        Three marker regions are populated (issue #78): the discovery Lambda's
        OU list (name + logical id), the (now comment-only) resource region, and one
        output per OU. The OUs, their SSM ID parameters, and their Control Tower
        baseline enrollment are all provisioned idempotently by the discovery Lambda
        (adopt-or-create for OUs, adopt-or-enable for baselines — issue #91), so no
        native AWS::Organizations::OrganizationalUnit or AWS::ControlTower::EnabledBaseline
        resources are emitted.

        Returns the template unchanged when it carries no OU marker region, which is
        the case for every organization template except 01-*-ous.yaml.
        """
        if self.OU_MARKER not in template_yaml:
            return template_yaml, []

        ou_entries = section_config.get("organizationalUnits", []) or []
        hub_ou_name = self._hub_ou_name()

        ou_names = []
        for entry in ou_entries:
            name = entry.get("name") if isinstance(entry, dict) else entry
            if not name:
                continue
            if name == hub_ou_name:
                # Owned by the Control Tower template; looked up, not created.
                continue
            if name not in ou_names:
                ou_names.append(name)

        modifications = []

        ou_list_lines = self._build_ou_list_lines(ou_names)
        template_yaml, mods = self.template_modifier.inject_marker_region(
            template_yaml, self.OU_LIST_MARKER, ou_list_lines
        )
        modifications.extend(mods)

        resource_lines = self._build_ou_resource_lines(ou_names)
        template_yaml, mods = self.template_modifier.inject_marker_region(
            template_yaml, self.OU_MARKER, resource_lines
        )
        modifications.extend(mods)

        output_lines = self._build_ou_output_lines(ou_names)
        template_yaml, mods = self.template_modifier.inject_marker_region(
            template_yaml, self.OU_OUTPUT_MARKER, output_lines
        )
        modifications.extend(mods)

        # The hub OU is discovered by name at deploy time, so the template's default
        # has to match whatever Control Tower was told to create.
        template_yaml, mods = self.template_modifier.update_parameter_defaults(
            template_yaml, {"uHubOuName": hub_ou_name}
        )
        modifications.extend([m for m in mods if not m.startswith("Info:")])

        if ou_names:
            modifications.append(
                f"Generated {len(ou_names)} organizational unit(s) with Control Tower "
                f"enrollment: {', '.join(ou_names)} (hub OU '{hub_ou_name}' excluded — "
                f"created by Control Tower)"
            )

        return template_yaml, modifications

    def _build_ou_list_lines(self, ou_names: List[str]) -> List[str]:
        """Build the discovery Lambda's OrganizationalUnits property value.

        Each entry pairs the OU Name (adopted-or-created at deploy time) with the
        CloudFormation LogicalId the generated baselines/outputs use to GetAtt the
        returned OU ID (``<LogicalId>OuId``). Emitted at 6-space indent to sit under
        ``OrganizationRootDiscovery.Properties``.
        """
        if not ou_names:
            return ["      OrganizationalUnits: []"]

        lines = ["      OrganizationalUnits:"]
        for ou_name in ou_names:
            logical = self._logical_id(ou_name)
            lines.append(f"        - Name: '{ou_name}'")
            lines.append(f"          LogicalId: '{logical}'")
        return lines

    def _build_ou_resource_lines(self, ou_names: List[str]) -> List[str]:
        """Build the generated per-OU resource block (now empty by design).

        Baseline enrollment is no longer emitted as native
        ``AWS::ControlTower::EnabledBaseline`` resources: those always CREATE and
        fail with AlreadyExists on any OU that is already Control Tower-enrolled,
        rolling back the whole stack (issue #91). Enrollment is instead performed by
        the discovery Lambda, which adopts already-enrolled OUs and fires
        EnableBaseline for the rest (see ``enroll_ou_baseline`` in the template). The
        OUs, their SSM ID parameters, and their enrollment are therefore all handled
        via the Lambda's ``OrganizationalUnits`` input (issue #78), so this region
        emits no resources — only a comment explaining why.
        """
        return [
            "  # Baseline enrollment is performed by the discovery Lambda (adopt if",
            "  # already enrolled, else fire EnableBaseline) rather than by native",
            "  # AWS::ControlTower::EnabledBaseline resources, which are not idempotent",
            "  # (issue #91). See the OrganizationalUnits input on OrganizationRootDiscovery.",
        ]

    def _build_ou_output_lines(self, ou_names: List[str]) -> List[str]:
        """Build the generated per-OU output block."""
        if not ou_names:
            return ["  # No organizational units configured."]

        lines = []
        for ou_name in ou_names:
            logical = self._logical_id(ou_name)
            lines.extend(
                [
                    "",
                    f"  {logical}OuId:",
                    f"    Description: '{ou_name} OU ID'",
                    f"    Value: !GetAtt OrganizationRootDiscovery.{logical}OuId",
                    "    Export:",
                    f"      Name: !Sub '${{AWS::StackName}}-{logical}OU-ID'",
                ]
            )
        return lines

    def extract_items(self, section_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract organization policy configuration items.

        Deployment targets are NOT resolved here. OU IDs only exist after the OUs
        are created at deploy time, so the u<Policy>Targets parameters are left as
        deploy-time inputs; the LLM deployment guide populates them from the SSM
        parameters template 01 publishes (/titanium/organization/ou-ids/...). See
        issue #75.

        Args:
            section_config: Organization section from Titanium.yaml

        Returns:
            List of configuration items (deploy toggle + description only).
        """
        items = []

        # Extract Service Control Policies
        for scp in section_config.get("serviceControlPolicies", []):
            items.append(
                {
                    "name": scp["name"],
                    "type": "scp",
                    "enabled": True,  # SCPs in config are always enabled
                    "config": scp,
                }
            )

        # Extract Tagging Policies
        for policy in section_config.get("taggingPolicies", []):
            items.append(
                {
                    "name": policy["name"],
                    "type": "tagging_policy",
                    "enabled": True,  # Presence implies enabled
                    "config": policy,
                }
            )

        # Extract Backup Policies
        for policy in section_config.get("backupPolicies", []):
            items.append(
                {
                    "name": policy["name"],
                    "type": "backup_policy",
                    "enabled": policy.get("enable", True),
                    "config": policy,
                }
            )

        return items

    def _generate_policy_parameters(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate parameter updates for a backup or tagging policy.

        Both policy types emit the same shape: a deployment toggle and an
        optional description. Deployment targets (u<PolicyName>Targets) are
        supplied at deploy time — see extract_items and issue #75.

        Args:
            item: Backup or tagging policy configuration item

        Returns:
            Dictionary of parameter updates for the policy
        """
        parameters = {}
        policy_name = item["name"]

        # Generate deployment toggle parameter (tDeploy<PolicyName>)
        deploy_param = f"tDeploy{policy_name}"
        parameters[deploy_param] = self._bool(item["enabled"])

        # Generate description parameter (t<PolicyName>Description)
        desc_param = f"t{policy_name}Description"
        if "description" in item["config"]:
            parameters[desc_param] = item["config"]["description"]

        return parameters

    def _item_handlers(self):
        return {
            'backup_policy': self._handle_policy,
            'tagging_policy': self._handle_policy,
            'scp': self._handle_scp,
        }

    def _handle_policy(self, item, updates):
        # Backup and tagging policies share the same parameter shape.
        updates.update(self._generate_policy_parameters(item))

    def _handle_scp(self, item, updates):
        # SCPs opt into the shared t/u convention (_apply_convention), minus the
        # deploy-time targets. Deployment targets are supplied at deploy time via the
        # deployment guide (populated from SSM OU IDs), not resolved at generation
        # time. The convention emits u<Name>Targets from the config's OU *names*,
        # which the attachment Lambda cannot attach, so drop it here (see issue #75).
        scp_parameters = {}
        self._apply_convention(item, scp_parameters)
        scp_parameters.pop(f"u{item['name']}Targets", None)
        updates.update(scp_parameters)
