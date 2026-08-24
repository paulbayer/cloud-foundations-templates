"""
Tests for #86: the advisor must not emit an inert vpcFlowLogs bucket name.

The advisor used to write vpcFlowLogs.destinationsConfig.s3.bucketName, but the
generator derives the flow-logs bucket name deterministically at deploy time
(titanium-vpc-flow-logs-<accountId>-<region>) and ignores any configured name —
so the field was inert, misleading, and not in the schema. destinationsConfig now
mirrors the reference Titanium.yaml / schema shape (cloudWatchLogs.retentionInDays).
"""
import json
import sys
from pathlib import Path

import yaml

MCP_SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MCP_SERVER_DIR))

import server  # noqa: E402


def _emit(monkeypatch, responses):
    sid = "flowtest"
    server.interview_sessions[sid] = {
        "session_id": sid,
        "industry": "starter",
        "responses": {
            "organization_name": "Acme Corp",
            "email_domain": "acme.example",
            "home_region": "us-east-1",
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


def test_no_bucket_name_emitted(monkeypatch):
    cfg = _emit(monkeypatch, {"flow_logs_enabled": True})
    # No bucket name anywhere in the flow-logs block — the generator derives it.
    assert "bucketName" not in json.dumps(cfg["vpcFlowLogs"])
    assert "s3" not in cfg["vpcFlowLogs"].get("destinationsConfig", {})


def test_destinations_config_matches_schema_shape(monkeypatch):
    cfg = _emit(monkeypatch, {"flow_logs_enabled": True, "log_retention_days": 120})
    fl = cfg["vpcFlowLogs"]
    # destinationsConfig uses the schema-defined cloudWatchLogs.retentionInDays,
    # consistent with the top-level retentionDays (same value).
    assert fl["destinationsConfig"]["cloudWatchLogs"]["retentionInDays"] == 120
    assert fl["retentionDays"] == 120


def test_disabled_flow_logs_has_empty_destinations_config(monkeypatch):
    cfg = _emit(monkeypatch, {"flow_logs_enabled": False})
    assert cfg["vpcFlowLogs"]["destinationsConfig"] == {}


def test_field_not_in_schema(monkeypatch):
    # Guard: the schema has no s3/bucketName under vpcFlowLogs.destinationsConfig.
    schema = json.loads((MCP_SERVER_DIR.parent / "core" / "templates" / "schemas" / "titanium-schema.json").read_text())
    dcfg = schema["properties"]["vpcFlowLogs"]["properties"]["destinationsConfig"]["properties"]
    assert "s3" not in dcfg
    assert "cloudWatchLogs" in dcfg
