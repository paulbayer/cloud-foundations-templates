"""
Tests for #107: honor vpcFlowLogs.enabled=false.

Two coupled behaviors:
  1. finalize_parameters sets tEnableVpcFlowLogs from the flow-logs-enabled
     decision, separate from the bucket decision. So a bucket that exists only
     for Network Firewall logging does not resurrect the per-VPC flow log.
  2. Every network template that creates an AWS::EC2::FlowLog gates it on an
     EnableVpcFlowLogs condition, so tEnableVpcFlowLogs=false suppresses it.
"""

from pathlib import Path

from titanium_generator.processors.network_processor import NetworkProcessor

import titanium_generator

TEMPLATE_DIR = (
    Path(titanium_generator.__file__).parent / "mcp_tools" / "templates" / "network"
)

FLOW_LOG_TEMPLATES = [
    "04a-tgw-stackset-network-egress-vpc.yaml",
    "04b-tgw-stackset-network-inspection-vpc-firewall.yaml",
    "05-dns-stackset-network-resolver.yaml",
    "06-vpc-stackset-network-endpoint-vpc.yaml",
    "07-vpc-stackset-network-workload-vpc.yaml",
]


def _finalize(full_config, config_items=None):
    processor = NetworkProcessor()
    processor.set_full_config(full_config)
    updates = {}
    processor.finalize_parameters(config_items or [], updates)
    return updates


def test_flow_logs_disabled_sets_enable_false():
    updates = _finalize({"vpcFlowLogs": {"enabled": False, "destinations": []}})
    assert updates["tEnableVpcFlowLogs"] == "false"
    assert updates["tDeployVPCFlowLogsBucket"] == "false"


def test_flow_logs_enabled_sets_enable_true():
    updates = _finalize({"vpcFlowLogs": {"enabled": True, "destinations": ["s3"]}})
    assert updates["tEnableVpcFlowLogs"] == "true"
    assert updates["tDeployVPCFlowLogsBucket"] == "true"


def test_firewall_keeps_bucket_but_not_flow_logs():
    # Firewall forces the bucket (its logging config needs S3) but the per-VPC
    # flow log stays off because the user disabled flow logs.
    items = [{"type": "inspection_vpc", "enabled": True, "config": {"networkFirewall": True}}]
    updates = _finalize({"vpcFlowLogs": {"enabled": False, "destinations": []}}, items)
    assert updates["tDeployVPCFlowLogsBucket"] == "true"
    assert updates["tEnableVpcFlowLogs"] == "false"


def test_every_flow_log_template_gates_on_enable_param():
    for name in FLOW_LOG_TEMPLATES:
        text = (TEMPLATE_DIR / name).read_text()
        assert "tEnableVpcFlowLogs" in text, name
        assert "EnableVpcFlowLogs" in text, name
        # The flow-log resource condition must reference the enable gate.
        assert "CreateVpcFlowLogs" in text, name
