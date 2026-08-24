"""
Test for #103: the SecurityHub delegate cleanup Lambda (security/01) must wait
for the delegated-admin deregistration to propagate before returning.

The custom resource is deleted right before the native
AWS::SecurityHub::DelegatedAdmin resource (which DependsOn it). That native
delete DELETE_FAILs if the account is still the org admin, and
disable_organization_admin_account is eventually consistent — so the cleanup
Lambda polls list_organization_admin_accounts until the deregistration settles.
"""

from pathlib import Path

import yaml

import titanium_generator

TEMPLATE = (
    Path(titanium_generator.__file__).parent
    / "mcp_tools" / "templates" / "security"
    / "01-securityhub-stack-mgmt-delegate.yaml"
)


class _CfnLoader(yaml.SafeLoader):
    pass


_CfnLoader.add_multi_constructor("!", lambda loader, suffix, node: None)


def _doc():
    return yaml.load(TEMPLATE.read_text(), Loader=_CfnLoader)


def _cleanup_code():
    return _doc()["Resources"]["SecurityHubCleanupLambda"]["Properties"]["Code"]["ZipFile"]


def test_cleanup_polls_for_deregistration_propagation():
    code = _cleanup_code()
    assert "import time" in code
    # Polls the admin list and sleeps between checks after disabling.
    assert "list_organization_admin_accounts" in code
    assert "time.sleep" in code


def test_cleanup_role_can_list_admin_accounts():
    role = _doc()["Resources"]["SecurityHubCleanupLambdaRole"]
    actions = set()
    for policy in role["Properties"]["Policies"]:
        for stmt in policy["PolicyDocument"]["Statement"]:
            action = stmt.get("Action", [])
            actions.update(action if isinstance(action, list) else [action])
    assert "securityhub:ListOrganizationAdminAccounts" in actions
    assert "securityhub:DisableOrganizationAdminAccount" in actions
