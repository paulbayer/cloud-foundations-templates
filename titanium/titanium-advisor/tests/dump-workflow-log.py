#!/usr/bin/env python3
"""Dump a workflow's agent transcripts as a readable conversation log."""
import json
import sys
from pathlib import Path


def summarize_mcp_result(result_text):
    """Extract key info from an MCP result JSON."""
    try:
        outer = json.loads(result_text)
        inner_str = outer.get("result", result_text)
        if isinstance(inner_str, str):
            inner = json.loads(inner_str)
        else:
            inner = inner_str

        if "session_id" in inner:
            sections = len(inner.get("sections", []))
            return f"session {inner['session_id']}, {sections} sections"

        if "section_name" in inner:
            nonce = inner.get("confirmation_nonce", "?")
            to_ask = len(inner.get("questions_to_ask", []))
            with_defaults = len(inner.get("questions_with_defaults", []))
            total = to_ask + with_defaults
            if inner.get("auto_completed"):
                return "AUTO-COMPLETED (no applicable questions)"
            return f"{total} questions, nonce {nonce}"

        if "✅_SUCCESS" in inner or "answers_recorded" in inner:
            count = inner.get("answers_recorded", "?")
            return f"SUCCESS, {count} answers recorded"

        if "complete" in inner:
            return f"complete={inner['complete']}"

        return str(inner)[:80]
    except (json.JSONDecodeError, TypeError):
        return result_text[:80] if result_text else ""


def format_mcp_call(name, input_args):
    """Format an MCP tool call as a compact one-liner."""
    short_name = name.replace("mcp__titanium-advisor__", "")

    if short_name == "start_interview":
        return f'start_interview("{input_args.get("industry", "?")}")'
    elif short_name == "get_section_quick_mode":
        return f'get_section_quick_mode("{input_args.get("section_id", "?")}")'
    elif short_name == "bulk_record_answers":
        answers = input_args.get("answers_dict", {})
        keys = list(answers.keys()) if isinstance(answers, dict) else []
        if len(keys) <= 3:
            return f"bulk_record_answers({', '.join(keys)})"
        return f"bulk_record_answers({len(keys)} answers)"
    elif short_name == "validate_interview_complete":
        return "validate_interview_complete()"
    elif short_name == "generate_deterministic_titanium_config":
        return "generate_deterministic_titanium_config()"
    else:
        return f"{short_name}({json.dumps(input_args)[:60]})"


def process_workflow(wf_dir):
    """Process a workflow directory and output a clean conversation log."""
    wf_dir = Path(wf_dir)

    journal_path = wf_dir / "journal.jsonl"
    agent_ids = []
    if journal_path.exists():
        with open(journal_path) as f:
            for line in f:
                entry = json.loads(line.strip())
                if entry.get("type") == "started":
                    agent_ids.append(entry.get("agentId", ""))

    turn_num = 0
    for agent_id in agent_ids:
        agent_file = wf_dir / f"agent-{agent_id}.jsonl"
        if not agent_file.exists():
            continue

        turn_num += 1
        is_interviewer = (turn_num % 2 == 1)
        role_label = "Interviewer" if is_interviewer else "Customer"

        mcp_calls = []
        output_message = None

        with open(agent_file) as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                    msg = d.get("message", {})
                    content = msg.get("content", [])

                    if not isinstance(content, list):
                        continue

                    for block in content:
                        if not isinstance(block, dict):
                            continue

                        if block.get("type") == "tool_use":
                            name = block.get("name", "")
                            inp = block.get("input", {})

                            if name == "ToolSearch":
                                continue
                            elif name == "StructuredOutput":
                                output_message = inp.get("message", "")
                            elif name.startswith("mcp__titanium-advisor__"):
                                mcp_calls.append({
                                    "call": format_mcp_call(name, inp),
                                    "id": block.get("id", "")
                                })

                        elif block.get("type") == "tool_result":
                            tool_use_id = block.get("tool_use_id", "")
                            result_content = block.get("content", "")
                            if isinstance(result_content, list) and result_content:
                                result_text = result_content[0].get("text", "")
                            else:
                                result_text = str(result_content)

                            for call in mcp_calls:
                                if call.get("id") == tool_use_id and "result" not in call:
                                    call["result"] = summarize_mcp_result(result_text)
                                    break

                except (json.JSONDecodeError, KeyError):
                    continue

        if not output_message and not mcp_calls:
            turn_num -= 1
            continue

        print(f"\n## Turn {turn_num}: {role_label}")
        print()

        if mcp_calls and is_interviewer:
            for call in mcp_calls:
                result = call.get("result", "")
                if result:
                    print(f"  [MCP] {call['call']} → {result}")
                else:
                    print(f"  [MCP] {call['call']}")
            print()

        if output_message:
            prefix = "ADVISOR" if is_interviewer else "CUSTOMER"
            print(f"{prefix}: {output_message}")

        print()
        print("---")

    print(f"\n## End of transcript ({turn_num} turns)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: dump-workflow-log.py <workflow-dir>")
        print("  e.g. dump-workflow-log.py ~/.claude/projects/.../subagents/workflows/wf_xxxxx")
        sys.exit(1)

    wf_dir = Path(sys.argv[1])
    if not wf_dir.exists():
        print(f"Directory not found: {wf_dir}")
        sys.exit(1)

    process_workflow(wf_dir)
