"""
Tests for #117: centralized VPC flow logs are S3-only.

The generator/templates only ever create an S3 flow log for the centralized
Inspection/Egress VPC (04b hardcodes LogDestinationType: s3; the network
processor never reads cloudwatch/both). The advisor used to offer
flow_log_destination = cloudwatch/both and even cost-estimate a CloudWatch flow
log, so the user's choice was silently ignored on deploy. The advisor must now
offer S3 only and must not bill for a CloudWatch flow log that never deploys.
"""
import json
import sys
from pathlib import Path

MCP_SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MCP_SERVER_DIR))

import server  # noqa: E402

OVERLAYS = Path(server.__file__).resolve().parents[1] / "industry-overlays"


def _flow_log_dest_options(industry):
    data = json.loads((OVERLAYS / industry / "questions.json").read_text())

    found = {}

    def walk(o):
        if isinstance(o, dict):
            if o.get("id") == "flow_log_destination":
                found["q"] = o
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(data)
    assert "q" in found, f"{industry} has no flow_log_destination question"
    return [opt["value"] for opt in found["q"]["options"]]


def test_starter_offers_s3_only():
    assert _flow_log_dest_options("starter") == ["s3"]


def test_enterprise_offers_s3_only():
    assert _flow_log_dest_options("enterprise") == ["s3"]


def test_neither_overlay_offers_cloudwatch_or_both():
    for industry in ("starter", "enterprise"):
        opts = _flow_log_dest_options(industry)
        assert "cloudwatch" not in opts
        assert "both" not in opts


def _cost_estimate(responses):
    sid = "costtest117"
    server.interview_sessions[sid] = {"session_id": sid, "industry": "starter",
                                      "responses": responses}
    try:
        return server.generate_cost_estimate(sid)
    finally:
        server.interview_sessions.pop(sid, None)


def test_cost_estimate_never_bills_cloudwatch_flow_logs():
    # Even a legacy session carrying flow_log_destination="both" must not add a
    # CloudWatch flow-logs cost line — no CloudWatch flow log deploys (#117).
    out = _cost_estimate({"flow_logs_enabled": True, "flow_log_destination": "both"})
    assert "CloudWatch Logs** (flow logs)" not in out
    # The S3 flow-logs line is still shown (flow logs always go to S3).
    assert "VPC Flow Logs to S3" in out


def test_cost_estimate_shows_s3_flow_logs_when_enabled():
    out = _cost_estimate({"flow_logs_enabled": True})
    assert "VPC Flow Logs to S3" in out


def test_config_flow_log_destination_is_s3(monkeypatch):
    # End-to-end: the generated config records destinations: [s3] (never both).
    sid = "cfg117"
    server.interview_sessions[sid] = {
        "session_id": sid, "industry": "starter",
        "responses": {"organization_name": "Acme", "email_domain": "acme.example",
                      "home_region": "us-east-1", "flow_logs_enabled": True,
                      "flow_log_destination": "s3"},
        "answers": {}, "all_questions": [],
    }
    monkeypatch.setattr(server, "validate_interview_complete",
                        lambda s: json.dumps({"complete": True}))
    import yaml
    try:
        cfg = yaml.safe_load(server.generate_deterministic_titanium_config(session_id=sid))
    finally:
        server.interview_sessions.pop(sid, None)
    assert cfg["vpcFlowLogs"]["destinations"] == ["s3"]
