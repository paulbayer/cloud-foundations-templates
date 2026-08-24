"""
Tests for #98: the DNS resolver StackSet (network/05) RAM ResourceShare must
share with OU *ARNs*, not raw OU IDs.

The ShareWithSpecificOUs branch used to pass !Ref uOrganizationalUnitIds (raw
ou-xxxx IDs) to RAM Principals, which RAM rejects with "Principal ID is
malformed", rolling back the whole 05 stack. CloudFormation cannot build ARNs
from a CommaDelimitedList of IDs, so the parameter now takes full OU ARNs
(uOrganizationalUnitArns) and the branch references it directly.
"""

from pathlib import Path

import yaml

import titanium_generator

TEMPLATE = (
    Path(titanium_generator.__file__).parent
    / "mcp_tools" / "templates" / "network"
    / "05-dns-stackset-network-resolver.yaml"
)


class _CfnLoader(yaml.SafeLoader):
    pass


def _tag(loader, suffix, node):
    """Preserve CloudFormation intrinsics as {"!Tag": value} so we can assert on them."""
    key = f"!{suffix}"
    if isinstance(node, yaml.ScalarNode):
        return {key: loader.construct_scalar(node)}
    if isinstance(node, yaml.SequenceNode):
        return {key: loader.construct_sequence(node, deep=True)}
    return {key: loader.construct_mapping(node, deep=True)}


_CfnLoader.add_multi_constructor("!", _tag)


def _doc():
    return yaml.load(TEMPLATE.read_text(), Loader=_CfnLoader)


def test_template_still_parses():
    # Guard: the edits keep the template well-formed.
    assert _doc()["Resources"]["DNSProfileResourceShare"]["Type"] == "AWS::RAM::ResourceShare"


def test_arns_parameter_replaces_ids():
    params = _doc()["Parameters"]
    assert "uOrganizationalUnitArns" in params
    assert "uOrganizationalUnitIds" not in params
    assert params["uOrganizationalUnitArns"]["Type"] == "CommaDelimitedList"


def test_specific_ou_branch_uses_arn_param():
    principals = _doc()["Resources"]["DNSProfileResourceShare"]["Properties"]["Principals"]
    # Principals: !If [ShareWithSpecificOUs, <specific-OU branch>, <org-wide branch>]
    if_args = principals["!If"]
    assert if_args[0] == "ShareWithSpecificOUs"
    # The specific-OU branch must reference the ARN param, never raw OU IDs.
    assert if_args[1] == {"!Ref": "uOrganizationalUnitArns"}


def test_no_raw_ou_id_reference_anywhere():
    # Belt-and-suspenders: the old ID-based param name is gone from the whole template.
    assert "uOrganizationalUnitIds" not in TEMPLATE.read_text()
