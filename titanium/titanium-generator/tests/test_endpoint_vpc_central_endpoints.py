"""
Tests for #92: enabling the Endpoint VPC must turn its central endpoints on.

template 06 gates every endpoint (S3 gateway, S3/EC2/SSM interface endpoints, and
the endpoint security group) on the tCentralEndpoints parameter. The advisor never
emits endpointVpc.centralEndpoints, so the generator defaulting it to False produced
a green-but-empty endpoint VPC (VPC + subnets + flow logs, zero endpoints). The
generator now defaults it to True — matching template 06's own default — while still
honoring an explicit centralEndpoints: false as an advanced opt-out.
"""

from titanium_generator.processors.network_processor import NetworkProcessor


def _endpoint_item(config):
    # Shape matches what extract_items builds for an enabled endpoint VPC.
    return {
        "name": "EndpointVpc",
        "type": "endpoint_vpc",
        "enabled": True,
        "config": config,
    }


class TestCentralEndpointsDefault:
    def test_enabled_endpoint_vpc_turns_endpoints_on(self):
        # No centralEndpoints key (the advisor-driven case) -> endpoints ON.
        processor = NetworkProcessor()
        updates = {}
        processor._handle_vpc(_endpoint_item({}), updates)
        assert updates["tCentralEndpoints"] == "true"

    def test_explicit_true_is_honored(self):
        processor = NetworkProcessor()
        updates = {}
        processor._handle_vpc(_endpoint_item({"centralEndpoints": True}), updates)
        assert updates["tCentralEndpoints"] == "true"

    def test_explicit_false_is_honored_as_opt_out(self):
        processor = NetworkProcessor()
        updates = {}
        processor._handle_vpc(_endpoint_item({"centralEndpoints": False}), updates)
        assert updates["tCentralEndpoints"] == "false"
