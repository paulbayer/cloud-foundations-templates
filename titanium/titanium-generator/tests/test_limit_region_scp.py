"""
Tests for #101 (generator side): the LimitRegionUsage SCP allowed-regions must be
derived from the config's enabledRegions, not left at the hardcoded template
default (us-east-1,us-west-2) that the deploy guide auto-resolves and hides.

us-east-1 is always included for global-service control-plane reachability.
"""

from titanium_generator.processors.organization_processor import SimpleOrganizationProcessor


def _derive(enabled_regions):
    processor = SimpleOrganizationProcessor()
    full_config = {"organization": {}}
    if enabled_regions is not None:
        full_config["enabledRegions"] = enabled_regions
    processor.set_full_config(full_config)
    updates = {}
    processor.finalize_parameters([], updates)
    return updates


def test_allowed_regions_derived_from_enabled_regions():
    updates = _derive(["us-west-2"])
    assert updates["tLimitRegionUsageAllowedRegions"] == "us-west-2,us-east-1"


def test_us_east_1_not_duplicated_when_already_present():
    updates = _derive(["us-east-1", "us-west-2"])
    assert updates["tLimitRegionUsageAllowedRegions"] == "us-east-1,us-west-2"


def test_multi_region_selection_preserved_plus_global():
    updates = _derive(["eu-west-2", "eu-central-1"])
    assert updates["tLimitRegionUsageAllowedRegions"] == "eu-west-2,eu-central-1,us-east-1"


def test_no_override_when_enabled_regions_absent():
    # No enabledRegions -> leave the template default untouched.
    updates = _derive(None)
    assert "tLimitRegionUsageAllowedRegions" not in updates
