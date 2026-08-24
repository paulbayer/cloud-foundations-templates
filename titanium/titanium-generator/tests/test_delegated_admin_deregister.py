"""
Test for #111: SH (security/01) and GD (security/05) delegate teardown must
deregister the Organizations-level delegated administrator, not just disable the
service-level org admin.

disable_organization_admin_account removes the service-level admin but leaves the
Organizations register-delegated-administrator entry for securityhub.amazonaws.com
/ guardduty.amazonaws.com on the Audit account, which orphans and accumulates
across deploy/teardown cycles. config -> Audit is Control Tower managed and must
be left alone.
"""

from pathlib import Path

import yaml

import titanium_generator

TEMPLATE_DIR = (
    Path(titanium_generator.__file__).parent / "mcp_tools" / "templates" / "security"
)
SH_TEMPLATE = TEMPLATE_DIR / "01-securityhub-stack-mgmt-delegate.yaml"
GD_TEMPLATE = TEMPLATE_DIR / "05-guardduty-stack-mgmt-configure.yaml"


class _CfnLoader(yaml.SafeLoader):
    pass


_CfnLoader.add_multi_constructor("!", lambda loader, suffix, node: None)


def _doc(template):
    return yaml.load(template.read_text(), Loader=_CfnLoader)


def _role_actions(doc, role_name):
    role = doc["Resources"][role_name]
    actions = set()
    for policy in role["Properties"]["Policies"]:
        for stmt in policy["PolicyDocument"]["Statement"]:
            action = stmt.get("Action", [])
            actions.update(action if isinstance(action, list) else [action])
    return actions


def _lambda_code(doc, lambda_name):
    return doc["Resources"][lambda_name]["Properties"]["Code"]["ZipFile"]


# --- security/01 (SecurityHub) ---

def test_sh_role_can_deregister_delegated_administrator():
    actions = _role_actions(_doc(SH_TEMPLATE), "SecurityHubCleanupLambdaRole")
    assert "organizations:DeregisterDelegatedAdministrator" in actions
    assert "organizations:ListDelegatedAdministrators" in actions


def test_sh_delete_handler_deregisters_securityhub_principal():
    code = _lambda_code(_doc(SH_TEMPLATE), "SecurityHubCleanupLambda")
    assert "deregister_delegated_administrator" in code
    assert "securityhub.amazonaws.com" in code


def test_sh_delete_handler_leaves_config_alone():
    # config -> Audit is Control Tower managed; teardown must never touch it.
    code = _lambda_code(_doc(SH_TEMPLATE), "SecurityHubCleanupLambda")
    assert "config.amazonaws.com" not in code


# --- security/05 (GuardDuty) ---

def test_gd_role_can_deregister_delegated_administrator():
    actions = _role_actions(_doc(GD_TEMPLATE), "rGuardDutyConfigurationLambdaRole")
    assert "organizations:DeregisterDelegatedAdministrator" in actions


def test_gd_delete_handler_deregisters_guardduty_principal():
    code = _lambda_code(_doc(GD_TEMPLATE), "rGuardDutyConfigurationLambda")
    assert "deregister_delegated_administrator" in code
    assert "guardduty.amazonaws.com" in code


def test_gd_delete_handler_leaves_config_alone():
    code = _lambda_code(_doc(GD_TEMPLATE), "rGuardDutyConfigurationLambda")
    assert "config.amazonaws.com" not in code
