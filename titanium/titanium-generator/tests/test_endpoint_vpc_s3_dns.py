"""
Tests for #88 / #93: the Endpoint VPC S3 interface endpoint must be deployable.

#88: the S3 interface endpoint set PrivateDnsEnabled: true with no S3 gateway
endpoint in the VPC, which AWS rejects. The template adds an S3 gateway endpoint
and scopes the interface endpoint's private DNS to inbound-resolver queries —
AWS's supported pattern for a centralized Endpoint VPC.

#93: DnsOptions.PrivateDnsOnlyForInboundResolverEndpoint is a STRING enum in
CloudFormation (OnlyInboundResolver | AllResolvers | NotSpecified), not a boolean.
obs-088 set it to boolean true, which CloudFormation rejects with an enum
validation error; it must be the string "OnlyInboundResolver".

EC2/SSM interface endpoints are unaffected (they carry no such constraint).
"""

from pathlib import Path

import yaml

import titanium_generator

TEMPLATE = (
    Path(titanium_generator.__file__).parent
    / "mcp_tools" / "templates" / "network"
    / "06-vpc-stackset-network-endpoint-vpc.yaml"
)


class _CfnLoader(yaml.SafeLoader):
    pass


_CfnLoader.add_multi_constructor("!", lambda loader, suffix, node: None)


def _resources():
    return yaml.load(TEMPLATE.read_text(), Loader=_CfnLoader)["Resources"]


def test_s3_gateway_endpoint_present():
    res = _resources()
    assert "S3GatewayEndpoint" in res
    gw = res["S3GatewayEndpoint"]["Properties"]
    assert gw["VpcEndpointType"] == "Gateway"
    assert "RouteTableIds" in gw  # gateway endpoints attach to route tables
    # Only meaningful when central endpoints are enabled.
    assert res["S3GatewayEndpoint"]["Condition"] == "EnableCentralEndpoints"


def test_s3_interface_endpoint_scoped_private_dns():
    s3 = _resources()["S3InterfaceEndpoint"]
    # Depends on the gateway endpoint so the AWS validation passes at deploy time.
    assert s3.get("DependsOn") == "S3GatewayEndpoint"
    props = s3["Properties"]
    assert props["PrivateDnsEnabled"] is True
    # #93: string enum value, not a boolean — CloudFormation rejects `true`.
    assert props["DnsOptions"] == {
        "PrivateDnsOnlyForInboundResolverEndpoint": "OnlyInboundResolver"
    }


def test_other_interface_endpoints_unchanged():
    res = _resources()
    for name in ("EC2InterfaceEndpoint", "SSMInterfaceEndpoint"):
        props = res[name]["Properties"]
        assert props["PrivateDnsEnabled"] is True
        # No gateway-endpoint constraint for these services, so no DnsOptions.
        assert "DnsOptions" not in props
