"""
Tests for #101 (advisor side): enabledRegions must reflect the user's region
selection, not the pattern default.

Previously, when regions were NOT restricted the advisor fell back to the
pattern default (["us-east-1"]) + home, so enabledRegions listed a region the
landing zone never deploys to (StackSets target the home region). Now:
  - restrict_regions=false -> enabledRegions == [home]
  - restrict_regions=true  -> enabledRegions == the interview's allowed_regions,
    with home ensured present, and no unbidden us-east-1.
"""
import json
import sys
from pathlib import Path

import yaml

MCP_SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MCP_SERVER_DIR))

import server  # noqa: E402


def _emit(monkeypatch, responses):
    sid = "regiontest"
    server.interview_sessions[sid] = {
        "session_id": sid,
        "industry": "starter",
        "responses": {
            "organization_name": "Acme Corp",
            "email_domain": "acme.example",
            **responses,
        },
        "answers": {},
        "all_questions": [],
    }
    monkeypatch.setattr(server, "validate_interview_complete", lambda s: json.dumps({"complete": True}))
    try:
        return yaml.safe_load(server.generate_deterministic_titanium_config(session_id=sid))
    finally:
        server.interview_sessions.pop(sid, None)


def test_unrestricted_regions_is_home_only(monkeypatch):
    cfg = _emit(monkeypatch, {"home_region": "us-west-2", "scp_restrict_regions": False})
    assert cfg["enabledRegions"] == ["us-west-2"]
    assert "us-east-1" not in cfg["enabledRegions"]


def test_restricted_regions_use_selection_no_phantom(monkeypatch):
    cfg = _emit(monkeypatch, {
        "home_region": "us-west-2",
        "scp_restrict_regions": True,
        "allowed_regions": ["us-west-2"],
    })
    assert cfg["enabledRegions"] == ["us-west-2"]
    assert "us-east-1" not in cfg["enabledRegions"]


def test_restricted_regions_ensure_home_present(monkeypatch):
    cfg = _emit(monkeypatch, {
        "home_region": "us-west-2",
        "scp_restrict_regions": True,
        "allowed_regions": ["eu-west-1"],
    })
    assert "us-west-2" in cfg["enabledRegions"]
    assert "eu-west-1" in cfg["enabledRegions"]
    assert "us-east-1" not in cfg["enabledRegions"]


# --- #106: discovery-type allowed_regions must geo-map/validate, not comma-split ---

def test_descriptive_phrase_with_embedded_code_does_not_emit_bogus(monkeypatch):
    # The reported repro: a comma inside a descriptive phrase must not leak
    # fragments like "US West only (Oregon" / "us-west-2)" into enabledRegions.
    cfg = _emit(monkeypatch, {
        "home_region": "us-west-2",
        "scp_restrict_regions": True,
        "allowed_regions": "US West only (Oregon, us-west-2)",
    })
    assert cfg["enabledRegions"] == ["us-west-2"]


def test_pure_geo_phrase_is_mapped(monkeypatch):
    # A phrase with no region code but a recognizable place maps via alias.
    cfg = _emit(monkeypatch, {
        "home_region": "us-east-1",
        "scp_restrict_regions": True,
        "allowed_regions": "London and Frankfurt",
    })
    assert set(cfg["enabledRegions"]) == {"us-east-1", "eu-west-2", "eu-central-1"}


def test_region_code_csv_still_parses(monkeypatch):
    # A clean region-code CSV keeps parsing into the two valid regions.
    cfg = _emit(monkeypatch, {
        "home_region": "us-west-2",
        "scp_restrict_regions": True,
        "allowed_regions": "us-west-2, us-east-2",
    })
    assert cfg["enabledRegions"] == ["us-west-2", "us-east-2"]


def test_unmappable_free_text_falls_back_to_home(monkeypatch):
    # Nothing resolvable -> fall back to [home], never a bogus token.
    cfg = _emit(monkeypatch, {
        "home_region": "us-west-2",
        "scp_restrict_regions": True,
        "allowed_regions": "somewhere sunny",
    })
    assert cfg["enabledRegions"] == ["us-west-2"]


# --- #110: discovery-type home_region must geo-map, not leak the raw phrase ---

def test_normalize_home_region_maps_descriptive_phrase():
    # The reported repro: a descriptive place phrase resolves to its region code.
    assert server._normalize_home_region("Portland, Oregon, USA") == "us-west-2"


def test_normalize_home_region_recovers_embedded_code():
    assert server._normalize_home_region("US West (us-west-2)") == "us-west-2"


def test_normalize_home_region_passes_through_clean_code():
    assert server._normalize_home_region("eu-west-2") == "eu-west-2"


