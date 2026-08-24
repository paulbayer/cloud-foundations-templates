"""
Regression tests for build_organizational_units (issue #76).

The advisor used to hardcode a four-OU list, discarding whatever each industry
overlay declared in its pattern.json. These tests assert the advisor now emits
the overlay's declared organizational_units verbatim and still merges any
additional OUs collected during the interview.
"""
import json
import sys
from pathlib import Path

import pytest

# server.py lives in the hyphenated mcp-server/ dir, which is not an importable
# package name; add it to sys.path so `import server` works.
MCP_SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MCP_SERVER_DIR))

import server  # noqa: E402

INDUSTRY_DIR = server.INDUSTRY_DIR


def _declared_ous(overlay):
    """Load an overlay's declared organizational_units from pattern.json."""
    pattern = json.loads((INDUSTRY_DIR / overlay / "pattern.json").read_text())
    return pattern["template_variables"]["organizational_units"]


def _names(ous):
    return [ou["name"] for ou in ous]


@pytest.mark.parametrize(
    "overlay", ["starter", "enterprise", "us-government", "uk-public-sector"]
)
def test_emits_overlay_declared_list_verbatim(overlay):
    declared = _declared_ous(overlay)
    result = server.build_organizational_units(declared)
    assert result == declared


@pytest.mark.parametrize(
    "overlay", ["starter", "us-government", "uk-public-sector"]
)
def test_exceptions_ou_preserved(overlay):
    result = server.build_organizational_units(_declared_ous(overlay))
    assert "Exceptions" in _names(result)


def test_enterprise_includes_development_and_production():
    result = server.build_organizational_units(_declared_ous("enterprise"))
    names = _names(result)
    assert "Development" in names
    assert "Production" in names


def test_generic_overlay_falls_back_to_base_four():
    # The generic overlay has no pattern.json, so declared_ous is None.
    result = server.build_organizational_units(None)
    assert _names(result) == ["Security", "Infrastructure", "Workloads", "Sandbox"]


def test_additional_ous_merge_onto_declared_list():
    result = server.build_organizational_units(
        _declared_ous("starter"), "Development, Production"
    )
    names = _names(result)
    assert "Development" in names
    assert "Production" in names
    # The overlay's own OUs are still present.
    assert "Exceptions" in names


def test_additional_ous_dedup_against_declared_and_each_other():
    # "Sandbox" already exists in starter; "Foo" is repeated in the input.
    result = server.build_organizational_units(
        _declared_ous("starter"), "Sandbox, Foo, Foo"
    )
    names = _names(result)
    assert names.count("Sandbox") == 1
    assert names.count("Foo") == 1


def test_declared_list_not_mutated():
    declared = _declared_ous("starter")
    before = _names(declared)
    server.build_organizational_units(declared, "Foo")
    assert _names(declared) == before
