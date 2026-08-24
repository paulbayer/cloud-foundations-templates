"""
Test for #103 (reopened): the SecurityHub configuration-policy cleanup Lambda
(security/02) must disable central configuration on teardown.

When SecurityHub central configuration is in use, AWS refuses to remove the
delegated admin (security/01) until the configuration policies are disassociated
+ deleted AND central configuration is disabled (ConfigurationType=LOCAL). The
02 Delete handler already disassociates + deletes the policy; it must also flip
the org configuration back to LOCAL, and its role must be allowed to do so.
"""

from pathlib import Path

import yaml

import titanium_generator

TEMPLATE = (
    Path(titanium_generator.__file__).parent
    / "mcp_tools" / "templates" / "security"
    / "02-securityhub-cspm-stackset-audit-configure.yaml"
)


class _CfnLoader(yaml.SafeLoader):
    pass


_CfnLoader.add_multi_constructor("!", lambda loader, suffix, node: None)


def _doc():
    return yaml.load(TEMPLATE.read_text(), Loader=_CfnLoader)


def _lambda_code():
    return _doc()["Resources"]["PolicyAssociationLambda"]["Properties"]["Code"]["ZipFile"]


def _role_actions():
    role = _doc()["Resources"]["PolicyAssociationLambdaRole"]
    actions = set()
    for policy in role["Properties"]["Policies"]:
        for stmt in policy["PolicyDocument"]["Statement"]:
            action = stmt.get("Action", [])
            actions.update(action if isinstance(action, list) else [action])
    return actions


def _role_grants(action):
    """True if the role is allowed `action` directly or via a securityhub:*/* grant."""
    acts = _role_actions()
    service = action.split(":", 1)[0]
    return action in acts or f"{service}:*" in acts or "*" in acts


def test_delete_handler_disables_central_configuration():
    code = _lambda_code()
    # Flips the org configuration back to LOCAL to disable central config.
    assert "update_organization_configuration" in code
    assert "'ConfigurationType': 'LOCAL'" in code


def test_role_can_update_organization_configuration():
    assert _role_grants("securityhub:UpdateOrganizationConfiguration")


def test_role_retains_policy_teardown_permissions():
    # Guard: disabling central config is only half the sequence — the policy
    # must still be disassociated + deleted first.
    assert _role_grants("securityhub:StartConfigurationPolicyDisassociation")
    assert _role_grants("securityhub:DeleteConfigurationPolicy")


def test_role_grants_securityhub_star_for_central_config_companions():
    # #103 Round-5: UpdateOrganizationConfiguration (LOCAL) was denied with a null
    # errorMessage (SecurityHub service-side rejection, not an IAM identity deny)
    # even though that action was granted — a companion central-config permission
    # SecurityHub does not name in CloudTrail is required. The proven-working grant
    # is securityhub:* on this teardown role.
    assert "securityhub:*" in _role_actions()


# --- #103 (reopened, Round-3): the earlier fix's teardown code existed but ran
# too optimistically — the native OrganizationConfiguration delete 409'd and wedged
# the stackset instance INOPERABLE, while the custom resource reported SUCCESS even
# when nothing was actually cleaned up. -------------------------------------------

def test_org_configuration_is_not_retained():
    # #115: OrganizationConfiguration must NOT be Retained. Retaining it left the
    # org singleton behind after teardown, so a redeploy's native CREATE hit
    # "Organization Configuration resource already exists". Retain is unnecessary
    # now that the obs-103 Round-4 fix confirms LOCAL + policy-deleted before the
    # PolicyAssociation custom resource returns SUCCESS: since that resource is torn
    # down (dependency order) BEFORE this one, central config is already disabled by
    # the time CFN issues this native delete, so it succeeds (no 409/INOPERABLE) and
    # clears the singleton — letting a redeploy CREATE cleanly.
    org_config = _doc()["Resources"]["SecurityHubOrganizationConfiguration"]
    assert "DeletionPolicy" not in org_config


