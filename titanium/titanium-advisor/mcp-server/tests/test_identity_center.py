"""
Tests for the Identity Center assumption in the advisor (issue #77).

The advisor used to read variables.get("identity_center_enabled") — a key no
pattern defines — so it always emitted enableIdentityCenterAccess: false. It now
pins the field to True, reflecting the assumption that the externally-provisioned
Control Tower manages IAM Identity Center. The value must be True regardless of
what the overlay's identity_center_access says.
"""
import json
import sys
from pathlib import Path

import pytest
import yaml

MCP_SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MCP_SERVER_DIR))

import server  # noqa: E402


def _emit_config(monkeypatch, industry):
    """Drive generate_deterministic_titanium_config with a minimal complete session."""
    session_id = "testses1"
    server.interview_sessions[session_id] = {
        "session_id": session_id,
        "industry": industry,
        "responses": {
            "organization_name": "Acme",
            "email_domain": "acme.example",
            "home_region": "us-east-1",
        },
        "answers": {},
        "all_questions": [],
    }
    # The interview-completeness gate is orthogonal to what we're asserting.
    monkeypatch.setattr(
        server, "validate_interview_complete",
        lambda sid: json.dumps({"complete": True}),
    )
    try:
        output = server.generate_deterministic_titanium_config(session_id=session_id)
    finally:
        server.interview_sessions.pop(session_id, None)
    # The leading header lines are YAML comments, so the whole string parses.
    return yaml.safe_load(output)


@pytest.mark.parametrize("industry", ["starter", "enterprise", "us-government"])
def test_identity_center_access_pinned_true(monkeypatch, industry):
    config = _emit_config(monkeypatch, industry)
    security = config["controlTower"]["landingZone"]["security"]
    assert security["enableIdentityCenterAccess"] is True
