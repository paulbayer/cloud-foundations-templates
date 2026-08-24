"""
Tests for #97: the advisor must emit a backup policy whose name matches the
backup template's singular deploy toggles.

The generator derives tDeploy<name>/t<name>Description directly from the policy
name. The template declares tDeployDailyBackup / tDeployWeeklyBackup /
tDeployMonthlyBackup (singular). The advisor used to hard-code the plural
"DailyBackups" regardless of the chosen frequency, so the generator emitted
tDeployDailyBackups, which silently no-ops against the template -> the backup
policy never deployed even when enabled.
"""
import json
import sys
from pathlib import Path

import yaml

MCP_SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MCP_SERVER_DIR))

import server  # noqa: E402


def _emit(monkeypatch, responses):
    sid = "backuptest"
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


def _policy(cfg):
    return cfg["organization"]["backupPolicies"][0]


def test_daily_frequency_emits_singular_daily_name(monkeypatch):
    cfg = _emit(monkeypatch, {"backup_enabled": True, "backup_frequency": "daily"})
    policy = _policy(cfg)
    assert policy["name"] == "DailyBackup"  # matches tDeployDailyBackup
    assert policy["enable"] is True


def test_weekly_frequency_emits_singular_weekly_name(monkeypatch):
    cfg = _emit(monkeypatch, {"backup_enabled": True, "backup_frequency": "weekly"})
    policy = _policy(cfg)
    assert policy["name"] == "WeeklyBackup"  # matches tDeployWeeklyBackup
    assert policy["enable"] is True


def test_name_is_never_plural(monkeypatch):
    # Regression guard for #97: a plural name -> tDeploy<name>s no-ops on the template.
    for freq in ("daily", "weekly", "monthly"):
        cfg = _emit(monkeypatch, {"backup_enabled": True, "backup_frequency": freq})
        assert not _policy(cfg)["name"].endswith("Backups")
