> [!TIP]
> ### 🤖 Automated Setup with Kiro (or any agentic IDE)
>
> Instead of following the manual steps below, paste this prompt into your AI assistant to automate the entire setup:
>
> ---
>
> *Copy and paste the following into Kiro chat (or your agentic IDE):*
>
> ```text
> Please automate the Titanium setup for me. Follow these steps:
>
> 1. Check that Python 3.12+ is installed (run `python3 --version`). If not, let me know.
> 2. Check that `uv` is installed (run `uv --version`). If not, install it with `pip install uv` or `brew install uv`.
> 3. Clone the cloud-foundations-templates repository if not already cloned,
>    then cd into the `titanium/` solution folder:
>    `git clone https://github.com/cloud-foundations-on-aws/cloud-foundations-templates.git`
>    then `cd cloud-foundations-templates/titanium`.
> 4. Set up the Titanium Advisor MCP server:
>    - Navigate to `titanium-advisor/mcp-server`
>    - Create a virtual environment: `python3 -m venv .venv`
>    - Install dependencies: `.venv/bin/pip install -r requirements.txt`
> 5. Set up the Titanium Generator MCP server:
>    - Navigate to `titanium-generator`
>    - Create a virtual environment: `python3 -m venv .venv`
>    - Install dependencies: `.venv/bin/pip install -r requirements.txt`
> 6. Confirm the steering file `.kiro/steering/titanium-landing-zone-guidance.md`
>    is present (it ships with the repo). For Kiro, this file routes questions
>    between the Titanium tools and AWS documentation.
> 7. Make sure the MCP servers are configured for my IDE (Kiro reads
>    `.kiro/settings/mcp.json`; Claude Code reads `titanium/.mcp.json`).
> 8. Verify the setup by listing the available Titanium tools.
> ```
>
> ---

# Step 1: Prerequisites & Setup

This guide covers everything you need to install and configure before using Titanium.

## Prerequisites

- **Python 3.12 or newer** — Required to run the Titanium MCP servers
- **uv** — Required to run the AWS documentation MCP servers. Install via `pip install uv` or `brew install uv` on macOS. See the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) for other platforms.
- **An MCP-compatible IDE or CLI** — One of the following:
  - [Kiro](https://kiro.dev) (recommended)
  - [Kiro CLI](https://kiro.dev)
  - [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview)

## Installation

### 0. Clone the Repository

Titanium ships as the `titanium/` folder of the **cloud-foundations-templates**
monorepo. Clone the monorepo and change into that folder — all commands below are
run from inside `titanium/`.

```bash
git clone https://github.com/cloud-foundations-on-aws/cloud-foundations-templates.git
cd cloud-foundations-templates/titanium
```

### 1. Set Up the Titanium Advisor

```bash
# Navigate to the MCP server directory
cd titanium-advisor/mcp-server

# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Up the Titanium Generator

