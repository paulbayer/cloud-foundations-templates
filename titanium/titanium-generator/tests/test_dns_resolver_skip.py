"""
Tests for #95: the DNS resolver StackSet (template 05) must not be generated or
deployed when hybrid DNS / Route53 Resolver is disabled.

obs-085 added the interview question for hybrid DNS, but the generator still
modified network/05-dns-stackset-network-resolver.yaml and listed it as a deploy
step even when tgwArchitecture.route53Resolver.enabled=false — which would create
resolver endpoints (~$0.125/hr per ENI) the user opted out of. The skip is now
enforced at generation time by should_skip_template, matching obs-081/082.
"""

from titanium_generator.processors.network_processor import NetworkProcessor

DNS_TEMPLATE = "05-dns-stackset-network-resolver.yaml"


def _network(resolver_enabled=None):
    """A network config with TGW present (advanced features) and optional resolver."""
    tgw_arch = {"transitGateway": {"name": "tgw"}, "vpcs": {}}
    if resolver_enabled is not None:
        tgw_arch["route53Resolver"] = {"enabled": resolver_enabled}
    return {"tgwArchitecture": tgw_arch}


class TestDnsResolverSkip:
    def test_skipped_when_disabled(self):
        processor = NetworkProcessor()
        reason = processor.should_skip_template(DNS_TEMPLATE, _network(False), {})
        assert reason == "Route53 Resolver (hybrid DNS) disabled in configuration"

    def test_generated_when_enabled(self):
        processor = NetworkProcessor()
        assert processor.should_skip_template(DNS_TEMPLATE, _network(True), {}) is None

    def test_skipped_when_block_absent(self):
        # TGW present but no route53Resolver block -> opt-in default False.
        processor = NetworkProcessor()
        reason = processor.should_skip_template(DNS_TEMPLATE, _network(None), {})
        assert reason == "Route53 Resolver (hybrid DNS) disabled in configuration"

    def test_other_network_templates_unaffected_when_resolver_disabled(self):
        # Disabling the resolver must not skip the TGW egress template.
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
