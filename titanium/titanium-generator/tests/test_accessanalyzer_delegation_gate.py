"""
Tests for #104: Access Analyzer template 10 must not race template 09's
delegated-admin registration.

Two defenses:
  - Template 09's Lambda polls list_delegated_administrators until the Audit
    account is visible before completing (instead of a fixed sleep).
  - The deployment guide injects a propagation GATE step before template 10,
    mirroring the org Step-13 enrollment gate.
"""

from pathlib import Path

import yaml

import titanium_generator
from titanium_generator.mcp_tools.llm_agent_guide import LLMAgentGuideGenerator

DELEGATE_TEMPLATE = (
    Path(titanium_generator.__file__).parent
    / "mcp_tools" / "templates" / "security"
    / "09-accessanalyzer-stack-mgmt-delegate.yaml"
)


class _CfnLoader(yaml.SafeLoader):
    pass


_CfnLoader.add_multi_constructor("!", lambda loader, suffix, node: None)


# --- Template 09 Lambda: propagation poll -----------------------------------

def _delegate_lambda():
    doc = yaml.load(DELEGATE_TEMPLATE.read_text(), Loader=_CfnLoader)
    fn = doc["Resources"]["rAccessAnalyzerDelegationLambda"]["Properties"]
    return fn


def test_delegate_lambda_polls_for_propagation():
    fn = _delegate_lambda()
    code = fn["Code"]["ZipFile"]
    # Polls the delegated-admin list after registering rather than a fixed sleep.
    assert "list_delegated_administrators" in code
    assert "register_delegated_administrator" in code
    # Timeout raised to accommodate the bounded poll.
    assert fn["Timeout"] >= 150


# --- Deployment guide: 09 -> 10 GATE ----------------------------------------

def test_gate_step_targets_the_delegated_admin():
    gen = LLMAgentGuideGenerator()
    step = gen._generate_accessanalyzer_delegation_gate_step({}, "us-west-2")
    assert "GATE" in step["title"]
    cmd = step["commands"][0]["command"]
    assert "list-delegated-administrators" in cmd
    assert "access-analyzer.amazonaws.com" in cmd


def _phase_with(monkeypatch, tmp_path, names):
    """Run _generate_phase_steps over `names`, stubbing per-template step gen."""
    gen = LLMAgentGuideGenerator()
    files = []
    for name in names:
        p = tmp_path / name
        p.write_text("Resources: {}\n")
        files.append({"name": name, "output_path": str(p)})

    # Stub template step generation so we test the gate injection wiring only.
    monkeypatch.setattr(
        gen, "_generate_template_steps",
        lambda file_info, *a, **k: [{"title": f"Deploy {file_info['name']}"}],
    )
    return gen._generate_phase_steps("security", {"files": files}, {}, "us-east-1", {})


def test_gate_injected_before_template_10(monkeypatch, tmp_path):
    steps = _phase_with(monkeypatch, tmp_path, [
        "09-accessanalyzer-stack-mgmt-delegate.yaml",
        "10-accessanalyzer-stackset-audit-configure.yaml",
    ])
    titles = [s["title"] for s in steps]
    gate_idx = next(i for i, t in enumerate(titles) if "delegated admin is active (GATE)" in t)
    ten_idx = next(i for i, t in enumerate(titles) if t.startswith("Deploy 10-accessanalyzer"))
    nine_idx = next(i for i, t in enumerate(titles) if t.startswith("Deploy 09-accessanalyzer"))
    # Gate sits between 09 and 10.
    assert nine_idx < gate_idx < ten_idx


def test_no_gate_when_template_10_absent(monkeypatch, tmp_path):
    steps = _phase_with(monkeypatch, tmp_path, [
        "09-accessanalyzer-stack-mgmt-delegate.yaml",
    ])
    assert not any("delegated admin is active (GATE)" in s["title"] for s in steps)


def test_gate_injected_only_once(monkeypatch, tmp_path):
    steps = _phase_with(monkeypatch, tmp_path, [
        "09-accessanalyzer-stack-mgmt-delegate.yaml",
        "10-accessanalyzer-stackset-audit-configure.yaml",
    ])
    gates = [s for s in steps if "delegated admin is active (GATE)" in s["title"]]
    assert len(gates) == 1