def test_normalize_home_region_falls_back_when_unresolvable():
    # Unrecognized answer is left intact rather than mangled.
    assert server._normalize_home_region("somewhere sunny") == "somewhere sunny"


def test_home_region_phrase_does_not_leak_into_config(monkeypatch):
    # End-to-end: a descriptive home_region must not leak verbatim into the
    # generated config's homeRegion/enabledRegions (deploy-breaking, #110).
    cfg = _emit(monkeypatch, {
        "home_region": "Portland, Oregon, USA",
        "scp_restrict_regions": False,
    })
    assert cfg["homeRegion"] == "us-west-2"
    assert cfg["enabledRegions"] == ["us-west-2"]


# --- #110 (Round-4): an unresolved home_region must FAIL LOUD, not leak. The
# geo-alias table is a small convenience set (not a worldwide gazetteer), so the
# guardrail is refusing to generate + rejecting at validation, not endlessly
# expanding the table. ------------------------------------------------------------

def test_is_aws_region_code():
    assert server._is_aws_region_code("us-west-2")
    assert server._is_aws_region_code("ap-southeast-4")
    assert server._is_aws_region_code("  eu-central-1  ")  # tolerates surrounding space
    assert not server._is_aws_region_code("Seattle, Washington, USA")
    assert not server._is_aws_region_code("Washington")
    assert not server._is_aws_region_code("")
    assert not server._is_aws_region_code(None)


def _emit_raw(monkeypatch, responses):
    """Like _emit but returns the raw tool output (may be a rejection, not YAML)."""
    sid = "regiontest_raw"
    server.interview_sessions[sid] = {
        "session_id": sid,
        "industry": "starter",
        "responses": {
            "organization_name": "Acme Corp",
            "email_domain": "acme.example",
            **responses,
        },
        "answers": {},
        "all_questions": [],
    }
    monkeypatch.setattr(server, "validate_interview_complete",
                        lambda s: json.dumps({"complete": True}))
    try:
        return server.generate_deterministic_titanium_config(session_id=sid)
    finally:
        server.interview_sessions.pop(sid, None)


def test_generator_refuses_unmapped_home_region(monkeypatch):
    # An unrecognized location must NOT produce a config; the generator returns
    # a directive rejection so the agent re-asks the user for a real region.
    out = _emit_raw(monkeypatch, {
        "home_region": "Seattle, Washington, USA",
        "scp_restrict_regions": False,
    })
    payload = json.loads(out)  # rejection is directive JSON, not YAML config
    assert "⛔_REJECTED" in payload
    assert any("update_answer" in step for step in payload["⚠️_WHAT_YOU_MUST_DO_NOW"])
    # The offending raw answer is surfaced so the agent/user knows what to fix.
    assert "Seattle, Washington, USA" in payload["error"]


def test_generator_still_emits_for_mapped_home_region(monkeypatch):
    # Guardrail must not regress the mapped path: a resolvable phrase still
    # generates a clean config.
    cfg = yaml.safe_load(_emit_raw(monkeypatch, {
        "home_region": "Portland, Oregon, USA",
        "scp_restrict_regions": False,
    }))
    assert cfg["homeRegion"] == "us-west-2"


def test_validate_rejects_non_region_home_region():
    cfg = (
        "homeRegion: Seattle, Washington, USA\n"
        "enabledRegions: [us-west-2]\n"
        "managementAccountAccessRole: x\ncontrolTower: {}\norganization: {}\n"
        "logging: {}\ncentralSecurityServices: {}\naccounts: {}\nnetwork: {}\n"
    )
    result = server.validate_titanium_config(cfg)
    assert "❌ homeRegion" in result


def test_validate_rejects_non_region_enabled_regions():
    cfg = (
        "homeRegion: us-west-2\n"
        "enabledRegions:\n- Seattle, Washington, USA\n- us-west-2\n"
        "managementAccountAccessRole: x\ncontrolTower: {}\norganization: {}\n"
        "logging: {}\ncentralSecurityServices: {}\naccounts: {}\nnetwork: {}\n"
    )
    result = server.validate_titanium_config(cfg)
    assert "❌ enabledRegions contains non-region values" in result


def test_validate_accepts_valid_regions():
    cfg = (
        "homeRegion: us-west-2\n"
        "enabledRegions: [us-west-2, eu-west-2]\n"
        "managementAccountAccessRole: x\ncontrolTower: {}\norganization: {}\n"
        "logging: {}\ncentralSecurityServices: {}\naccounts: {}\nnetwork: {}\n"
    )
    result = server.validate_titanium_config(cfg)
    assert "❌ homeRegion" not in result
    assert "❌ enabledRegions" not in result
