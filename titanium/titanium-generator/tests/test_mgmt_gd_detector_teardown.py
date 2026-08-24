"""
Test for #113: security/05 (GuardDuty configure) teardown must delete the
management-account GuardDuty detector.

Enabling GuardDuty delegation from the management account leaves a detector there
as a side-effect. The Delete handler previously only disabled the org admin, so
the mgmt-account detector survived teardown and accumulated across deploy/teardown
cycles. Teardown must now delete it, and the mgmt role must be allowed to.
"""

from pathlib import Path

import yaml

import titanium_generator

GD_TEMPLATE = (
    Path(titanium_generator.__file__).parent
    / "mcp_tools" / "templates" / "security"
    / "05-guardduty-stack-mgmt-configure.yaml"
)


class _CfnLoader(yaml.SafeLoader):
    pass


_CfnLoader.add_multi_constructor("!", lambda loader, suffix, node: None)


def _doc():
    return yaml.load(GD_TEMPLATE.read_text(), Loader=_CfnLoader)


def _role_actions():
    role = _doc()["Resources"]["rGuardDutyConfigurationLambdaRole"]
    actions = set()
    for policy in role["Properties"]["Policies"]:
        for stmt in policy["PolicyDocument"]["Statement"]:
            action = stmt.get("Action", [])
            actions.update(action if isinstance(action, list) else [action])
    return actions


def _lambda_code():
    return _doc()["Resources"]["rGuardDutyConfigurationLambda"]["Properties"]["Code"]["ZipFile"]


def test_role_can_delete_management_detector():
    actions = _role_actions()
    assert "guardduty:ListDetectors" in actions
    assert "guardduty:DeleteDetector" in actions


def test_delete_handler_deletes_management_detector():
    code = _lambda_code()
    assert "delete_detector" in code
    assert "list_detectors" in code
