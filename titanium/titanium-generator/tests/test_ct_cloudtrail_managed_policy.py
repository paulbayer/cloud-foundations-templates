"""
Regression test for #70: the Control Tower CloudTrail role must attach the
AWS-managed AWSControlTowerCloudTrailRolePolicy via ManagedPolicyArns, not an
inline AWS::IAM::Policy (which Landing Zone 4.0 rejects).
"""

from pathlib import Path

import titanium_generator

CT_TEMPLATE = (
    Path(titanium_generator.__file__).parent
    / "mcp_tools" / "templates" / "controltower"
    / "01-controltower-stack-mgmt-setup.yaml"
)


def _text():
    return CT_TEMPLATE.read_text()


def test_no_inline_cloudtrail_role_policy_resource():
    # The inline policy resource must be gone.
    assert "rAWSControlTowerCloudTrailRolePolicy:" not in _text()


def test_cloudtrail_role_attaches_managed_policy():
    text = _text()
    assert "iam::aws:policy/service-role/AWSControlTowerCloudTrailRolePolicy" in text
    # Attached via ManagedPolicyArns (partition-portable).
    assert "arn:${AWS::Partition}:iam::aws:policy/service-role/AWSControlTowerCloudTrailRolePolicy" in text
