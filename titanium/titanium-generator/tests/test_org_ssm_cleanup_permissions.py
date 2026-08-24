"""
Test for #102: the org/01 discovery Lambda role must be able to list the SSM
parameters it wrote, so the Delete handler can clean them up.

The Delete handler lists every parameter under the prefix via
get_parameters_by_path before deleting them. Without ssm:GetParametersByPath the
list call fails with AccessDenied, the handler swallows it, and the params
survive the stack delete (obs-094's cleanup was effectively a no-op).

Reopened (obs-102): GetParametersByPath authorizes against the *path container*
resource (the prefix, no trailing /*), NOT the child ARNs. The first fix scoped
it to the /* ARN only, so the list call was still denied. These tests assert
each action is granted on the correct ARN shape.
"""

from pathlib import Path

import yaml

import titanium_generator

TEMPLATE = (
    Path(titanium_generator.__file__).parent
    / "mcp_tools" / "templates" / "organization"
    / "01-organizations-stack-mgmt-ous.yaml"
)


class _CfnLoader(yaml.SafeLoader):
    pass


# Preserve the scalar body of !Sub so the tests can inspect the ARN string;
# collapse every other CFN tag to None (we don't need their values here).
def _keep_sub_scalar(loader, suffix, node):
    if suffix == "Sub" and isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    return None


_CfnLoader.add_multi_constructor("!", _keep_sub_scalar)

# The !Sub bodies are inspected verbatim (unresolved), so the prefix appears as
# its ${uSSMParameterPrefix} placeholder. The container ARN has no trailing /*.
CONTAINER_ARN = (
    "arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter${uSSMParameterPrefix}"
)
CHILD_ARN = CONTAINER_ARN + "/*"


def _ssm_statements():
    """Return (action_set, resource) tuples for the discovery role policies."""
    doc = yaml.load(TEMPLATE.read_text(), Loader=_CfnLoader)
    role = doc["Resources"]["OrganizationDiscoveryRole"]
    statements = []
    for policy in role["Properties"]["Policies"]:
        for stmt in policy["PolicyDocument"]["Statement"]:
            action = stmt.get("Action", [])
            actions = set(action if isinstance(action, list) else [action])
            statements.append((actions, stmt.get("Resource")))
    return statements


def _resource_for(action):
    """The Resource string granted for a given SSM action, if any."""
    for actions, resource in _ssm_statements():
        if action in actions:
            return resource
    return None


def _all_actions():
    actions = set()
    for acts, _ in _ssm_statements():
        actions.update(acts)
    return actions


def test_get_parameters_by_path_targets_container_arn():
    # GetParametersByPath authorizes against the path container ARN (no /*),
    # not the child ARNs. Scoping it to /* leaves the list call AccessDenied.
    assert _resource_for("ssm:GetParametersByPath") == CONTAINER_ARN


def test_item_actions_target_child_arns():
    for action in ("ssm:PutParameter", "ssm:DeleteParameter", "ssm:GetParameter"):
        assert _resource_for(action) == CHILD_ARN, action


def test_role_retains_delete_permission():
    # Guard: listing is useless without the delete the handler actually performs.
    assert "ssm:DeleteParameter" in _all_actions()
