"""
Tests for #82: IPAM delegation (01) and sharing (02) must not be generated or
deployed when IPAM is disabled.

With ipam.enabled=false the generator set tDeployIPAM=false but still emitted
templates 01/02, deploying an empty StackSet + org-wide instances that provision
nothing. The network processor now skips both when IPAM is disabled, using the
same enabled-resolution as extract_items (single source of truth).
"""

import pytest

from titanium_generator.processors.network_processor import NetworkProcessor

IPAM_TEMPLATES = [
    "01-ipam-stack-mgmt-delegation.yaml",
    "02-ipam-stackset-network-sharing.yaml",
]


def _network(ipam):
    """TGW present (advanced features) plus an optional ipam block (dict or None)."""
    config = {"tgwArchitecture": {"transitGateway": {"name": "tgw"}}}
    if ipam is not None:
        config["ipam"] = ipam
    return config


class TestIpamTemplateSkip:
    @pytest.mark.parametrize("template", IPAM_TEMPLATES)
    def test_skipped_when_disabled(self, template):
        processor = NetworkProcessor()
        reason = processor.should_skip_template(template, _network({"enabled": False}), {})
        assert reason == "IPAM disabled in configuration"

    @pytest.mark.parametrize("template", IPAM_TEMPLATES)
    def test_generated_when_enabled(self, template):
        processor = NetworkProcessor()
        assert processor.should_skip_template(template, _network({"enabled": True}), {}) is None

    @pytest.mark.parametrize("template", IPAM_TEMPLATES)
    def test_skipped_when_block_absent(self, template):
        processor = NetworkProcessor()
        reason = processor.should_skip_template(template, _network(None), {})
        assert reason == "IPAM disabled in configuration"

    @pytest.mark.parametrize("template", IPAM_TEMPLATES)
    def test_default_on_quirk_preserved(self, template):
        # An ipam block present without an explicit enabled flag counts as enabled,
        # matching extract_items so generation and skipping never disagree.
        processor = NetworkProcessor()
        assert processor.should_skip_template(template, _network({"pools": []}), {}) is None


class TestIpamEnabledHelperMatchesExtractItems:
    """_ipam_enabled is the single source of truth used by extract_items."""

    def test_helper_and_extract_items_agree(self):
        processor = NetworkProcessor()
        for ipam, expected in [
            ({"enabled": False}, False),
            ({"enabled": True}, True),
            ({"pools": []}, True),   # default-on quirk
            (None, False),
        ]:
            section = _network(ipam)
            assert processor._ipam_enabled(section) is expected
            items = processor.extract_items(section)
            ipam_items = [i for i in items if i["type"] == "ipam"]
            if ipam is None:
                assert not ipam_items  # no block, no item
            else:
                assert ipam_items and ipam_items[0]["enabled"] is expected
