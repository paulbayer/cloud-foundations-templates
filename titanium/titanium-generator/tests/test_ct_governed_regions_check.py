"""
Tests for #109: the advisor accepts allowed_regions the Control Tower landing
zone does not govern, so org-wide StackSets fail in the ungoverned region.

Control Tower is an external prerequisite, so the advisor cannot validate at
interview time. The fix is a validation/documentation gap closure on two sides:
  1. The advisor's allowed_regions help_text tells the user the regions must be
     a subset of the CT-governed regions.
  2. The deployment guide (where CT IS reachable) adds a pre-deployment setup
     step that reads the landing zone's governedRegions and verifies the enabled
     regions are a subset before any org-wide StackSet runs.
"""

import json
from pathlib import Path

import titanium_generator
from titanium_generator.mcp_tools.llm_agent_guide import LLMAgentGuideGenerator

ADVISOR_DIR = Path(titanium_generator.__file__).parents[2] / "titanium-advisor"
OVERLAYS = [
    ADVISOR_DIR / "industry-overlays" / "starter" / "questions.json",
    ADVISOR_DIR / "industry-overlays" / "enterprise" / "questions.json",
]


def _setup_steps(config):
    gen = LLMAgentGuideGenerator()
    return gen._generate_setup_steps(config, config.get("homeRegion", "us-east-1"))


def _governed_step(steps):
    for step in steps:
        cmds = " ".join(c.get("command", "") for c in step.get("commands", []))
        if "get-landing-zone" in cmds and "governedRegions" in cmds:
            return step
    return None


def test_guide_adds_governed_regions_check_when_regions_enabled():
    steps = _setup_steps({"enabledRegions": ["us-west-2", "us-east-2"]})
    step = _governed_step(steps)
    assert step is not None
    # It must run before the specialized-account collection (i.e. early setup).
    assert step["phase"] == "setup"
    # Both enabled regions surface for the subset comparison.
    blob = json.dumps(step)
    assert "us-west-2" in blob and "us-east-2" in blob
    assert "list-landing-zones" in blob


def test_guide_skips_check_when_no_regions_enabled():
    steps = _setup_steps({})
    assert _governed_step(steps) is None


def test_advisor_help_text_mentions_governed_subset():
    for overlay in OVERLAYS:
        data = json.loads(overlay.read_text())

        found = {}

        def walk(node):
            if isinstance(node, dict):
                if node.get("id") == "allowed_regions":
                    found["help"] = node.get("help_text", "")
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(data)
        assert "help" in found, overlay
        help_text = found["help"].lower()
        assert "control tower" in help_text, overlay
        assert "govern" in help_text, overlay
