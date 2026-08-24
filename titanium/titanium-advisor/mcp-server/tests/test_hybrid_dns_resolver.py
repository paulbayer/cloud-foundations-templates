"""
Tests for #85: hybrid DNS resolver is reachable through the advisor interview.

Previously generate_deterministic_titanium_config hardcoded
route53Resolver.enabled=False, so an advisor-generated config could never turn on
the DNS resolver template. The interview now has enable_hybrid_dns (+ follow-on
domains / on-prem DNS servers / allowed CIDRs), and the builder populates
route53Resolver from those answers.
"""
import json
import sys
from pathlib import Path

import yaml

MCP_SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MCP_SERVER_DIR))

import server  # noqa: E402


def _emit_config(monkeypatch, industry, extra_responses):
    session_id = "dnstest1"
    server.interview_sessions[session_id] = {
        "session_id": session_id,
        "industry": industry,
        "responses": {
            "organization_name": "Acme",
            "email_domain": "acme.example",
            "home_region": "us-east-1",
            "network_account_enabled": True,  # resolver only renders with a Network account
            **extra_responses,
        },
        "answers": {},
        "all_questions": [],
    }
    monkeypatch.setattr(
        server, "validate_interview_complete",
        lambda sid: json.dumps({"complete": True}),
    )
    try:
        output = server.generate_deterministic_titanium_config(session_id=session_id)
    finally:
        server.interview_sessions.pop(session_id, None)
    return yaml.safe_load(output)


def _resolver(config):
    return config["network"]["tgwArchitecture"]["route53Resolver"]


def test_disabled_by_default(monkeypatch):
    # No DNS answer → resolver stays off (no regression from the old hardcode).
    resolver = _resolver(_emit_config(monkeypatch, "starter", {}))
    assert resolver["enabled"] is False
    assert resolver["outboundDomains"] == []
    assert resolver["onPremDnsServers"] == []
    assert resolver["allowedSourceCidrs"] == []


def test_enabled_with_collected_lists(monkeypatch):
    resolver = _resolver(_emit_config(monkeypatch, "starter", {
        "route53_resolver_enabled": True,
        "route53_resolver_outbound_domains": "corp.acme.com, internal.acme.com",
        "route53_resolver_on_prem_dns_servers": "10.1.1.10,10.1.1.11",
        "route53_resolver_allowed_source_cidrs": "10.0.0.0/8",
    }))
    assert resolver["enabled"] is True
    assert resolver["outboundDomains"] == ["corp.acme.com", "internal.acme.com"]
    assert resolver["onPremDnsServers"] == ["10.1.1.10", "10.1.1.11"]
    assert resolver["allowedSourceCidrs"] == ["10.0.0.0/8"]


def test_enabled_falls_back_to_pattern_lists(monkeypatch):
    # Enterprise pattern ships sample domains/servers/CIDRs; when the user enables
    # DNS but provides no lists, the pattern values are used as the fallback.
    resolver = _resolver(_emit_config(monkeypatch, "enterprise", {
        "route53_resolver_enabled": True,
    }))
    assert resolver["enabled"] is True
    assert resolver["outboundDomains"]  # non-empty from the enterprise pattern
    assert resolver["onPremDnsServers"]


def test_interview_has_dns_question():
    # The overlays that drive the interview must actually ask the DNS question.
    for industry in ("starter", "enterprise"):
        path = MCP_SERVER_DIR.parent / "industry-overlays" / industry / "questions.json"
        data = json.loads(path.read_text())
        ids = set()
        for section in data.get("sections", []):
            for question in section.get("questions", []):
                ids.add(question.get("id"))
        assert "enable_hybrid_dns" in ids, industry
