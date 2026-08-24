# Interview Test Harness

Automated end-to-end testing of the Titanium Advisor interview flow using LLM agents. Tests verify that the MCP server correctly guides an LLM through the interview and generates accurate configuration.

## Available Tests

| Test | Time | What it tests |
|------|------|---------------|
| **Fast** (single-agent) | ~5 min | Config correctness — one agent drives the full interview and a reviewer validates the output |
| **Full** (two-agent) | ~40-60 min | Conversational quality — separate interviewer and customer agents converse naturally, then a reviewer assesses both the config and the interview experience |

## Running Tests

Requires Claude Code. The workflows are in `.claude/workflows/`.

### Fast test (recommended for regression)

Best for quickly checking that code changes didn't break config generation:

```
Invoke workflow: test-advisor-interview-fast
Args: {"scenario": "B"}
```

### Full test (for experience validation)

Tests the real conversational flow — how well the MCP server guides an LLM agent through the interview:

```
Invoke workflow: test-advisor-interview
Args: {"scenario": "A"}
```

### Run all scenarios in parallel

```
Invoke three workflows with args: {"scenario": "A"}, {"scenario": "B"}, {"scenario": "C"}
```

## Scenarios

| Scenario | Persona | Description |
|----------|---------|-------------|
| **A** | Sarah Chen (Enterprise PM) | ACME Corp, eu-west-2, Network account, tags, backups, firewall, budget alerts |
| **B** | Mike Thompson (Startup founder) | MinimalOrg, us-east-1, everything disabled/minimal, beginner |
| **C** | Dr. Patricia Okonkwo (Compliance officer) | Enterprise Inc, ap-southeast-2, everything enabled, 3 infra accounts, advanced |

## Reading Results

### Review files

After each run, a timestamped review file appears in `test-runs/`:

```
test-runs/20260607-113918-scenario-A-full-review.md
```

Contains pass/fail checks, issues found, and interview quality assessment.

### Transcript files

A readable conversation transcript is also generated:

```
test-runs/20260607-113918-scenario-A-full-transcript.txt
```

Format:
```
## Turn 1: Interviewer
  [MCP] start_interview("starter") → session abc123, 11 sections
  [MCP] get_section_quick_mode("basic_info") → 5 questions

ADVISOR: Welcome! I'm here to help you configure...

---

## Turn 2: Customer

CUSTOMER: Hi! We're ACME Corp, based in London...
```

### Regenerating transcripts

If you need to regenerate a transcript from raw workflow data:

```bash
python3 titanium-advisor/tests/dump-workflow-log.py <workflow-dir>
```

The workflow directory is shown in Claude Code's task notification when the workflow completes.

## Prerequisites

- **Claude Code** (all team members have licenses)
- **MCP server configured** — `.mcp.json` in repo root (uses `git rev-parse` for portable paths)
- **Python 3.12+** with the advisor venv set up (`titanium-advisor/mcp-server/.venv/`)

## What the Tests Check

1. **All sections present** (issue #13) — every Titanium section appears in output, disabled ones use `enabled: false`
2. **Config matches requirements** — budget amounts, email addresses, SCPs, network settings all match what the persona specified
3. **Interview quality** (full test only) — natural conversation flow, clear explanations, section-by-section progression
