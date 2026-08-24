"""
Tests for #81: the Endpoint VPC StackSet (template 06) must not be generated or
deployed when it is disabled.

network/06-vpc-stackset-network-endpoint-vpc.yaml has no whole-template deploy
gate internally, so opting out (tgwArchitecture.vpcs.endpointVpc.enabled=false)
is enforced at generation time by the network processor's should_skip_template,
and the deployment-guide selector is aligned to the same default.
"""

from titanium_generator.processors.network_processor import NetworkProcessor

ENDPOINT_TEMPLATE = "06-vpc-stackset-network-endpoint-vpc.yaml"


def _network(endpoint_enabled=None):
    """A network config with TGW present (advanced features) and optional endpointVpc."""
    vpcs = {}
    if endpoint_enabled is not None:
        vpcs["endpointVpc"] = {"enabled": endpoint_enabled}
    return {"tgwArchitecture": {"transitGateway": {"name": "tgw"}, "vpcs": vpcs}}


class TestEndpointVpcSkip:
    def test_skipped_when_disabled(self):
        processor = NetworkProcessor()
        reason = processor.should_skip_template(ENDPOINT_TEMPLATE, _network(False), {})
        assert reason == "Endpoint VPC disabled in configuration"

    def test_generated_when_enabled(self):
        processor = NetworkProcessor()
        assert processor.should_skip_template(ENDPOINT_TEMPLATE, _network(True), {}) is None

    def test_skipped_when_block_absent(self):
        # Hand-written config with TGW but no endpointVpc block → opt-in default False.
        processor = NetworkProcessor()
        reason = processor.should_skip_template(ENDPOINT_TEMPLATE, _network(None), {})
        assert reason == "Endpoint VPC disabled in configuration"

    def test_other_network_templates_unaffected_when_endpoint_disabled(self):
        # Disabling the endpoint VPC must not skip the TGW egress template.
        processor = NetworkProcessor()
        config = _network(False)
        config["tgwArchitecture"]["vpcs"]["inspectionVpc"] = {
            "enabled": True,
            "networkFirewall": False,
        }
        assert (
            processor.should_skip_template(
                "04a-tgw-stackset-network-egress-vpc.yaml", config, {}
            )
            is None
        )
