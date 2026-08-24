"""
Tests for #105: the email_domain validator must accept valid multi-label FQDNs.

The old pattern permitted only a single label + TLD, so subdomains like
sub.example.com (common for account root-email domains, e.g. aws.example.com)
were rejected with "Answer does not match required format". The tests run
against the pattern actually shipped in the overlays so the fix can't regress.
"""
import json
import sys
from pathlib import Path

import pytest

MCP_SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MCP_SERVER_DIR))

import server  # noqa: E402

OVERLAYS = MCP_SERVER_DIR.parent / "industry-overlays"


def _email_domain_question(industry):
    data = json.loads((OVERLAYS / industry / "questions.json").read_text())
    for section in data["sections"]:
        for q in section["questions"]:
            if q.get("id") == "email_domain":
                return q
    raise AssertionError(f"email_domain question not found in {industry}")


INDUSTRIES = ["starter", "enterprise"]


@pytest.mark.parametrize("industry", INDUSTRIES)
@pytest.mark.parametrize("domain", [
    "example.com",
    "sub.example.com",
    "run1minimal.example.com",
    "aws.example.co.uk",
])
def test_valid_fqdns_accepted(industry, domain):
    ok, msg = server.validate_answer(_email_domain_question(industry), domain)
    assert ok, f"{domain} should be valid ({msg})"


@pytest.mark.parametrize("industry", INDUSTRIES)
@pytest.mark.parametrize("domain", [
    "nodot",        # no TLD
    "foo..com",     # empty label
    "-bad.com",     # label starts with hyphen
    "example.",     # trailing dot, no TLD
])
def test_invalid_domains_rejected(industry, domain):
    ok, _ = server.validate_answer(_email_domain_question(industry), domain)
    assert not ok, f"{domain} should be rejected"
