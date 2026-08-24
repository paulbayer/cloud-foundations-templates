"""
Tests for #87: the Workload VPC StackSet (template 07) must never be deployed.

Workload VPCs belong to workload accounts provisioned by Control Tower account
vending; deploying them via a Titanium StackSet wrongly targeted the Network
account. The template stays in the repo but is non-actionable: the network
processor always skips it, workloadVpcs is no longer a Network-account trigger,
and no workload item / parameters are extracted. workloadVpcs derives from the CT
auto_create_workload_vpcs setting, which this solution does not act on.
"""

from titanium_generator.processors.network_processor import NetworkProcessor

WORKLOAD_TEMPLATE = "07-vpc-stackset-network-workload-vpc.yaml"


def _valid_tgw_network(**extra):
    config = {
        "tgwArchitecture": {
            "transitGateway": {"name": "tgw"},
            "vpcs": {"inspectionVpc": {"enabled": True, "networkFirewall": False}},
        }
    }
    config.update(extra)
    return config


class TestWorkloadVpcNeverDeployed:
    def test_template_07_always_skipped(self):
        processor = NetworkProcessor()
        config = _valid_tgw_network(
            workloadVpcs={"enabled": True, "deploymentTargets": {"organizational_units": ["Workloads"]}}
        )
        reason = processor.should_skip_template(WORKLOAD_TEMPLATE, config, {})
        assert reason and "Control Tower account vending" in reason

    def test_template_07_skipped_even_when_workload_disabled(self):
        processor = NetworkProcessor()
        config = _valid_tgw_network(workloadVpcs={"enabled": False})
        assert processor.should_skip_template(WORKLOAD_TEMPLATE, config, {}) is not None


class TestWorkloadVpcsNotATrigger:
    def test_workload_vpcs_alone_does_not_require_network_account(self):
        assert NetworkProcessor.has_advanced_network_features({"workloadVpcs": {"enabled": True}}) is False

    def test_real_advanced_features_still_trigger(self):
        assert NetworkProcessor.has_advanced_network_features(
            {"tgwArchitecture": {"transitGateway": {"name": "t"}}}
        ) is True
        assert NetworkProcessor.has_advanced_network_features({"ipam": {"enabled": True}}) is True


class TestWorkloadVpcsNotExtracted:
    def test_no_workload_item_or_parameters(self):
        processor = NetworkProcessor()
        config = _valid_tgw_network(workloadVpcs={"enabled": True})
        items = processor.extract_items(config)
        assert not any(i["type"] == "workload_vpcs" for i in items)
        updates = processor.generate_parameter_updates(items)
        assert "tDeployWorkloadVpcs" not in updates