def test_config_policy_still_retained():
    # Guard: the ConfigurationPolicy is still deleted by the custom resource's
    # Delete handler (disassociate -> delete), so it must stay Retained. Only the
    # OrganizationConfiguration Retain was dropped (#115).
    config_policy = _doc()["Resources"]["SecurityHubConfigurationPolicy"]
    assert config_policy.get("DeletionPolicy") == "Retain"


def test_delete_handler_reports_success_only_when_local_confirmed():
    # The Delete handler must gate its SUCCESS on the LOCAL flip actually
    # succeeding, rather than always reporting SUCCESS.
    code = _lambda_code()
    assert "if disable_central_configuration():" in code
    assert "cfnresponse.SUCCESS" in code
    assert "cfnresponse.FAILED" in code


def test_disable_central_configuration_polls_instead_of_swallowing():
    # The 409 "can't disable central config while policies/associations exist" is
    # retryable (async propagation). It must be retried, and the function must
    # return a bool so the caller can gate SUCCESS on it.
    code = _lambda_code()
    assert "def disable_central_configuration(" in code
    assert "return True" in code
    assert "return False" in code


def test_wait_for_disassociation_does_not_assume_done_on_error():
    # Regression guard: the old code did `return True` inside the except block,
    # treating a describe failure as "disassociation complete". It must not.
    code = _lambda_code()
    marker = "def wait_for_disassociation("
    start = code.index(marker)
    end = code.index("def delete_policy_with_retry(", start)
    wait_fn = code[start:end]
    assert "will retry" in wait_fn  # keeps polling on error instead of returning


def test_lambda_timeout_has_headroom_for_async_teardown():
    timeout = _doc()["Resources"]["PolicyAssociationLambda"]["Properties"]["Timeout"]
    assert timeout == 900


# --- #103 (reopened, Round-4): the disassociation wait declared completion on a
# transient empty read ~2s in (eventual consistency), so delete_configuration_policy
# then 409'd on the still-associated policy and was swallowed, and central config
# could never be disabled. The wait must confirm zero associations across a
# stability window, and the policy delete must retry until the policy is gone. ----

def test_wait_for_disassociation_uses_stability_window():
    # A single transient 0 must not be treated as "done": the wait requires
    # `stable_polls` consecutive zero-count reads before declaring completion.
    code = _lambda_code()
    marker = "def wait_for_disassociation("
    start = code.index(marker)
    end = code.index("def delete_policy_with_retry(", start)
    wait_fn = code[start:end]
    assert "stable_polls" in wait_fn
    assert "consecutive_zero" in wait_fn
    # default window is 3 consecutive zero-count polls
    assert "stable_polls=3" in wait_fn


def test_wait_polls_org_wide_association_list_not_root_batch_get():
    # The transient false positive came from batch_get on only the RootId. The
    # wait must instead page the org-wide association list and count only
    # associations that still reference our policy.
    code = _lambda_code()
    assert "def count_policy_associations(" in code
    assert "list_configuration_policy_associations" in code
    assert "ConfigurationPolicyAssociationSummaries" in code
    assert "NextToken" in code  # paginates the full org-wide list


def test_delete_policy_is_retried_not_swallowed():
    # delete_configuration_policy can still 409 ("associated with one or more
    # accounts") right after the list clears; that conflict must be retried until
    # the policy is gone, and a timeout must fail the resource (not proceed).
    code = _lambda_code()
    assert "def delete_policy_with_retry(" in code
    assert "if not delete_policy_with_retry(policy_id):" in code
    assert "PolicyDeleteTimeout" in code


def test_delete_handler_is_strictly_gated():
    # Each step gates the next: a disassociation timeout must stop before deleting
    # the policy, and both must precede disabling central configuration.
    code = _lambda_code()
    assert "if not wait_for_disassociation(policy_id):" in code
    assert "DisassociationTimeout" in code


def test_role_can_list_configuration_policy_associations():
    assert _role_grants("securityhub:ListConfigurationPolicyAssociations")
