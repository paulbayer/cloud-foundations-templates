"""
Tests for #100: the centralized VPC Flow Logs bucket StackSet (network/03) must
not be generated when the bucket is not needed.

finalize_parameters set tDeployVPCFlowLogsBucket but that only toggles a
parameter — the template file was still emitted (and the S3 bucket deployed in
Log Archive) even when flow logs were disabled (vpcFlowLogs.enabled=false,
destinations=[]). The skip is now enforced at generation time by
should_skip_template, matching obs-081/082/095.
"""

from titanium_generator.processors.network_processor import NetworkProcessor

BUCKET_TEMPLATE = "03-vpc-stackset-logarchive-flowlogs-bucket.yaml"
SKIP_REASON = "VPC flow logs bucket not enabled in configuration"


def _network(inspection=False, firewall=False):
    """A network config with TGW present and an optional inspection VPC."""
    vpcs = {}
    if inspection:
        vpcs["inspectionVpc"] = {"enabled": True, "networkFirewall": firewall}
    return {"tgwArchitecture": {"transitGateway": {"name": "tgw"}, "vpcs": vpcs}}


class TestFlowLogsBucketSkip:
    def test_skipped_when_no_destination_and_no_inspection(self):
        processor = NetworkProcessor()
        full_config = {"vpcFlowLogs": {"enabled": False, "destinations": []}}
        reason = processor.should_skip_template(BUCKET_TEMPLATE, _network(), full_config)
        assert reason == SKIP_REASON

    def test_skipped_when_flow_logs_block_absent(self):
        processor = NetworkProcessor()
        reason = processor.should_skip_template(BUCKET_TEMPLATE, _network(), {})
        assert reason == SKIP_REASON

    def test_generated_when_s3_destination(self):
        processor = NetworkProcessor()
        full_config = {"vpcFlowLogs": {"enabled": True, "destinations": ["s3"]}}
        assert processor.should_skip_template(BUCKET_TEMPLATE, _network(), full_config) is None

    def test_skipped_when_inspection_vpc_but_flow_logs_disabled(self):
        # #107 (revising #100): an inspection/egress VPC no longer forces the
        # bucket on when the user disabled flow logs and there is no firewall.
        processor = NetworkProcessor()
        full_config = {"vpcFlowLogs": {"enabled": False, "destinations": []}}
        reason = processor.should_skip_template(BUCKET_TEMPLATE, _network(inspection=True), full_config)
        assert reason == SKIP_REASON

    def test_generated_when_inspection_vpc_flow_logs_enabled(self):
        processor = NetworkProcessor()
        full_config = {"vpcFlowLogs": {"enabled": True, "destinations": []}}
        assert processor.should_skip_template(BUCKET_TEMPLATE, _network(inspection=True), full_config) is None

    def test_generated_when_firewall_even_if_flow_logs_disabled(self):
        # Network Firewall's logging configuration must deliver to S3 and the
        # firewall will not deploy without it, so the bucket is still needed.
        processor = NetworkProcessor()
        full_config = {"vpcFlowLogs": {"enabled": False, "destinations": []}}
        assert processor.should_skip_template(
            BUCKET_TEMPLATE, _network(inspection=True, firewall=True), full_config
        ) is None

    def test_generated_when_pattern_variable_opt_in(self):
        processor = NetworkProcessor()
        processor.set_pattern_variables({"flow_logs_bucket_enabled": True})
        full_config = {"vpcFlowLogs": {"enabled": False, "destinations": []}}
        assert processor.should_skip_template(BUCKET_TEMPLATE, _network(), full_config) is None

    def test_skipped_even_in_minimal_config(self):
        # The bucket is a Log Archive StackSet, independent of the Network account,
        # so the minimal-config early return must not keep it around.
        processor = NetworkProcessor()
        reason = processor.should_skip_template(BUCKET_TEMPLATE, {"deleteDefaultVpcs": True}, {})
        assert reason == SKIP_REASON

    def test_other_network_templates_unaffected(self):
        # Skipping the bucket must not affect the DNS resolver skip logic, etc.
        processor = NetworkProcessor()
        full_config = {"vpcFlowLogs": {"enabled": False, "destinations": []}}
        # DNS resolver enabled -> template 05 must still be generated.
        cfg = _network()
        cfg["tgwArchitecture"]["route53Resolver"] = {"enabled": True}
        assert processor.should_skip_template(
            "05-dns-stackset-network-resolver.yaml", cfg, full_config
        ) is None