```bash
# Navigate to the generator directory
cd titanium-generator

# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Steering Rules (routing between Titanium tools and AWS docs)

Titanium ships a steering file that teaches your AI assistant when to use the Titanium MCP tools versus AWS documentation, and enforces best practices during landing zone design. It lives in the repo at `.kiro/steering/titanium-landing-zone-guidance.md` — no copying required.

- **Kiro:** Kiro loads steering files from `.kiro/steering/` in the workspace. The file's `inclusion` frontmatter controls when it applies — `auto` loads it in every conversation, `manual` means you reference it on demand. Set it to `auto` if you want it always active.
- **Claude Code:** Claude Code doesn't read `.kiro/steering/`. To give Claude Code the same routing guidance, reference `.kiro/steering/titanium-landing-zone-guidance.md` in your prompt, or add its content to a project `CLAUDE.md`.

### 4. Configure Your IDE

Titanium ships a canonical **`.mcp.json`** in the `titanium/` folder that defines the two Titanium servers using portable, machine-independent launch commands (`bash -c "cd \"$(git rev-parse --show-toplevel)/titanium/…\" && .venv/bin/python …"`, no absolute paths — they resolve relative to the monorepo root):

```json
{
  "mcpServers": {
    "titanium-advisor": {
      "command": "bash",
      "args": ["-c", "cd \"$(git rev-parse --show-toplevel)/titanium/titanium-advisor/mcp-server\" && .venv/bin/python server.py"],
      "env": {}
    },
    "titanium-generator": {
      "command": "bash",
      "args": ["-c", "cd \"$(git rev-parse --show-toplevel)/titanium/titanium-generator\" && PYTHONPATH=. .venv/bin/python mcp_server.py"],
      "env": {}
    }
  }
}
```

Claude Code uses this file directly. Other tools read their config from a different location, so you copy these two server entries and adapt the wrapper to your tool. Choose your IDE below.

<details>
<summary>Kiro</summary>

Kiro reads `.kiro/settings/mcp.json` (per-workspace, and gitignored — so it is not shipped; you create it). Copy the two server entries from the root `.mcp.json` above and add Kiro's `disabled` / `timeout` / `type` fields:

```json
{
  "mcpServers": {
    "titanium-advisor": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "bash",
      "args": ["-c", "cd \"$(git rev-parse --show-toplevel)/titanium/titanium-advisor/mcp-server\" && .venv/bin/python server.py"],
      "env": {}
    },
    "titanium-generator": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "bash",
      "args": ["-c", "cd \"$(git rev-parse --show-toplevel)/titanium/titanium-generator\" && PYTHONPATH=. .venv/bin/python mcp_server.py"],
      "env": {}
    }
  }
}
```

Because the launch commands are relative to the repo root, there are no absolute paths to edit — once the venvs from steps 1–2 exist, both servers start when you open the workspace in Kiro.

To also search AWS documentation, add an optional `aws-docs` server entry:

```json
"aws-docs": {
  "disabled": false,
  "timeout": 60,
  "command": "uvx",
  "args": ["awslabs.aws-documentation-mcp-server@latest"],
  "env": { "FASTMCP_LOG_LEVEL": "ERROR" }
}
```

> **Note:** The `aws-docs` server requires `uvx` (part of the [uv](https://docs.astral.sh/uv/getting-started/installation/) Python package manager). Install it with `pip install uv` or `brew install uv` on macOS. Once installed, `uvx` downloads and runs the AWS documentation server automatically — no additional installation needed.

</details>

<details>
<summary>Kiro CLI</summary>

Kiro CLI uses the same `.kiro/settings/mcp.json` you create in the Kiro section above. Once it exists and the venvs from steps 1–2 are in place, both servers start automatically — the launch commands use no absolute paths.

Test with:
```bash
kiro --chat
```

Then ask: "List the available Titanium tools"

You should see tools from both the Advisor and Generator servers (plus the AWS documentation server if you added the optional `aws-docs` entry).

</details>

<details>
<summary>Claude Code</summary>

Claude Code reads `titanium/.mcp.json` directly — no adaptation needed. Complete the venv setup in steps 1–2, open the `titanium/` folder in Claude Code, and both servers start automatically.

To also search AWS documentation, you can optionally add an `aws-docs` server to `.mcp.json`:

```json
"aws-docs": {
  "command": "uvx",
  "args": ["awslabs.aws-documentation-mcp-server@latest"],
  "env": { "FASTMCP_LOG_LEVEL": "ERROR" }
}
```

> **Note:** The `aws-docs` server requires `uvx` (part of the [uv](https://docs.astral.sh/uv/getting-started/installation/) Python package manager). Install it with `pip install uv` or `brew install uv` on macOS.

Test with:
```bash
claude
> /mcp
```

You should see the `titanium-advisor` and `titanium-generator` servers connected (plus `aws-docs` if you added it).

</details>

## Verify Your Setup

Start a conversation with your AI assistant and say:

> "List the available Titanium tools"

You should see tools from both the Advisor (interview, configuration) and Generator (template generation, validation) servers — plus AWS documentation search tools if you added the optional `aws-docs` server.

If you're using Kiro, also verify the steering file `.kiro/steering/titanium-landing-zone-guidance.md` is present in your workspace (see step 3 for how Kiro applies it).

## Next Step

➡️ [Step 2: Design Your Landing Zone](DESIGN_GUIDE.md)
