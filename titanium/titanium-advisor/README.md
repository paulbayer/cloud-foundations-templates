# Titanium Advisor

A GenAI-powered MCP server that conducts a guided AWS Landing Zone interview and produces a standardized `Titanium.yaml` configuration. It runs inside an MCP-compatible assistant (Kiro or Claude Code) and consolidates every landing zone decision into a single file that the [Titanium Generator](../titanium-generator/README.md) turns into CloudFormation.

## Overview

Titanium Advisor is Phase 1 of the Titanium workflow — the **Design** stage. It:

- Runs a structured, section-by-section interview tailored to an industry overlay
- Applies industry best practices and compliance requirements as defaults
- Emits a validated `Titanium.yaml` in the standardized schema

## Architecture

The Advisor is an MCP server that exposes read-only knowledge (interview questions, industry requirements, examples, schema) plus stateful interview and config-generation tools. Interview answers are held in a per-session store on the local machine (`titanium-advisor/sessions/`, gitignored) — the server processes configuration locally, so customer-specific data stays in your environment.

## Directory Structure

```
titanium-advisor/
├── core/                          # Core interview framework and templates
│   ├── interview-framework.md
│   └── templates/
│       ├── base-titanium.j2       # Jinja2 template for Titanium.yaml
│       └── schemas/
│           └── titanium-schema.json
├── industry-overlays/             # Industry-specific content (see below)
│   ├── starter/                   # questions.json, pattern.json, requirements/
│   ├── enterprise/                # questions.json, pattern.json, requirements/
│   ├── uk-public-sector/          # interview-questions.md, pattern.json, patterns/, requirements/
│   ├── us-government/             # interview-questions.md, pattern.json, requirements/
│   └── generic/                   # placeholder — no content yet
├── mcp-server/                    # MCP server implementation
│   ├── server.py
│   ├── requirements.txt
│   └── tests/
└── output-examples/               # Example generated configurations
    ├── starter-example.yaml
    ├── uk-council.yaml
    └── us-federal.yaml
```

## Industry Overlays

Each overlay tailors the interview questions and configuration defaults. Note that overlays currently use two content formats: `starter` and `enterprise` are driven by `questions.json`, while `uk-public-sector` and `us-government` use `interview-questions.md`.

- **Starter** — Small-to-medium orgs and first-time users; simplifies most decisions to Yes/No.
- **Enterprise** — Large corporate environments: multi-region operations, complex org structures, enhanced financial governance.
- **UK Public Sector** — UK government/public sector: NCSC Cloud Security Principles, UK GDPR, PSN connectivity, local-government digital standards.
- **US Government** — US federal/state/local agencies: FedRAMP, NIST frameworks, sovereign-cloud considerations.
- **Generic** — Reserved placeholder; not yet populated.

## Getting Started

Setup (Python venv, MCP server configuration for Kiro or Claude Code, and verification) is covered once in the repository's [Getting Started guide](../GETTING_STARTED.md). Follow that guide, then start the interview by asking your assistant:

> "I need to design a landing zone for my organization. Can you help me through the process?"

### Running the tests

```bash
# From the repository root (uses the advisor venv; see GETTING_STARTED.md)
titanium-advisor/mcp-server/.venv/bin/python -m pytest titanium-advisor/mcp-server/tests/ -q
```

## Available MCP Tools

The server exposes these tools (defined in `mcp-server/server.py`):

**Interview flow**
- `start_interview` — begin a session for a chosen industry overlay
- `get_next_question` — get the next interview question
- `get_section_quick_mode` — retrieve a whole section for bulk answering
- `bulk_record_answers` — record multiple answers at once
- `update_answer` — change a previously recorded answer
- `get_interview_progress` — check completion status
- `validate_interview_complete` — confirm all required questions are answered
- `get_session_answers` — retrieve the answers recorded so far

**Sessions**
- `list_sessions` — list saved interview sessions
- `resume_session` — resume a previous session

**Industry knowledge**
- `list_available_industries` — list supported overlays
- `get_interview_questions` — get an overlay's interview questions
- `get_industry_requirements` — get compliance/regulatory requirements
- `get_configuration_example` — get an example configuration

**Configuration generation & validation**
- `generate_deterministic_titanium_config` — build `Titanium.yaml` from the recorded answers
- `validate_titanium_config` — validate a configuration against the schema
- `generate_configuration_summary` — summarize a generated configuration
- `generate_cost_estimate` — estimate monthly cost for the configuration

## Customization

### Adding a New Industry Overlay

1. Create a new directory in `industry-overlays/`.
2. Add a `questions.json` (interview questions) and a `pattern.json` (base configuration defaults).
3. Add a `requirements/` directory with the overlay's compliance/requirements content.

### Extending Templates

1. Edit the Jinja2 template in `core/templates/base-titanium.j2` and the schema in `core/templates/schemas/titanium-schema.json`.
2. Update the server if new template variables are introduced.

## License

This project is licensed under the MIT License — see the [LICENSE](../LICENSE) file for details.
