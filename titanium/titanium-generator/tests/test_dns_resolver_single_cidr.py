"""
Test for #112: network/05 DNS resolver must support a single allowed source CIDR
(and a single on-prem DNS server) without crashing.

Conditions resolve eagerly, so the old `HasMultipleCidrs: !Not [!Equals
[!Select [1, !Ref tAllowedSourceCidrs], ""]]` threw "Fn::Select cannot select
nonexistent value at index 1" at parse time for a 1-element list, rolling back
the stack. Likewise the OnPremDomainResolverRule hard-coded a second TargetIp via
`!Select [1, !Ref tOnPremDnsServers]`, crashing at deploy for one DNS server.

This test loads the template preserving CFN intrinsics and evaluates the two
conditions (and the gated second TargetIp) for 1- and 2-element inputs, proving
no index error and correct behaviour.
"""

from pathlib import Path

import pytest
import yaml

import titanium_generator

TEMPLATE = (
    Path(titanium_generator.__file__).parent
    / "mcp_tools" / "templates" / "network"
    / "05-dns-stackset-network-resolver.yaml"
)

NO_VALUE = object()  # stand-in for AWS::NoValue


class _CfnLoader(yaml.SafeLoader):
    pass


def _cfn_multi(loader, suffix, node):
    if suffix == "Ref":
        key = "Ref"
    elif suffix == "Condition":
        key = "Condition"
    else:
        key = "Fn::" + suffix
    if isinstance(node, yaml.ScalarNode):
        val = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        val = loader.construct_sequence(node, deep=True)
    else:
        val = loader.construct_mapping(node, deep=True)
    return {key: val}


_CfnLoader.add_multi_constructor("!", _cfn_multi)


def _doc():
    return yaml.load(TEMPLATE.read_text(), Loader=_CfnLoader)


def _ev(node, params, conditions=None):
    """Minimal evaluator for the CFN intrinsics used in the conditions/target."""
    conditions = conditions or {}
    if isinstance(node, dict) and len(node) == 1 and next(iter(node)) in (
        "Ref", "Fn::Select", "Fn::Split", "Fn::Join", "Fn::Equals", "Fn::Not", "Fn::If",
    ):
        (k, v), = node.items()
        if k == "Ref":
            if v == "AWS::NoValue":
                return NO_VALUE
            return params[v]
        if k == "Fn::Select":
            idx, lst = v
            idx = int(_ev(idx, params, conditions))
            return _ev(lst, params, conditions)[idx]  # raises IndexError if OOB
        if k == "Fn::Split":
            delim, s = v
            return _ev(s, params, conditions).split(_ev(delim, params, conditions))
        if k == "Fn::Join":
            delim, items = v
            return _ev(delim, params, conditions).join(_ev(items, params, conditions))
        if k == "Fn::Equals":
            a, b = v
            return _ev(a, params, conditions) == _ev(b, params, conditions)
        if k == "Fn::Not":
            (x,) = v
            return not _ev(x, params, conditions)
        if k == "Fn::If":
            cond, t, f = v
            return _ev(t if conditions[cond] else f, params, conditions)
    if isinstance(node, dict):
        # ordinary mapping (e.g. {Ip: ..., Port: 53}) -> recurse into values
        return {k: _ev(v, params, conditions) for k, v in node.items()}
    if isinstance(node, list):
        return [_ev(i, params, conditions) for i in node]
    return node


def _conditions():
    return _doc()["Conditions"]


@pytest.mark.parametrize("cidrs,expected", [
    (["10.10.0.0/16"], False),
    (["192.168.0.0/16", "10.0.0.0/8"], True),
])
def test_has_multiple_cidrs_no_crash_and_correct(cidrs, expected):
    cond = _conditions()["HasMultipleCidrs"]
    assert _ev(cond, {"tAllowedSourceCidrs": cidrs}) is expected


@pytest.mark.parametrize("servers,expected", [
    (["192.168.0.10"], False),
    (["192.168.0.10", "192.168.0.11"], True),
])
def test_has_multiple_dns_servers_no_crash_and_correct(servers, expected):
    cond = _conditions()["HasMultipleDnsServers"]
    assert _ev(cond, {"tOnPremDnsServers": servers}) is expected


def _target_ips():
    return _doc()["Resources"]["OnPremDomainResolverRule"]["Properties"]["TargetIps"]


def test_single_dns_server_drops_second_target_ip():
    servers = ["192.168.0.10"]
    conditions = {"HasMultipleDnsServers": False}
    resolved = [_ev(t, {"tOnPremDnsServers": servers}, conditions) for t in _target_ips()]
    assert resolved[0] == {"Ip": "192.168.0.10", "Port": 53}
    assert resolved[1] is NO_VALUE  # AWS::NoValue -> item removed by CFN


def test_two_dns_servers_keep_both_target_ips():
    servers = ["192.168.0.10", "192.168.0.11"]
    conditions = {"HasMultipleDnsServers": True}
    resolved = [_ev(t, {"tOnPremDnsServers": servers}, conditions) for t in _target_ips()]
    assert resolved[0] == {"Ip": "192.168.0.10", "Port": 53}
    assert resolved[1] == {"Ip": "192.168.0.11", "Port": 53}
