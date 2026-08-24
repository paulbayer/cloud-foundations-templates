#!/usr/bin/env python3
"""
Titanium Advisor MCP Server

A Model Context Protocol server for AWS Landing Zone configuration generation.
Provides industry-specific guidance and templates for creating Titanium.yaml
configurations tailored to specific regulatory and compliance requirements.

Phase 1 & 2: Mandatory Question Tracking
- Structured questions.json format
- Session tracking and validation
- Progress tracking
- Validation gates for config generation
"""

import argparse
import os
import yaml
import json
import uuid
import re
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, List, Optional
from datetime import datetime
from jinja2 import Template
import copy

# Base directory for resources
BASE_DIR = Path(__file__).parent.parent.resolve()
INDUSTRY_DIR = BASE_DIR / "industry-overlays"
TEMPLATE_DIR = BASE_DIR / "core" / "templates"
OUTPUT_DIR = BASE_DIR / "output-examples"
SESSIONS_DIR = BASE_DIR / "sessions"

# Session storage for interview state tracking
interview_sessions: Dict[str, Dict[str, Any]] = {}

# Geo/city aliases -> AWS region code. The allowed_regions and home_region
# questions are "discovery"-type ("describe which parts of the world"), so the
# stored answer is often a place name rather than a region code.
_REGION_ALIASES = {
    "london": "eu-west-2", "ireland": "eu-west-1", "frankfurt": "eu-central-1",
    "paris": "eu-west-3", "stockholm": "eu-north-1", "milan": "eu-south-1",
    "spain": "eu-south-2", "zurich": "eu-central-2",
    "virginia": "us-east-1", "ohio": "us-east-2", "oregon": "us-west-2",
    "california": "us-west-1", "n. virginia": "us-east-1",
    "sydney": "ap-southeast-2", "melbourne": "ap-southeast-4",
    "tokyo": "ap-northeast-1", "osaka": "ap-northeast-3",
    "singapore": "ap-southeast-1", "mumbai": "ap-south-1",
    "hyderabad": "ap-south-2", "seoul": "ap-northeast-2",
    "jakarta": "ap-southeast-3", "hong kong": "ap-east-1",
    "canada": "ca-central-1", "calgary": "ca-west-1",
    "sao paulo": "sa-east-1", "brazil": "sa-east-1",
    "bahrain": "me-south-1", "uae": "me-central-1",
    "cape town": "af-south-1", "south africa": "af-south-1",
}

# Structural AWS region-code matcher, e.g. us-west-2, eu-central-1, ap-southeast-4.
_AWS_REGION_RE = re.compile(r"\b([a-z]{2}-[a-z]+-\d+)\b")


def _resolve_region_fragment(fragment: str) -> List[str]:
    """Return every AWS region code a single free-text fragment refers to.

    Recognizes both AWS region codes embedded anywhere in the text (recovers
    the region from a fragment like ``us-west-2)`` produced by comma-splitting
    ``"US West only (Oregon, us-west-2)"``) and geo aliases appearing as whole
    words (``"London and Frankfurt"`` -> both regions). Unmatched free text
    yields ``[]`` so callers drop it rather than emit a bogus region.
    """
    text = fragment.strip().lower()
    if not text:
        return []
    codes = list(_AWS_REGION_RE.findall(text))
    # Longest alias first so multi-word aliases ("hong kong", "n. virginia")
    # match ahead of any shorter substring.
    for alias in sorted(_REGION_ALIASES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(alias) + r"\b", text):
            codes.append(_REGION_ALIASES[alias])
    return codes


def _normalize_home_region(value: Any) -> Any:
    """Geo-map a discovery-style ``home_region`` answer to an AWS region code.

    ``home_region`` is a discovery question ("tell me your location"), so the
    stored answer is often a descriptive phrase ("Portland, Oregon, USA") rather
    than a region code. Resolve it the same way as ``allowed_regions`` (issue
    #110): find the first region code/geo alias inside the phrase via
    :func:`_resolve_region_fragment` ("oregon" -> us-west-2; an embedded
    "us-west-2" -> itself). Fall back to the raw answer only if nothing resolves,
    so a genuinely already-clean value or an unrecognized answer is left intact.
    """
    if not isinstance(value, str):
        return value
    resolved = _resolve_region_fragment(value)
    return resolved[0] if resolved else value


# Structural full-string AWS region-code check (us-east-1, ap-southeast-4, ...).
# Distinct from _AWS_REGION_RE, which *finds* a code embedded in free text; this
# asserts the whole value IS a region code, so a leaked descriptive phrase
# ("Seattle, Washington, USA") is rejected rather than emitted (issue #110).
_AWS_REGION_FULL_RE = re.compile(r"[a-z]{2}-[a-z]+-\d+")


def _is_aws_region_code(value: Any) -> bool:
    """True only if ``value`` is exactly a structurally-valid AWS region code."""
    return isinstance(value, str) and bool(_AWS_REGION_FULL_RE.fullmatch(value.strip()))


def _resolve_region_codes(value: Any) -> List[str]:
    """Resolve a discovery-style allowed_regions answer into AWS region codes.

    Accepts a string or a list (each element may itself be a comma-joined
    phrase). Every comma-separated fragment is geo-mapped/validated via
    :func:`_resolve_region_fragment`; unmatched free text is dropped instead of
    being passed through as a bogus ``enabledRegions`` entry (issue #106).
    Order is preserved and duplicates removed. Free text that maps to nothing
    yields ``[]``, letting the caller fall back to the home region.
    """
    if value is None:
        return []
    if isinstance(value, str):
        fragments = value.split(",")
    elif isinstance(value, (list, tuple)):
        fragments = [frag for item in value for frag in str(item).split(",")]
    else:
        fragments = [str(value)]

    resolved: List[str] = []
    for fragment in fragments:
        for code in _resolve_region_fragment(fragment):
            if code not in resolved:
                resolved.append(code)
    return resolved


def _session_to_dict(session: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare session for JSON serialisation (convert set -> list)."""
    s = copy.deepcopy(session)
    if isinstance(s.get("pending_confirmation"), set):
        s["pending_confirmation"] = list(s["pending_confirmation"])
    return s


def _session_from_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Restore session from JSON (convert list -> set)."""
    if isinstance(data.get("pending_confirmation"), list):
        data["pending_confirmation"] = set(data["pending_confirmation"])
    return data


def save_session(session_id: str) -> None:
    """Persist a session to disk."""
    SESSIONS_DIR.mkdir(exist_ok=True)
    with open(SESSIONS_DIR / f"{session_id}.json", "w") as f:
        json.dump(_session_to_dict(interview_sessions[session_id]), f, indent=2)


def load_session_from_disk(session_id: str) -> Optional[Dict[str, Any]]:
    """Load a session from disk. Returns None if not found."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if not session_file.exists():
        return None
    with open(session_file, "r") as f:
        return _session_from_dict(json.load(f))


def load_structured_questions(industry: str) -> Optional[Dict[str, Any]]:
    """
    Load structured questions from questions.json for an industry.
    
    Args:
        industry: Industry type
        
    Returns:
        Parsed questions structure or None if not found
    """
    questions_file = INDUSTRY_DIR / industry / "questions.json"
    if questions_file.exists():
        with open(questions_file, "r") as f:
            return json.load(f)
    return None


def get_all_questions(questions_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Flatten all questions from all sections into a single list with section info.
    
    Args:
        questions_data: Parsed questions.json structure
        
    Returns:
        List of all questions with section metadata
    """
    all_questions = []
    for section in sorted(questions_data.get("sections", []), key=lambda s: s.get("order", 0)):
        for question in section.get("questions", []):
            q = question.copy()
            q["section_id"] = section["id"]
            q["section_name"] = section["name"]
            all_questions.append(q)
    return all_questions


def evaluate_depends_on(question: Dict[str, Any], answers: Dict[str, Any]) -> bool:
    """
    Check if a question's dependencies are satisfied.
    
    Args:
        question: Question definition
        answers: Current answers dictionary (keyed by question_id)
        
    Returns:
        True if question should be asked, False if dependencies not met
    """
    depends_on = question.get("depends_on")
    if not depends_on:
        return True
    
    dep_question_id = depends_on.get("question_id")
    dep_answer_value = depends_on.get("answer_value")
    
    if dep_question_id not in answers:
        return False
    
    actual_answer = answers[dep_question_id].get("answer")
    
    # Handle yes_no type - normalize to boolean
    if isinstance(dep_answer_value, bool):
        if isinstance(actual_answer, bool):
            return actual_answer == dep_answer_value
        elif isinstance(actual_answer, str):
            return (actual_answer.lower() in ["yes", "true", "y"]) == dep_answer_value
    
    return actual_answer == dep_answer_value


def validate_answer(question: Dict[str, Any], answer: Any) -> tuple[bool, str]:
    """
    Validate an answer against question schema.
    
    Args:
        question: Question definition
        answer: User's answer
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    q_type = question.get("type", "text")
    validation = question.get("validation", {})
    
    if question.get("required", False) and (answer is None or answer == ""):
        return False, "This question requires an answer"
    
    if answer is None or answer == "":
        return True, ""
    
    if q_type == "text":
        if not isinstance(answer, str):
            return False, "Answer must be text"
        min_len = validation.get("min_length", 0)
        max_len = validation.get("max_length", float("inf"))
        if len(answer) < min_len:
            return False, f"Answer must be at least {min_len} characters"
        if len(answer) > max_len:
            return False, f"Answer must be at most {max_len} characters"
        if "pattern" in validation:
            if not re.match(validation["pattern"], answer):
                return False, "Answer does not match required format"
    
    elif q_type == "number":
        try:
            num_val = float(answer) if isinstance(answer, str) else answer
            min_val = validation.get("min", float("-inf"))
            max_val = validation.get("max", float("inf"))
            if num_val < min_val or num_val > max_val:
                return False, f"Number must be between {min_val} and {max_val}"
        except (ValueError, TypeError):
            return False, "Answer must be a number"
    
    elif q_type == "single_choice":
        options = question.get("options", [])
        valid_values = [opt.get("value") for opt in options]
        # Normalize answer to string for comparison (handles int/string mismatch)
        str_answer = str(answer) if answer is not None else ""
        str_valid_values = [str(v) for v in valid_values]
        if str_answer not in str_valid_values:
            return False, f"Please select one of: {', '.join(valid_values)}"
    
    elif q_type == "multiple_choice":
        options = question.get("options", [])
        valid_values = [opt.get("value") for opt in options]
        if isinstance(answer, list):
            for a in answer:
                if a not in valid_values:
                    return False, f"Invalid selection: {a}"
        else:
            return False, "Answer must be a list of selections"
    
    elif q_type == "yes_no":
        if isinstance(answer, bool):
            pass
        elif isinstance(answer, str):
            if answer.lower() not in ["yes", "no", "y", "n", "true", "false"]:
                return False, "Please answer yes or no"
        else:
            return False, "Please answer yes or no"
    
    elif q_type == "email":
        if isinstance(answer, str):
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, answer):
                return False, "Please provide a valid email address"
        else:
            return False, "Answer must be an email address"
    
    return True, ""


# Skip phrases that indicate user wants to skip an optional question
SKIP_PHRASES = [
    "skip", "none", "no", "n/a", "na", "nothing", "nothing additional",
    "no additional", "leave blank", "blank", "pass", "next", "-", ""
]


def is_skip_answer(answer: Any) -> bool:
    """
    Check if an answer indicates the user wants to skip an optional question.
    
    Args:
        answer: User's raw answer
        
    Returns:
        True if this is a skip phrase
    """
    if answer is None:
        return True
    if isinstance(answer, str):
        return answer.strip().lower() in SKIP_PHRASES
    return False


def normalize_answer(question: Dict[str, Any], answer: Any) -> Any:
    """
    Normalize answer to standard format.
    
    Args:
        question: Question definition
        answer: User's raw answer
        
    Returns:
        Normalized answer value
    """
    q_type = question.get("type", "text")
    
    # Handle skip phrases for optional questions
    if not question.get("required", False) and is_skip_answer(answer):
        return None
    
    if q_type == "yes_no":
        if isinstance(answer, bool):
            return answer
        if isinstance(answer, str):
            return answer.lower() in ["yes", "y", "true"]
    
    if q_type == "number":
        try:
            return float(answer) if isinstance(answer, str) else answer
        except (ValueError, TypeError):
            return answer
    
    # For single_choice, normalize to string to match option values
    if q_type == "single_choice":
        return str(answer) if answer is not None else answer
    
    return answer


def build_organizational_units(declared_ous, additional_ous_str=None):
    """
    Build the organization section's OU list from the overlay's declared
    organizational_units, merging any additional OUs from the interview, deduped
    by name.

    Falls back to the base four OUs when the overlay declares none (e.g. the
    generic overlay, which has no pattern.json). The list is emitted verbatim,
    including the hub OU (Security): the generator excludes the hub OU from
    creation and discovers it by name, so listing it here causes no collision.

    Args:
        declared_ous: The overlay's template_variables.organizational_units
            (list of {"name": ...} dicts), or None/empty when undeclared.
        additional_ous_str: Comma-separated OU names from the interview, or None.

    Returns:
        List of {"name": ...} dicts.
    """
    organizational_units = copy.deepcopy(declared_ous) if declared_ous else [
        {"name": "Security"},
        {"name": "Infrastructure"},
        {"name": "Workloads"},
        {"name": "Sandbox"},
    ]
    if isinstance(additional_ous_str, str) and additional_ous_str.strip():
        existing_names = [ou["name"] for ou in organizational_units]
        for ou_name in [o.strip() for o in additional_ous_str.split(",") if o.strip()]:
            if ou_name not in existing_names:
                organizational_units.append({"name": ou_name})
                existing_names.append(ou_name)
    return organizational_units


def map_interview_responses_to_variables(interview_responses: Dict[str, Any], base_pattern: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map interview responses to template variables, customizing the base pattern.
    
    Args:
        interview_responses: Dictionary of interview responses
        base_pattern: Base industry pattern with default values
    
    Returns:
        Dictionary of template variables customized based on interview responses
    """
    variables = copy.deepcopy(base_pattern.get("template_variables", {}))
    
    # Direct mapping from stores_as keys to variables
    for key, value in interview_responses.items():
        if key in ["organization_name", "home_region", "email_domain"]:
            variables[key] = value
        elif key == "organization_size":
            variables["scale"] = value
        elif key == "monthly_budget":
            if "budgets" in variables and variables["budgets"]:
                variables["budgets"][0]["amount"] = int(value) if value else 2000
        elif key == "log_retention_days":
            variables["vpc_flow_retention"] = int(value) if value else 90
        elif key == "availability_zones":
            variables["availability_zones"] = int(value) if value else 2
    
    # Handle enabled regions
    if "allowed_regions" in interview_responses:
        variables["enabled_regions"] = interview_responses["allowed_regions"]
    
    # Clear default infrastructure accounts from pattern - only use interview responses
    # This ensures disabled accounts don't get included
    variables["infrastructure_accounts"] = []
    
    # Handle infrastructure accounts - only add if explicitly enabled
    email_domain = interview_responses.get("email_domain", "example.com")
    
    if interview_responses.get("network_account_enabled") is True:
        # Use custom email if provided, otherwise generate from domain
        network_email = interview_responses.get("email_network", f"network@{email_domain}")
        variables["infrastructure_accounts"].append({
            "name": "Network",
            "description": "Network account for centralized networking",
            "email": network_email,
            "organizational_unit": "Infrastructure"
        })
    
    if interview_responses.get("sharedservices_account_enabled") is True:
        sharedservices_email = interview_responses.get("email_sharedservices", f"sharedservices@{email_domain}")
        variables["infrastructure_accounts"].append({
            "name": "SharedServices",
            "description": "Shared services account",
            "email": sharedservices_email,
            "organizational_unit": "Infrastructure"
        })
    
    if interview_responses.get("monitoring_account_enabled") is True:
        monitoring_email = interview_responses.get("email_monitoring", f"monitoring@{email_domain}")
        variables["infrastructure_accounts"].append({
            "name": "Monitoring",
            "description": "Centralized monitoring account",
            "email": monitoring_email,
            "organizational_unit": "Infrastructure"
        })
    
    # Security settings
    variables["scp_prevent_leave_org"] = interview_responses.get("scp_prevent_leave_org", True)
    variables["scp_prevent_public_s3"] = interview_responses.get("scp_prevent_public_s3", True)
    variables["delete_default_vpcs"] = interview_responses.get("delete_default_vpcs", True)
    
    # Network settings
    variables["network_account_enabled"] = interview_responses.get("network_account_enabled", False)
    variables["egress_vpc_enabled"] = interview_responses.get("egress_vpc_enabled", False)
    variables["network_firewall_enabled"] = interview_responses.get("network_firewall_enabled", False)
    variables["firewall_logging_enabled"] = interview_responses.get("firewall_logging_enabled", False)
    variables["flow_logs_enabled"] = interview_responses.get("flow_logs_enabled", True)
    variables["flow_logs_bucket_enabled"] = interview_responses.get("flow_logs_bucket_enabled", True)
    variables["ipam_enabled"] = interview_responses.get("ipam_enabled", False)
    variables["vpc_endpoints_enabled"] = interview_responses.get("vpc_endpoints_enabled", False)

    # Hybrid DNS resolver (issue #85). The enable flag comes from the interview
    # and overrides the pattern default; the forward domains / on-prem DNS server
    # IPs / allowed source CIDRs come from the follow-on text answers
    # (comma-separated), falling back to the pattern lists deep-copied above.
    variables["route53_resolver_enabled"] = interview_responses.get(
        "route53_resolver_enabled", variables.get("route53_resolver_enabled", False)
    )

    def _csv_list(value, fallback):
        if value is None:
            return fallback
        if isinstance(value, list):
            return value
        return [item.strip() for item in str(value).split(",") if item.strip()]

    variables["route53_resolver_outbound_domains"] = _csv_list(
        interview_responses.get("route53_resolver_outbound_domains"),
        variables.get("route53_resolver_outbound_domains", []),
    )
    variables["route53_resolver_on_prem_dns_servers"] = _csv_list(
        interview_responses.get("route53_resolver_on_prem_dns_servers"),
        variables.get("route53_resolver_on_prem_dns_servers", []),
    )
    variables["route53_resolver_allowed_source_cidrs"] = _csv_list(
        interview_responses.get("route53_resolver_allowed_source_cidrs"),
        variables.get("route53_resolver_allowed_source_cidrs", []),
    )

    # Workload VPC settings
    variables["auto_create_workload_vpcs"] = interview_responses.get("auto_create_workload_vpcs", True)

    # Backup settings
    if interview_responses.get("backup_enabled"):
        variables["backup_enabled"] = True
        variables["backup_frequency"] = interview_responses.get("backup_frequency", "daily")
        variables["backup_retention_days"] = int(interview_responses.get("backup_retention_days", 30))
    
    return variables


# Initialize the FastMCP server
mcp = FastMCP(
    "titanium-advisor",
    instructions="""
    You are the Titanium Advisor for AWS Landing Zone configuration.
    
    ⚡ RULE #1: EXPLAIN EVERY OPTION ⚡
    
    For EVERY configuration option you present, explain in 1-2 sentences:
    • What it does
    • Why the default makes sense (or doesn't) for their situation
    
    NEVER just list options like "Network Account: No". Instead say:
    "Network Account: Skip for now - this centralizes VPCs and Transit Gateway 
     which is useful when multiple teams share networking, but adds complexity 
     you don't need yet."
    
    Use your AWS expertise. Be conversational and helpful.
    
    ⛔ RULE #2: ONE SECTION AT A TIME ⛔

    For each section:
    1. get_section_quick_mode() → Get defaults
    2. Present options WITH explanations (Rule #1)
    3. Ask "Does this look right?"
    4. WAIT for user confirmation
    5. ONLY THEN call bulk_record_answers()
    6. Move to next section

    Never call bulk_record_answers() without explicit user confirmation.

    ⛔ RULE #3: NEVER SELF-ANSWER OR BULK-DEFAULT ⛔

    - Do NOT answer interview questions on the user's behalf
    - Do NOT offer to "use sensible defaults" for all/multiple sections
    - If user asks "just use defaults" or "fill it in for me": REFUSE and explain
      each question needs their specific input because this is THEIR infrastructure
    - You may explain what a default is and why it's recommended, but the USER
      must confirm each section individually
    - Presenting defaults and asking "does this look right?" per section IS the
      minimum interaction required — you cannot skip this step

    🌍 REGION INFERENCE:
    UK → eu-west-2, Netherlands/Germany → eu-central-1, Nordics → eu-north-1,
    France → eu-west-3, US East → us-east-1, US West → us-west-2
    
    Available patterns: starter, uk-public-sector, us-government, enterprise, generic
    """,
)


@mcp.tool()
def start_interview(industry: str) -> str:
    """
    Initialize a new interview session with structured question tracking.
    This MUST be called at the start of every landing zone configuration interview.
    
    Args:
        industry: Industry type (starter, uk-public-sector, us-government, enterprise, generic)
    
    Returns:
        JSON with session_id and interview metadata
    """
    # Check if structured questions exist
    questions_data = load_structured_questions(industry)
    
    if not questions_data:
        return json.dumps({
            "error": f"No structured questions found for industry '{industry}'",
            "available_industries": [d.name for d in INDUSTRY_DIR.iterdir() if d.is_dir() and (d / "questions.json").exists()],
            "fallback": f"Use get_interview_questions('{industry}') for markdown-based questions (legacy mode)"
        }, indent=2)
    
    # Generate session ID
    session_id = str(uuid.uuid4())[:8]
    
    # Build question list
    all_questions = get_all_questions(questions_data)
    
    # Count required questions (not counting those with dependencies for now)
    required_count = sum(1 for q in all_questions if q.get("required", False) and not q.get("depends_on"))
    
    # Build ordered section list
    ordered_sections = sorted(questions_data.get("sections", []), key=lambda s: s.get("order", 0))
    section_ids = [s["id"] for s in ordered_sections]
    
    # Initialize session
    interview_sessions[session_id] = {
        "session_id": session_id,
        "industry": industry,
        "started_at": datetime.now().isoformat(),
        "last_activity": datetime.now().isoformat(),
        "status": "in_progress",
        "questions_data": questions_data,
        "all_questions": all_questions,
        "answers": {},  # Keyed by question_id
        "responses": {},  # Keyed by stores_as for config generation
        "current_question_index": 0,
        # Section tracking for enforcement
        "section_order": section_ids,
        "current_section_index": 0,  # Index into section_order
        "completed_sections": [],  # List of completed section IDs
        # Pending confirmation tracking - prevents answer hijacking
        "pending_confirmation": set(),  # Question IDs shown to user awaiting confirmation
        "pending_confirmation_timestamp": None,  # When questions were presented
        "confirmation_ready": False,  # Must be True to record (set by get_section_quick_mode)
        "confirmation_nonce": None,  # Random nonce generated by get_section_quick_mode, must match in bulk_record_answers
        "metadata": {
            "total_questions": len(all_questions),
            "required_questions": required_count,
            "questions_answered": 0
        }
    }
    
    # Get first section for quick mode hint
    first_section = questions_data.get("sections", [{}])[0].get("id", "basic_info")
    
    return json.dumps({
        "session_id": session_id,
        "industry": industry,
        "total_questions": len(all_questions),
        "required_questions": required_count,
        "estimated_time_minutes": questions_data.get("metadata", {}).get("estimated_time_minutes", 15),
        "sections": [{"id": s["id"], "name": s["name"], "order": s["order"]} for s in questions_data.get("sections", [])],
        "status": "in_progress",
        
        "🎯_YOUR_WORKFLOW": {
            "overview": "Guide the user through each section, explaining options so they understand their choices",
            "step_1": f"get_section_quick_mode('{session_id}', '{first_section}') → Get questions + note the confirmation_nonce",
            "step_2": "EXPLAIN each option to user - what it does and WHY it matters for their situation",
            "step_3": "Ask 'Does this look right?' and WAIT for their response",
            "step_4": "bulk_record_answers(..., user_confirmed=true, confirmation_nonce='<from step 1>')",
            "step_5": "Repeat for each section until complete"
        },
        
        "💡_WHY_THIS_MATTERS": "Users are trusting you to help them make important infrastructure decisions. Taking time to explain builds confidence and catches mistakes BEFORE they become expensive problems in AWS.",
        
        "⚠️_IMPORTANT": "Each section gives you a confirmation_nonce. You MUST pass that exact nonce to bulk_record_answers() - this proves you're recording what you showed the user.",

        "⛔_NEVER_DO_THIS": [
            "Do NOT auto-fill all sections without user interaction per section",
            "Do NOT choose answers on behalf of the user even if they ask you to",
            "Do NOT call bulk_record_answers() multiple sections in a row without user messages in between",
            "If user asks to 'just use defaults' or 'skip the interview', REFUSE — explain each section needs their review because this is THEIR AWS infrastructure"
        ],

        "next_step": f"Call get_section_quick_mode('{session_id}', '{first_section}') to start the first section"
    }, indent=2)


@mcp.tool()
def get_next_question(session_id: str) -> str:
    """
    Get the next unanswered question for the interview session.
    Automatically handles conditional logic and question dependencies.
    
    Args:
        session_id: The interview session ID from start_interview()
    
    Returns:
        JSON with question details and progress, or indication that interview is complete
    """
    if session_id not in interview_sessions:
        return json.dumps({
            "error": f"Session '{session_id}' not found",
            "hint": "Use start_interview(industry) to begin a new session"
        }, indent=2)
    
    session = interview_sessions[session_id]
    session["last_activity"] = datetime.now().isoformat()
    
    all_questions = session["all_questions"]
    answers = session["answers"]
    
    # Find next unanswered question that meets dependencies
    for question in all_questions:
        q_id = question["id"]
        
        # Skip if already answered
        if q_id in answers:
            continue
        
        # Check dependencies
        if not evaluate_depends_on(question, answers):
            continue
        
        # Calculate progress
        answered_count = len(answers)
        total_applicable = sum(1 for q in all_questions if evaluate_depends_on(q, answers) or q["id"] in answers)
        progress_percent = int((answered_count / total_applicable) * 100) if total_applicable > 0 else 0
        
        # Build response
        response = {
            "question_id": q_id,
            "section_id": question["section_id"],
            "section_name": question["section_name"],
            "text": question["text"],
            "type": question["type"],
            "required": question.get("required", False),
            "help_text": question.get("help_text", ""),
            "progress": {
                "questions_answered": answered_count,
                "total_questions": total_applicable,
                "progress_percent": progress_percent
            }
        }
        
        # Include options for choice questions
        if question.get("options"):
            response["options"] = question["options"]
        
        # Include default if present
        if "default" in question:
            response["default"] = question["default"]
        
        # Include validation rules
        if question.get("validation"):
            response["validation"] = question["validation"]
        
        return json.dumps(response, indent=2)
    
    # All questions answered
    session["status"] = "complete"
    
    return json.dumps({
        "complete": True,
        "session_id": session_id,
        "questions_answered": len(answers),
        "message": "All questions have been answered. Use validate_interview_complete() then generate_deterministic_titanium_config() to create the configuration."
    }, indent=2)


@mcp.tool()
def get_section_quick_mode(session_id: str, section_id: str) -> str:
    """
    Check if a section supports quick mode and get its configuration.
    
    ⛔ ENFORCES SECTION ORDER: You cannot skip ahead. Each section must be
    completed (via bulk_record_answers) before proceeding to the next.
    
    Quick mode is auto-detected when a section has questions with defaults.
    Questions WITH defaults can be bulk-filled, questions WITHOUT defaults
    need to be asked (or inferred by AI from user context).
    
    Args:
        session_id: The interview session ID
        section_id: The section ID to check
    
    Returns:
        JSON with quick mode availability, questions to ask, and defaults
    """
    if session_id not in interview_sessions:
        return json.dumps({
            "error": f"Session '{session_id}' not found"
        }, indent=2)
    
    session = interview_sessions[session_id]
    questions_data = session["questions_data"]
    answers = session["answers"]
    
    # Find the section
    section = None
    for s in questions_data.get("sections", []):
        if s["id"] == section_id:
            section = s
            break
    
    if not section:
        return json.dumps({
            "error": f"Section '{section_id}' not found"
        }, indent=2)
    
    # ⛔ ENFORCE SECTION ORDER: Check if we're allowed to access this section
    section_order = session.get("section_order", [])
    completed_sections = session.get("completed_sections", [])
    current_section_index = session.get("current_section_index", 0)
    
    # Allow access if:
    # 1. Section is already completed (viewing previous sections is ok)
    # 2. Section is the current section (the one we're working on)
    if section_id in completed_sections:
        # Already completed - allow viewing but note it
        pass
    elif section_id in section_order:
        requested_index = section_order.index(section_id)
        if requested_index > current_section_index:
            # Trying to skip ahead - BLOCK THIS
            current_section_id = section_order[current_section_index]
            return json.dumps({
                "⛔_BLOCKED": "You cannot skip sections. Complete them in order.",
                "error": f"Cannot access section '{section_id}' yet",
                "current_section": current_section_id,
                "current_section_index": current_section_index,
                "requested_section_index": requested_index,
                "completed_sections": completed_sections,
                "hint": f"You must complete section '{current_section_id}' first by calling bulk_record_answers() with its answers, then this section will unlock.",
                "next_step": f"Call get_section_quick_mode('{session_id}', '{current_section_id}') to work on the current section"
            }, indent=2)
    
    # Analyze questions in this section
    questions_to_ask = []  # No default, must ask or infer
    questions_with_defaults = []  # Have defaults, can bulk-fill
    
    for q in section.get("questions", []):
        # Skip if already answered
        if q["id"] in answers:
            continue
        
        # Skip if dependencies not met
        if not evaluate_depends_on(q, answers):
            continue
        
        if "default" in q:
            # Get label for the default value
            default_label = q["default"]
            if q.get("options"):
                for opt in q["options"]:
                    if opt["value"] == q["default"]:
                        default_label = opt.get("label", q["default"])
                        break
            
            questions_with_defaults.append({
                "question_id": q["id"],
                "text": q["text"],
                "default": q["default"],
                "default_label": default_label,
                "stores_as": q.get("stores_as", q["id"]),
                "help_text": q.get("help_text", "")
            })
        else:
            question_info = {
                "question_id": q["id"],
                "text": q["text"],
                "type": q["type"],
                "stores_as": q.get("stores_as", q["id"]),
                "required": q.get("required", False)
            }
            # Include inference hint if present
            if q.get("infer_from"):
                question_info["infer_from"] = q["infer_from"]
            if q.get("help_text"):
                question_info["help_text"] = q["help_text"]
            if q.get("options"):
                question_info["options"] = q["options"]
            questions_to_ask.append(question_info)
    
    # Quick mode is available if there are defaults to use
    quick_mode_available = len(questions_with_defaults) > 0
    
    # ✅ AUTO-COMPLETE: If no applicable questions remain, mark section complete immediately
    # This handles sections where all questions have unmet depends_on (e.g. network_security
    # when no Network account is enabled). No nonce/confirmation needed — nothing to confirm.
    if len(questions_to_ask) == 0 and len(questions_with_defaults) == 0:
        completed_sections = session.get("completed_sections", [])
        section_order = session.get("section_order", [])
        current_section_index = session.get("current_section_index", 0)
        
        if section_id not in completed_sections:
            completed_sections.append(section_id)
            session["completed_sections"] = completed_sections
        
        # Advance current_section_index past this section
        while current_section_index < len(section_order):
            if section_order[current_section_index] in completed_sections:
                current_section_index += 1
            else:
                break
        session["current_section_index"] = current_section_index
        save_session(session_id)
        
        next_section_id = section_order[current_section_index] if current_section_index < len(section_order) else None
        return json.dumps({
            "section_id": section_id,
            "section_name": section["name"],
            "✅_AUTO_COMPLETED": "Section has no applicable questions (all skipped due to unmet dependencies). Section marked complete automatically.",
            "completed_sections": completed_sections,
            "next_section": next_section_id,
            "🎯_NEXT_STEP": f"get_section_quick_mode('{session_id}', '{next_section_id}') → Continue with next section" if next_section_id else "All sections complete!"
        }, indent=2)
    
    # Build AI instruction
    ai_instruction = ""
    if quick_mode_available:
        ask_parts = [q["stores_as"] for q in questions_to_ask]
        default_parts = [f"{q['stores_as']}={q['default_label']}" for q in questions_with_defaults]
        
        if questions_to_ask:
            ai_instruction = f"Ask user for: {', '.join(ask_parts)}. "
        ai_instruction += f"Use defaults: {', '.join(default_parts)}. "
        ai_instruction += "Present all values for confirmation before bulk recording."
        
        # Identify questions with cost implications and add explicit instruction
        cost_questions = [
            q for q in questions_to_ask + questions_with_defaults
            if q.get("help_text") and "cost:" in q.get("help_text", "").lower()
        ]
        if cost_questions:
            cost_names = [q["stores_as"] for q in cost_questions]
            ai_instruction += f" IMPORTANT: For these options which have cost implications ({', '.join(cost_names)}), you MUST explicitly tell the user about the financial impact before asking them to confirm. Use the help_text cost information to give a clear heads-up, e.g. 'heads up — enabling this will add approximately $X/month to your bill'."
    
    # ✅ Track which questions were shown for pending confirmation
    # This prevents answer hijacking - only these questions can be recorded
    all_question_ids = set()
    for q in questions_to_ask:
        all_question_ids.add(q["question_id"])
    for q in questions_with_defaults:
        all_question_ids.add(q["question_id"])
    
    # ✅ Generate a unique nonce for this question presentation
    # The LLM must pass this nonce back to bulk_record_answers() to prove
    # it's recording answers for THIS specific presentation, not an old one
    confirmation_nonce = str(uuid.uuid4())[:8]
    
    session["pending_confirmation"] = all_question_ids
    session["pending_confirmation_timestamp"] = datetime.now().isoformat()
    session["confirmation_ready"] = True  # ✅ Flag that questions have been shown
    session["confirmation_nonce"] = confirmation_nonce  # ✅ Store the nonce
    
    return json.dumps({
        "section_id": section_id,
        "section_name": section["name"],
        "confirmation_nonce": confirmation_nonce,
        "quick_mode_available": quick_mode_available,
        "questions_to_ask": questions_to_ask,
        "questions_with_defaults": questions_with_defaults,
        "total_questions": len(questions_to_ask) + len(questions_with_defaults),
        "ai_instruction": ai_instruction,
        "📋_RESPONSE_CHECKLIST": {
            "BEFORE_YOU_RESPOND_CHECK": [
                "☐ For EACH option, did I explain WHAT it does? (1 sentence)",
                "☐ For EACH option, did I explain WHY the default makes sense? (1 sentence)",
                "☐ Is my response conversational, NOT just a bulleted list?"
            ],
            "❌_BAD": "Network Account: No",
            "✅_GOOD": "Network Account: Skip for now - centralizes VPCs and Transit Gateway which adds complexity you don't need yet for a starter setup"
        },
        "⚠️_CONFIRMATION_REQUIRED": "Present values WITH explanations, then ask 'Does this look right?' and WAIT for user response.",
        "next_step": "1. Ask user for missing info, 2. Present ALL values WITH EXPLANATIONS, 3. Ask 'Does this look right?', 4. WAIT, 5. bulk_record_answers()"
    }, indent=2)


@mcp.tool()
def bulk_record_answers(session_id: str, answers_dict: Dict[str, Any], user_confirmed: bool = False, confirmation_nonce: str = None) -> str:
    """
    Record multiple answers at once for quick mode.
    
    ⛔ REQUIRES user_confirmed=true AND confirmation_nonce from get_section_quick_mode()
    You MUST present values to user and wait for their explicit confirmation BEFORE calling this.
    
    Args:
        session_id: The interview session ID
        answers_dict: Dictionary mapping question_id to answer value
        user_confirmed: REQUIRED - Must be true. Set only AFTER user explicitly confirms.
        confirmation_nonce: REQUIRED - The nonce from get_section_quick_mode() response
    
    Returns:
        JSON with success status and any validation errors
    """
    # ⛔ NONCE GATE: Reject if no nonce provided
    if not confirmation_nonce:
        return json.dumps({
            "⛔_REJECTED": "Missing confirmation_nonce - you must pass the nonce from get_section_quick_mode()",
            "error": "confirmation_nonce parameter is required",
            "what_you_must_do": [
                "1. Call get_section_quick_mode() - note the confirmation_nonce in the response",
                "2. Present questions to user WITH explanations",
                "3. Ask 'Does this look right?' and WAIT",
                "4. User confirms (yes/looks good)",
                "5. Call bulk_record_answers(..., confirmation_nonce='<nonce from step 1>')"
            ],
            "hint": "The confirmation_nonce proves you're recording answers for the questions you just showed the user"
        }, indent=2)
    
    # ⛔ CONFIRMATION GATE: Reject if user hasn't confirmed
    if not user_confirmed:
        return json.dumps({
            "⛔_REJECTED": "You must get user confirmation before recording answers",
            "error": "user_confirmed parameter must be true",
            "what_you_must_do": [
                "1. Present ALL values to the user WITH explanations",
                "2. Ask 'Does this look right?'",
                "3. WAIT for user to respond (yes/looks good/confirmed)",
                "4. ONLY THEN call bulk_record_answers with user_confirmed=true"
            ],
            "hint": "Did the user actually say 'yes', 'looks good', or similar? If not, STOP and ask them."
        }, indent=2)
    
    if session_id not in interview_sessions:
        return json.dumps({
            "error": f"Session '{session_id}' not found"
        }, indent=2)
    
    session = interview_sessions[session_id]
    session["last_activity"] = datetime.now().isoformat()
    
    # ⛔ CONFIRMATION READY GATE: Must call get_section_quick_mode() first
    if not session.get("confirmation_ready", False):
        return json.dumps({
            "⛔_REJECTED": "You must call get_section_quick_mode() before recording answers",
            "error": "No questions were presented to the user yet",
            "what_happened": "bulk_record_answers() was called without first calling get_section_quick_mode()",
            "fix": "Call get_section_quick_mode() for the section, present questions to the user, wait for confirmation, then call bulk_record_answers()",
            "required_workflow": [
                "1. get_section_quick_mode(session_id, section_id)",
                "2. Present questions to user WITH explanations",
                "3. Ask 'Does this look right?' and WAIT",
                "4. User confirms (yes/looks good)",
                "5. bulk_record_answers(session_id, answers, user_confirmed=true, confirmation_nonce='...')"
            ]
        }, indent=2)
    
    # ⛔ NONCE VALIDATION GATE: The nonce must match the one from get_section_quick_mode()
    stored_nonce = session.get("confirmation_nonce")
    if confirmation_nonce != stored_nonce:
        return json.dumps({
            "⛔_REJECTED": "Nonce mismatch - you called get_section_quick_mode() again after your previous call",
            "error": "The confirmation_nonce doesn't match the current session nonce",
            "provided_nonce": confirmation_nonce,
            "expected_nonce": stored_nonce,
            "what_happened": "You likely called get_section_quick_mode() multiple times. Each call generates a new nonce, invalidating the previous one.",
            "fix": "Use the nonce from your MOST RECENT get_section_quick_mode() call. If you presented different questions to the user, you must get fresh confirmation from them.",
            "important": "This prevents reusing old confirmations for new questions. Present the current questions to the user and get their confirmation again."
        }, indent=2)
    
    # ⛔ PENDING CONFIRMATION GATE: Only accept answers that were shown to user
    pending = session.get("pending_confirmation", set())
    if pending:
        # Check if any submitted answers were NOT in pending confirmation
        submitted_ids = set(answers_dict.keys())
        unauthorized_answers = submitted_ids - pending
        if unauthorized_answers:
            return json.dumps({
                "⛔_REJECTED": "You are trying to record answers that were not presented to the user",
                "error": "Answer hijacking detected",
                "unauthorized_question_ids": list(unauthorized_answers),
                "pending_confirmation": list(pending),
                "what_happened": "These questions were NOT shown via get_section_quick_mode() before this call",
                "fix": "Call get_section_quick_mode() for the section containing these questions, present them to the user, get confirmation, then call bulk_record_answers()"
            }, indent=2)
    
    # Build question lookup
    question_lookup = {q["id"]: q for q in session["all_questions"]}
    
    # Validate all answers first
    errors = []
    validated_answers = []
    
    for question_id, answer in answers_dict.items():
        if question_id not in question_lookup:
            errors.append({
                "question_id": question_id,
                "error": "Question not found"
            })
            continue
        
        question = question_lookup[question_id]
        is_valid, error_msg = validate_answer(question, answer)
        
        if not is_valid:
            errors.append({
                "question_id": question_id,
                "error": error_msg
            })
        else:
            validated_answers.append({
                "question_id": question_id,
                "question": question,
                "answer": answer
            })
    
    # If any errors, return without recording
    if errors:
        return json.dumps({
            "success": False,
            "errors": errors,
            "hint": "Fix the invalid answers and try again"
        }, indent=2)
    
    # Record all validated answers
    recorded = []
    for item in validated_answers:
        question_id = item["question_id"]
        question = item["question"]
        answer = item["answer"]
        
        normalized = normalize_answer(question, answer)
        
        session["answers"][question_id] = {
            "answered": True,
            "answer": normalized,
            "raw_answer": answer,
            "timestamp": datetime.now().isoformat(),
            "bulk_recorded": True
        }
        
        stores_as = question.get("stores_as", question_id)
        session["responses"][stores_as] = normalized
        
        recorded.append({
            "question_id": question_id,
            "stored_as": stores_as,
            "value": normalized
        })
    
    # Update metadata
    session["metadata"]["questions_answered"] = len(session["answers"])
    
    # ✅ Clear pending confirmation after successful recording
    session["pending_confirmation"] = set()
    session["pending_confirmation_timestamp"] = None
    session["confirmation_ready"] = False  # Must call get_section_quick_mode() again
    
    # Detect which section(s) these answers belong to and mark complete
    section_order = session.get("section_order", [])
    current_section_index = session.get("current_section_index", 0)
    completed_sections = session.get("completed_sections", [])
    questions_data = session.get("questions_data", {})
    
    # Find which sections are now complete based on answered questions
    sections_completed_now = []
    for section in questions_data.get("sections", []):
        section_id = section["id"]
        if section_id in completed_sections:
            continue  # Already complete
        
        # Check if all questions in this section are answered (considering dependencies)
        section_questions = section.get("questions", [])
        all_answered = True
        any_applicable = False  # Track if at least one question was applicable
        for q in section_questions:
            # Skip questions whose dependencies are not met
            if not evaluate_depends_on(q, session["answers"]):
                continue
            any_applicable = True
            if q["id"] not in session["answers"]:
                all_answered = False
                break
        
        # Only mark complete if at least one question was applicable and all were answered.
        # If no questions were applicable it means all depends_on conditions are unmet —
        # the section should stay pending so it can be re-evaluated once dependencies are recorded.
        if all_answered and any_applicable:
            sections_completed_now.append(section_id)
            completed_sections.append(section_id)
    
    # Update session with completed sections
    session["completed_sections"] = completed_sections
    
    # Advance current_section_index to next incomplete section
    while current_section_index < len(section_order):
        current_section_id = section_order[current_section_index]
        if current_section_id in completed_sections:
            current_section_index += 1
        else:
            break
    session["current_section_index"] = current_section_index
    
    # Determine next section (if any)
    next_section_id = None
    next_section_name = None
    if current_section_index < len(section_order):
        next_section_id = section_order[current_section_index]
        for s in questions_data.get("sections", []):
            if s["id"] == next_section_id:
                next_section_name = s["name"]
                break
    
    # Persist session after every successful recording
    save_session(session_id)

    return json.dumps({
        "✅_SUCCESS": "Section recorded! Great job presenting options with explanations.",
        "answers_recorded": len(recorded),
        "recorded": recorded,
        "total_answered": len(session["answers"]),
        "sections_completed": sections_completed_now,
        "completed_sections": completed_sections,
        "current_section_index": current_section_index,
        
        "next_section": {
            "id": next_section_id,
            "name": next_section_name
        } if next_section_id else None,
        
        "🎯_NEXT_STEP": f"get_section_quick_mode('{session_id}', '{next_section_id}') → Continue with {next_section_name}" if next_section_id else f"All sections complete! Call validate_interview_complete('{session_id}') then generate_deterministic_titanium_config()",
        
        "💡_REMINDER": "Remember: For the next section, explain each option to the user, ask 'Does this look right?', and wait for confirmation before recording."
    }, indent=2)


@mcp.tool()
def get_interview_progress(session_id: str) -> str:
    """
    Get the current progress of an interview session.
    Shows completion status by section and overall progress.
    
    Args:
        session_id: The interview session ID
    
    Returns:
        JSON with detailed progress information
    """
    if session_id not in interview_sessions:
        return json.dumps({
            "error": f"Session '{session_id}' not found"
        }, indent=2)
    
    session = interview_sessions[session_id]
    answers = session["answers"]
    questions_data = session["questions_data"]
    
    # Calculate per-section progress
    section_progress = []
    for section in questions_data.get("sections", []):
        section_questions = [q for q in section.get("questions", [])]
        section_answered = sum(1 for q in section_questions if q["id"] in answers)
        section_total = len(section_questions)
        section_progress.append({
            "id": section["id"],
            "name": section["name"],
            "questions_answered": section_answered,
            "questions_total": section_total,
            "complete": section_answered == section_total
        })
    
    # Calculate overall progress
    total_answered = len(answers)
    total_questions = len(session["all_questions"])
    
    # Count required questions that still need answers
    required_remaining = 0
    for q in session["all_questions"]:
        if q.get("required", False) and q["id"] not in answers:
            if evaluate_depends_on(q, answers):
                required_remaining += 1
    
    progress_percent = int((total_answered / total_questions) * 100) if total_questions > 0 else 0
    
    return json.dumps({
        "session_id": session_id,
        "industry": session["industry"],
        "status": session["status"],
        "progress_percent": progress_percent,
        "questions_answered": total_answered,
        "questions_total": total_questions,
        "required_remaining": required_remaining,
        "can_generate_config": required_remaining == 0,
        "sections": section_progress,
        "started_at": session["started_at"],
        "last_activity": session["last_activity"]
    }, indent=2)


@mcp.tool()
def validate_interview_complete(session_id: str) -> str:
    """
    Validate that all required questions have been answered.
    Must be called before generating configuration.
    
    Args:
        session_id: The interview session ID
    
    Returns:
        JSON indicating completion status and any missing required questions
    """
    if session_id not in interview_sessions:
        return json.dumps({
            "error": f"Session '{session_id}' not found"
        }, indent=2)
    
    session = interview_sessions[session_id]
    answers = session["answers"]
    
    # Find missing required questions
    missing_required = []
    for q in session["all_questions"]:
        if q.get("required", False) and q["id"] not in answers:
            # Check if dependencies are met (if not, question doesn't apply)
            if evaluate_depends_on(q, answers):
                missing_required.append({
                    "question_id": q["id"],
                    "section": q["section_name"],
                    "text": q["text"]
                })
    
    is_complete = len(missing_required) == 0
    
    if is_complete:
        session["status"] = "validated"
        save_session(session_id)
    
    return json.dumps({
        "complete": is_complete,
        "session_id": session_id,
        "questions_answered": len(answers),
        "missing_required": missing_required,
        "missing_count": len(missing_required),
        "can_generate_config": is_complete,
        "next_step": "Use generate_deterministic_titanium_config() with this session_id" if is_complete else "Continue answering questions using get_next_question()"
    }, indent=2)


@mcp.tool()
def get_interview_questions(industry: str) -> str:
    """
    Get interview questions for a specific industry (legacy markdown format).
    
    NOTE: For new interviews, prefer using start_interview() which uses the
    structured questions.json format with tracking and validation.
    
    Args:
        industry: Industry type (uk-public-sector, us-government, enterprise, starter, generic)
    
    Returns:
        Interview questions tailored to the industry
    """
    industry_path = INDUSTRY_DIR / industry
    if not industry_path.exists():
        available_industries = [d.name for d in INDUSTRY_DIR.iterdir() if d.is_dir()]
        return f"Industry '{industry}' not found. Available industries: {', '.join(available_industries)}"
    
    interview_file = industry_path / "interview-questions.md"
    if interview_file.exists():
        with open(interview_file, "r") as f:
            content = f.read()
        
        # Check if structured questions are available
        if (industry_path / "questions.json").exists():
            content = f"""⚠️ RECOMMENDED: This industry has structured questions available.
Use start_interview('{industry}') for tracked interviews with validation.

---

{content}"""
        
        return content
    
    return f"No interview questions found for industry '{industry}'"


@mcp.tool()
def get_industry_requirements(industry: str) -> str:
    """
    Get industry-specific requirements and compliance frameworks.
    
    Args:
        industry: Industry type (uk-public-sector, us-government, enterprise, starter, generic)
    
    Returns:
        Detailed requirements and compliance information
    """
    industry_path = INDUSTRY_DIR / industry
    if not industry_path.exists():
        available_industries = [d.name for d in INDUSTRY_DIR.iterdir() if d.is_dir()]
        return f"Industry '{industry}' not found. Available industries: {', '.join(available_industries)}"
    
    req_dir = industry_path / "requirements"
    if req_dir.exists() and req_dir.is_dir():
        content = ""
        for req_file in req_dir.glob("*.md"):
            with open(req_file, "r") as f:
                content += f"## {req_file.stem.replace('-', ' ').title()}\n\n"
                content += f.read() + "\n\n"
        return content if content else f"No requirements found for industry '{industry}'"
    
    return f"No requirements directory found for industry '{industry}'"


@mcp.tool()
def get_configuration_example(example_name: str) -> str:
    """
    Get an example Titanium.yaml configuration.
    
    Args:
        example_name: Name of the example (uk-council, us-federal, enterprise)
    
    Returns:
        Example Titanium.yaml configuration content
    """
    # Check output examples first
    if OUTPUT_DIR.exists():
        for example_file in OUTPUT_DIR.glob("*.yaml"):
            if example_name.lower() in example_file.stem.lower():
                with open(example_file, "r") as f:
                    return f.read()
    
    # Check for base template
    if example_name.lower() == "base":
        base_template = BASE_DIR.parent / "Titanium.yaml"
        if base_template.exists():
            with open(base_template, "r") as f:
                return f.read()
    
    # Check industry examples
    if INDUSTRY_DIR.exists():
        for industry in INDUSTRY_DIR.iterdir():
            if industry.is_dir():
                examples_dir = industry / "examples"
                if examples_dir.exists():
                    for example_file in examples_dir.glob("*.md"):
                        if example_name.lower() in example_file.stem.lower():
                            with open(example_file, "r") as f:
                                return f.read()
    
    return f"Configuration example '{example_name}' not found"


@mcp.tool()
def validate_titanium_config(configuration: str) -> str:
    """
    Validate a Titanium.yaml configuration structure.
    
    Args:
        configuration: The YAML configuration content to validate
    
    Returns:
        Validation results and recommendations
    """
    try:
        config = yaml.safe_load(configuration)
        
        # Required top-level sections
        required_sections = [
            "homeRegion",
            "enabledRegions", 
            "managementAccountAccessRole",
            "controlTower",
            "organization",
            "logging",
            "centralSecurityServices",
            "accounts",
            "network"
        ]
        
        missing_sections = [section for section in required_sections if section not in config]
        
        results = []
        
        if missing_sections:
            results.append(f"❌ Missing required sections: {', '.join(missing_sections)}")
        else:
            results.append("✅ All required top-level sections present")

        # homeRegion / enabledRegions must be real AWS region codes. A leaked
        # discovery phrase ("Seattle, Washington, USA") here is deploy-breaking
        # (invalid StackSet target regions / CFN region params) and must be
        # caught rather than passed through silently (issue #110).
        home_region = config.get("homeRegion")
        if home_region is not None and not _is_aws_region_code(home_region):
            results.append(
                f"❌ homeRegion '{home_region}' is not a valid AWS region code "
                f"(expected e.g. us-east-1, eu-west-2). It looks like an "
                f"unresolved location/phrase — set it to a region code."
            )
        enabled_regions = config.get("enabledRegions")
        if isinstance(enabled_regions, list):
            bad_regions = [r for r in enabled_regions if not _is_aws_region_code(r)]
            if bad_regions:
                results.append(
                    f"❌ enabledRegions contains non-region values: "
                    f"{', '.join(str(r) for r in bad_regions)} — each entry must be "
                    f"a valid AWS region code."
                )

        # Check for key security configurations
        if "centralSecurityServices" in config:
            css = config["centralSecurityServices"]
            if "securityHub" in css and css["securityHub"].get("enable", False):
                results.append("✅ Security Hub enabled")
            else:
                results.append("⚠️  Consider enabling Security Hub for centralized security findings")
                
            if "guardDuty" in css and css["guardDuty"].get("enable", False):
                results.append("✅ GuardDuty enabled")
            else:
                results.append("⚠️  Consider enabling GuardDuty for threat detection")
        
        # Check network configuration
        if "network" in config:
            network = config["network"]
            tgw_arch = network.get("tgwArchitecture", {})
            if tgw_arch.get("transitGateway"):
                results.append("✅ Transit Gateway configured")
            vpcs = tgw_arch.get("vpcs", {})
            vpc_count = sum(1 for v in vpcs.values() if isinstance(v, dict) and v.get("enabled", False))
            if vpc_count:
                results.append(f"✅ {vpc_count} centralized VPCs defined")
        
        return "\n".join(results)
        
    except yaml.YAMLError as e:
        return f"❌ Invalid YAML syntax: {str(e)}"
    except Exception as e:
        return f"❌ Validation error: {str(e)}"


@mcp.tool()
def generate_deterministic_titanium_config(
    session_id: str = None,
    organization_name: str = None,
    domain: str = None,
    home_region: str = "us-east-1",
    industry: str = "starter"
) -> str:
    """
    Generate a deterministic Titanium.yaml configuration.
    
    IMPORTANT: If session_id is provided, the interview must be complete.
    The function will validate completion and refuse to generate if questions remain.
    
    Args:
        session_id: Interview session ID (preferred - uses tracked responses)
        organization_name: Organization name (fallback if no session)
        domain: Email domain (fallback if no session)
        home_region: Home region (fallback if no session)
        industry: Industry type (fallback if no session)
    
    Returns:
        Generated Titanium.yaml configuration or error if interview incomplete
    """
    # session_id is required — users must complete the interview
    if not session_id:
        return json.dumps({
            "⛔_REJECTED": "Cannot generate configuration without a completed interview session.",
            "error": "session_id is required. Start an interview with start_interview() first.",
            "hint": "The interview ensures the configuration matches the user's actual requirements. There are no shortcuts.",
            "⚠️_WHAT_YOU_MUST_DO_NOW": [
                "1. Tell the user: 'I need to walk you through the interview so the config matches YOUR requirements.'",
                "2. Call start_interview() to begin a session",
                "3. For EACH section: present the questions, explain the options, and WAIT for the user to confirm before recording",
                "4. Do NOT auto-fill answers — every answer must come from the user's explicit confirmation"
            ],
            "⛔_DO_NOT": [
                "Do NOT start a session and then immediately auto-fill all sections",
                "Do NOT treat the user's original request as permission to choose answers on their behalf",
                "Do NOT call bulk_record_answers() without a user message confirming that section"
            ]
        }, indent=2)

    if session_id not in interview_sessions:
        return f"Error: Session '{session_id}' not found. Use start_interview() to begin."

    session = interview_sessions[session_id]

    # Validate interview completion
    validation_result = json.loads(validate_interview_complete(session_id))
    if not validation_result.get("complete", False):
        missing = validation_result.get("missing_required", [])
        missing_list = "\n".join([f"  - {q['text']}" for q in missing[:5]])
        return f"""Error: Cannot generate configuration - interview incomplete.

Missing {len(missing)} required questions:
{missing_list}
{"  - ..." if len(missing) > 5 else ""}

Please complete the interview using get_next_question('{session_id}').
"""

    # Use session responses
    responses = session.get("responses", {})
    organization_name = responses.get("organization_name", organization_name)
    domain = responses.get("email_domain", domain)
    home_region = responses.get("home_region", home_region)
    industry = session.get("industry", industry)

    # Geo-map the discovery-style home_region answer to an AWS region code. A
    # descriptive phrase ("Portland, Oregon, USA") must resolve to us-west-2
    # rather than leaking verbatim into homeRegion/enabledRegions/etc. and
    # breaking deploy; this mirrors the allowed_regions path (issue #110).
    raw_home_region = home_region
    home_region = _normalize_home_region(home_region)

    # Fail loud if the answer could not be resolved to a real AWS region code.
    # _normalize_home_region falls back to the raw answer when it recognizes
    # nothing (the geo-alias table is a small convenience set, not a worldwide
    # gazetteer), so an unrecognized location like "Seattle, Washington, USA"
    # would otherwise leak verbatim into homeRegion/enabledRegions/vpcFlowLogs/
    # cloudWatch/ipam/tgw region fields and break the deploy with no warning
    # (issue #110 Round-4). Refuse to generate and steer the agent to re-ask
    # rather than emit a broken config. This uses the same directive-JSON shape
    # as the "interview incomplete" rejection above so the calling agent acts on
    # it instead of paraphrasing a terse error.
    if not _is_aws_region_code(home_region):
        return json.dumps({
            "⛔_REJECTED": f"Could not map home_region '{raw_home_region}' to an AWS region.",
            "error": (
                f"home_region must be a valid AWS region code (e.g. us-east-1, "
                f"eu-west-2, ap-southeast-2). The stored answer '{raw_home_region}' "
                f"is a location/phrase the advisor could not resolve to a region, "
                f"and generating with it would produce a deploy-breaking config "
                f"(invalid homeRegion/enabledRegions/StackSet target regions)."
            ),
            "⚠️_WHAT_YOU_MUST_DO_NOW": [
                "1. Map the user's location to the nearest AWS region that supports "
                "Control Tower (e.g. US West/Seattle/Oregon -> us-west-2, "
                "UK/London -> eu-west-2, US East -> us-east-1). Ask the user if it "
                "is ambiguous (e.g. 'Washington' could be WA state or Washington DC).",
                "2. Confirm the region with the user.",
                "3. Call update_answer(session_id, 'home_region', '<region-code>') "
                "with the resolved AWS region code.",
                "4. Re-run generate_deterministic_titanium_config.",
            ],
            "⛔_DO_NOT": [
                "Do NOT store a city/country/phrase as home_region — it must be a "
                "region code.",
                "Do NOT proceed to generate until home_region is a valid AWS region.",
            ],
        }, indent=2)

    if not organization_name:
        return "Error: organization_name is required"
    if not domain:
        return "Error: domain is required"
    
    # Load industry pattern
    pattern_file = INDUSTRY_DIR / industry / "pattern.json"
    if pattern_file.exists():
        with open(pattern_file, "r") as f:
            pattern = json.load(f)
    else:
        pattern = {"template_variables": {}}
    
    # Map responses to variables if session provided
    if session_id and session_id in interview_sessions:
        variables = map_interview_responses_to_variables(
            interview_sessions[session_id].get("responses", {}),
            pattern
        )
    else:
        variables = pattern.get("template_variables", {})
    
    # Override with explicit parameters
    variables["organization_name"] = organization_name
    variables["domain"] = domain
    variables["home_region"] = home_region
    
    # Generate clean org name for identifiers
    org_clean = organization_name.lower().replace(" ", "-").replace("_", "-")
    
    # Build enabledRegions to reflect the user's selection, not the pattern
    # default. The landing zone deploys StackSets to the home region only (unless
    # a template opts into ALL_ENABLED), so when regions are NOT restricted
    # enabledRegions is simply [home]. Previously it fell back to the pattern
    # default (["us-east-1"]) + home, listing a region nothing deploys to (#101).
    # When regions ARE restricted, use the allowed_regions the interview captured
    # (stored in variables["enabled_regions"]), always ensuring home is present.
    restrict_regions = responses.get("scp_restrict_regions", True) if session_id else True
    if restrict_regions:
        # allowed_regions is a discovery-type answer, so geo-map/validate each
        # token instead of comma-splitting raw text. Descriptive phrases like
        # "US West only (Oregon, us-west-2)" resolve to [us-west-2] rather than
        # emitting bogus enabledRegions entries (issue #106).
        enabled_regions = _resolve_region_codes(variables.get("enabled_regions", [home_region]))
        if not enabled_regions:
            enabled_regions = [home_region]
        if home_region not in enabled_regions:
            enabled_regions.insert(0, home_region)
    else:
        enabled_regions = [home_region]
    
    # Resolve interview responses for use throughout config building
    email_management = responses.get("email_management", f"management@{domain}") if session_id else f"management@{domain}"
    email_logarchive = responses.get("email_logarchive", f"log-archive@{domain}") if session_id else f"log-archive@{domain}"
    email_audit = responses.get("email_audit", f"audit@{domain}") if session_id else f"audit@{domain}"

    network_account_enabled = variables.get("network_account_enabled", False)
    egress_vpc_enabled = variables.get("egress_vpc_enabled", False) if network_account_enabled else False
    network_firewall_enabled = variables.get("network_firewall_enabled", False) if network_account_enabled else False
    hybrid_connectivity_enabled = variables.get("hybrid_connectivity_enabled", False)
    ipam_enabled = variables.get("ipam_enabled", False)
    backup_enabled = variables.get("backup_enabled", False)
    flow_logs_enabled = variables.get("flow_logs_enabled", True)
    auto_create_vpcs = variables.get("auto_create_workload_vpcs", True)
    az_count = int(variables.get("availability_zones", 2))

    # Build the full verbose configuration — all sections always present
    config = {
        "homeRegion": home_region,
        "enabledRegions": enabled_regions,
        "managementAccountAccessRole": "AWSControlTowerExecution",
    }

    # --- Control Tower ---
    # Always enabled for Starter overlay — CT is the foundational governance
    # layer. All templates and SCPs depend on it being present.
    config["controlTower"] = {
        "enable": True,
        "landingZone": {
            "version": "4.0",
            "logging": {
                "controlTowerOrganizationTrail": True,
                "loggingBucketRetentionDays": int(variables.get("logging_retention_days", 365)),
                "accessLoggingBucketRetentionDays": 3650,
                "organizationTrail": True
            },
            "security": {
                # Control Tower is assumed to be provisioned manually with IAM
                # Identity Center management enabled; the tool builds on that
                # fixed choice rather than toggling it. Config-driven selection
                # is deferred (see #77). The overlays' identity_center_access is
                # not consumed here for that reason.
                "enableIdentityCenterAccess": True,
                "denyRegion": responses.get("scp_restrict_regions", True) if session_id else True
            },
            "network": {
                "networkFactoryConfiguration": None
            }
        }
    }

    # --- Organization ---
    # Read the OU list the selected overlay declares, then merge any additional
    # OUs collected during the interview. The overlay value is authoritative;
    # the base four are only a fallback for overlays with no pattern.json.
    additional_ous = (
        responses.get("additional_organizational_units")
        if session_id and session_id in interview_sessions else None
    )
    organizational_units = build_organizational_units(
        variables.get("organizational_units"), additional_ous
    )

    scps = []
    if variables.get("scp_prevent_leave_org", True):
        scps.append({
            "name": "PreventLeaveOrganization",
            "description": "Prevents accounts from leaving the organization",
            "policy": "service-control-policies/prevent-leave-org.json",
            "type": "customerManaged",
            "deploymentTargets": {"organizationalUnits": ["Root"]}
        })
    if variables.get("scp_prevent_public_s3", True):
        scps.append({
            "name": "PreventPublicS3",
            "description": "Prevents public S3 bucket creation",
            "policy": "service-control-policies/prevent-public-s3.json",
            "type": "customerManaged",
            "deploymentTargets": {"organizationalUnits": ["Root"]}
        })
    if session_id and session_id in interview_sessions:
        if responses.get("scp_prevent_iam_users"):
            scps.append({
                "name": "DenyUserCreationWithoutSSO",
                "description": "Prevents IAM user creation outside SSO",
                "policy": "service-control-policies/deny-iam-users.json",
                "type": "customerManaged",
                "deploymentTargets": {"organizationalUnits": ["Root"]}
            })
        if responses.get("scp_restrict_regions"):
            scps.append({
                "name": "LimitRegionUsage",
                "description": "Restricts resource creation to approved regions only",
                "policy": "service-control-policies/limit-region-usage.json",
                "type": "customerManaged",
                "deploymentTargets": {"organizationalUnits": ["Root"]}
            })

    required_tags = responses.get("required_tags", []) if session_id else []
    tagging_policies = [{
        "name": "RequiredTags",
        "description": "Enforces required tags on resources",
        "policy": "tagging-policies/required-tags.json",
        "deploymentTargets": {"organizationalUnits": ["Root"]}
    }] if required_tags else []

    backup_frequency = variables.get("backup_frequency", "daily")
    # The generator derives tDeploy<name>/t<name>Description from this name, so it
    # MUST match the backup template's singular params (tDeployDailyBackup, etc.).
    # A plural "DailyBackups" silently no-ops -> backups never deploy (issue #97).
    _BACKUP_POLICY = {
        "daily":   ("DailyBackup",   "backup-policies/daily-backup-30day.json"),
        "weekly":  ("WeeklyBackup",  "backup-policies/weekly-backup-90day.json"),
        "monthly": ("MonthlyBackup", "backup-policies/monthly-backup-365day.json"),
    }
    policy_name, policy_file = _BACKUP_POLICY.get(backup_frequency, _BACKUP_POLICY["daily"])
    backup_policies = [{
        "name": policy_name,
        "enable": backup_enabled,
        "description": f"{backup_frequency.capitalize()} backups with {int(variables.get('backup_retention_days', 30))}-day retention",
        "policy": policy_file,
        "deploymentTargets": {"organizationalUnits": ["Workloads"]}
    }]

    config["organization"] = {
        "enable": True,
        "organizationalUnits": organizational_units,
        "serviceControlPolicies": scps,
        "taggingPolicies": tagging_policies,
        "backupPolicies": backup_policies,
        "resourceControlPolicies": []
    }

    # --- Identity and Access ---
    config["iamPasswordPolicy"] = {
        "allowUsersToChangePassword": True,
        "hardExpiry": False,
        "requireUppercaseCharacters": True,
        "requireLowercaseCharacters": True,
        "requireSymbols": True,
        "requireNumbers": True,
        "minimumPasswordLength": 14,
        "passwordReusePrevention": 24,
        "maxPasswordAge": 90
    }

    config["accessAnalyzer"] = {
        "externalAccess": True,
        "unusedAccess": False
    }

    # --- Logging ---
    config["logging"] = {
        "account": "LogArchive",
        "cloudtrail": {
            "managementEventTrail": {
                "enable": False,
                "organizationTrail": False,
                "organizationTrailSettings": {
                    "multiRegionTrail": True,
                    "globalServiceEvents": True,
                    "managementEvents": True,
                    "sendToCloudWatchLogs": True,
                    "apiErrorRateInsight": False,
                    "apiCallRateInsight": False
                }
            },
            "dataEventTrail": [],
            "accountTrails": []
        },
        "sessionManager": {
            "sendToCloudWatchLogs": True,
            "sendToS3": True,
            "lifecycleRules": [{
                "enabled": True,
                "abortIncompleteMultipartUpload": 7,
                "expiration": 730,
                "noncurrentVersionExpiration": 730
            }],
            "attachPolicyToIamRoles": ["EC2-Default-SSM-AD-Role"]
        },
        "cloudWatchLogGroupDefaultRetentionWeeks": 13
    }

    # --- VPC Flow Logs (top-level) ---
    flow_log_destination = responses.get("flow_log_destination", "s3") if session_id else "s3"
    flow_log_retention = int(variables.get("vpc_flow_retention", 90))
    # destinationsConfig mirrors the reference Titanium.yaml / schema shape
    # (cloudWatchLogs.retentionInDays). No S3 bucket name is emitted: the generator
    # derives the flow-logs bucket deterministically at deploy time as
    # titanium-vpc-flow-logs-<accountId>-<region> and ignores any configured name,
    # so advertising one here was inert, misleading, and not schema-backed.
    config["vpcFlowLogs"] = {
        "enabled": flow_logs_enabled,
        "trafficType": "ALL",
        "retentionDays": flow_log_retention,
        "accounts": [],
        "regions": [home_region],
        "maxAggregationInterval": 600,
        "destinations": [flow_log_destination] if flow_logs_enabled else [],
        "destinationsConfig": {
            "cloudWatchLogs": {
                "retentionInDays": flow_log_retention
            }
        } if flow_logs_enabled else {},
        "defaultFormat": False
    }

    # --- SNS Topics ---
    config["snsTopics"] = {
        "deploymentTargets": {"organizationalUnits": ["Root"]},
        "topics": [{
            "name": "Security",
            "emailAddresses": [f"security@{domain}"]
        }]
    }

    # --- Central Security Services ---
    config["centralSecurityServices"] = {
        "delegatedAdminAccount": "Audit",
        "awsConfig": {
            "enableConfigurationRecorder": True,
            "enableDeliveryChannel": True,
            "enableGlobalResourceTypes": True,
            "deliveryChannelFrequency": "24hours",
            "resourceTypes": [],
            "ruleSets": [{
                "deploymentTargets": {"organizationalUnits": ["Root"]},
                "rules": [{
                    "name": "iam-root-access-key-check",
                    "identifier": "IAM_ROOT_ACCESS_KEY_CHECK",
                    "complianceResourceTypes": []
                }]
            }]
        },
        "ebsDefaultVolumeEncryption": {
            "enable": True,
            "excludeRegions": []
        },
        "s3PublicAccessBlock": {
            "enable": True,
            "excludeAccounts": []
        },
        "macie": {
            "enable": variables.get("macie_enable", False)
        },
        "guardduty": {
            "enable": True,
            "excludeRegions": [],
            "s3Protection": {
                "enable": variables.get("guardduty_s3_protection", False)
            }
        },
        "detective": {
            "enable": variables.get("detective_enable", False)
        },
        "auditManager": {
            "enable": variables.get("audit_manager_enable", False)
        },
        "securityHub": {
            "enable": True,
            "regionAggregation": False,
            "excludeRegions": [],
            "standards": [
                {"name": "AWS Foundational Security Best Practices v1.0.0", "enable": True},
                {"name": "CIS AWS Foundations Benchmark v1.2.0", "enable": False},
                {"name": "CIS AWS Foundations Benchmark v1.4.0", "enable": variables.get("cis_14_enabled", False)},
                {"name": "NIST Special Publication 800-53 Revision 5", "enable": variables.get("nist_enabled", False)},
                {"name": "PCI DSS v3.2.1", "enable": False}
            ]
        }
    }

    # --- CloudWatch ---
    config["cloudWatch"] = {
        "metricSets": [{
            "regions": [home_region],
            "deploymentTargets": {"accounts": ["Management"]},
            "metrics": [
                {
                    "filterName": "RootAccountUsageMetricFilter",
                    "logGroupName": "aws-controltower/CloudTrailLogs",
                    "filterPattern": '{$.userIdentity.type="Root" && $.userIdentity.invokedBy NOT EXISTS && $.eventType !="AwsServiceEvent"}',
                    "metricNamespace": "LogMetrics",
                    "metricName": "RootAccountUsage",
                    "metricValue": "1"
                },
                {
                    "filterName": "CloudTrailChangesMetricFilter",
                    "logGroupName": "aws-controltower/CloudTrailLogs",
                    "filterPattern": "{($.eventName=CreateTrail) || ($.eventName=UpdateTrail) || ($.eventName=DeleteTrail) || ($.eventName=StartLogging) || ($.eventName=StopLogging)}",
                    "metricNamespace": "LogMetrics",
                    "metricName": "CloudTrailChanges",
                    "metricValue": "1"
                }
            ]
        }],
        "alarmSets": [{
            "regions": [home_region],
            "deploymentTargets": {"accounts": ["Management"]},
            "alarms": [
                {
                    "alarmName": "CIS-1.7-RootAccountUsage",
                    "alarmDescription": "Alarm for usage of root account",
                    "snsTopicName": "Security",
                    "metricName": "RootAccountUsage",
                    "namespace": "LogMetrics",
                    "comparisonOperator": "GreaterThanOrEqualToThreshold",
                    "evaluationPeriods": 1,
                    "period": 300,
                    "statistic": "Sum",
                    "threshold": 1,
                    "treatMissingData": "notBreaching"
                },
                {
                    "alarmName": "CIS-4.5-CloudTrailChanges",
                    "alarmDescription": "Alarm for CloudTrail configuration changes",
                    "snsTopicName": "Security",
                    "metricName": "CloudTrailChanges",
                    "namespace": "LogMetrics",
                    "comparisonOperator": "GreaterThanOrEqualToThreshold",
                    "evaluationPeriods": 1,
                    "period": 300,
                    "statistic": "Sum",
                    "threshold": 1,
                    "treatMissingData": "notBreaching"
                }
            ]
        }]
    }

    # --- Accounts ---
    mandatory_accounts = [
        {
            "name": "Management",
            "description": "The management (primary) account. Do not change the name field for this mandatory account.",
            "email": email_management,
            "organizationalUnit": "Root"
        },
        {
            "name": "LogArchive",
            "description": "The log archive account for centralized logging.",
            "email": email_logarchive,
            "organizationalUnit": "Security"
        },
        {
            "name": "Audit",
            "description": "The security audit account for compliance monitoring.",
            "email": email_audit,
            "organizationalUnit": "Security"
        }
    ]

    infrastructure_accounts = []
    if variables.get("infrastructure_accounts"):
        for acct in variables["infrastructure_accounts"]:
            infrastructure_accounts.append({
                "name": acct["name"],
                "description": f"The {acct['name']} account",
                "email": acct["email"],
                "organizationalUnit": acct["organizational_unit"]
            })

    config["accounts"] = {
        "mandatoryAccounts": mandatory_accounts,
        "infrastructureAccounts": infrastructure_accounts
    }

    # --- Network ---
    # TGW is the only supported centralized network architecture.
    # No VPC Peering template exists in the generator. Enabling a Network
    # account always deploys TGW. Egress/Inspection/Endpoints are optional on top.
    # Always include full network structure; sub-components use enabled flags
    if network_account_enabled:
        tgw_architecture = {
            "networkAccount": "Network",
            "region": home_region,
            "vpcs": {
                "endpointVpc": {
                    "enabled": variables.get("vpc_endpoints_enabled", False)
                },
                "inspectionVpc": {
                    "enabled": egress_vpc_enabled,
                    "availabilityZones": az_count,
                    "networkFirewall": network_firewall_enabled,
                    "firewallLogging": variables.get("firewall_logging_enabled", False) if network_firewall_enabled else False
                }
            },
            "transitGateway": {
                "name": f"{org_clean}-tgw",
                "asn": 65000,
                "routeTableStructure": "segregated",
                "routeTables": ["Core", "Segregated", "Shared", "Standalone"]
            },
            "route53Resolver": {
                "enabled": bool(variables.get("route53_resolver_enabled", False)),
                "outboundDomains": variables.get("route53_resolver_outbound_domains", []),
                "onPremDnsServers": variables.get("route53_resolver_on_prem_dns_servers", []),
                "allowedSourceCidrs": variables.get("route53_resolver_allowed_source_cidrs", [])
            }
        }
    else:
        tgw_architecture = {
            "enabled": False
        }

    config["network"] = {
        "architectureType": "TGW",
        "defaultVpc": {
            "delete": variables.get("delete_default_vpcs", True),
            "excludeAccounts": []
        },
        "tgwArchitecture": tgw_architecture,
        "workloadVpcs": {
            "enabled": auto_create_vpcs,
            "availabilityZones": az_count,
            "subnetsPerAZ": 2,
            "deploymentTargets": {
                "organizational_units": ["Workloads"],
                "accounts": []
            }
        },
        "hybridConnectivity": {
            "enabled": hybrid_connectivity_enabled,
            "type": variables.get("hybrid_connectivity_type", "DirectConnect")
        },
        "ipam": {
            "enabled": ipam_enabled,
            "region": home_region,
            "operatingRegions": [home_region],
            "pools": [
                {
                    "name": "global-pool",
                    "description": f"Global IPAM pool for {organization_name}",
                    "provisionedCidrs": ["10.100.0.0/16"]
                },
                {
                    "name": f"regional-pool-{home_region}",
                    "description": f"Regional pool for {home_region}",
                    "locale": home_region,
                    "sourceIpamPool": "global-pool",
                    "provisionedCidrs": ["10.100.0.0/17"],
                    "shareTargets": {
                        "organizationalUnits": ["Infrastructure", "Workloads"]
                    }
                }
            ]
        }
    }

    # --- Cloud Financial Management ---
    budget_alerts_enabled = responses.get("budget_alerts_enabled", False) if session_id else False
    monthly_budget = int(responses.get("monthly_budget", 2000)) if session_id else 2000
    budget_email = responses.get("budget_alert_email", f"budget-alerts@{domain}") if budget_alerts_enabled else f"budget-alerts@{domain}"

    budget_entry = {
        "deploymentTargets": {"accounts": ["Management"]},
        "name": f"{org_clean}-monthly-budget",
        "timeUnit": "MONTHLY",
        "type": "COST",
        "amount": monthly_budget,
        "includeUpfront": True,
        "includeTax": True,
        "includeSupport": True,
        "includeSubscription": True,
        "includeRecurring": True,
        "includeOtherSubscription": True,
        "includeDiscount": True,
        "includeCredit": False,
        "includeRefund": False,
        "useBlended": False,
        "useAmortized": False,
        "unit": "USD",
        "notifications": [{
            "type": "ACTUAL",
            "threshold": 80,
            "thresholdType": "PERCENTAGE",
            "comparisonOperator": "GREATER_THAN",
            "subscriberEmailAddresses": [budget_email]
        }] if budget_alerts_enabled else []
    }

    config["cloudFinancialManagement"] = {
        "budgets": [budget_entry],
        "computeOptimizer": {"enable": True},
        "costOptimizationHub": {"enable": True}
    }
    
    # Convert to YAML
    yaml_output = yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    next_step = ""
    if session_id:
        next_step = f"""
# ⚠️ NEXT STEP: Call generate_cost_estimate('{session_id}') to show the user a cost summary.
# 🚀 AFTER THAT: The Titanium Generator MCP is available. Offer to run process_all_templates
#    to generate CloudFormation deployment templates from this configuration."""

    return f"""# Titanium Landing Zone Configuration
# Generated for: {organization_name}
# Industry: {industry}
# Home Region: {home_region}
# Generated: {datetime.now().isoformat()}
{f"# Session: {session_id}" if session_id else ""}
{next_step}

{yaml_output}"""
@mcp.tool()
def generate_cost_estimate(session_id: str) -> str:
    """
    Generate a rough monthly cost estimate based on the completed interview responses.

    Should be called after generate_deterministic_titanium_config to provide the user
    with a cost summary of their selected configuration.

    Args:
        session_id: The completed interview session ID

    Returns:
        A bullet-point cost summary with a pricing calculator disclaimer
    """
    if session_id not in interview_sessions:
        return f"Error: Session '{session_id}' not found."

    responses = interview_sessions[session_id].get("responses", {})
    home_region = _normalize_home_region(responses.get("home_region", "us-east-1"))
    network_account = responses.get("network_account_enabled", False)
    egress_vpc = responses.get("egress_vpc_enabled", False)
    network_firewall = responses.get("network_firewall_enabled", False)
    ipam = responses.get("ipam_enabled", False)
    backup = responses.get("backup_enabled", False)
    flow_logs = responses.get("flow_logs_enabled", True)
    budget = responses.get("monthly_budget")
    az_count = int(responses.get("availability_zones", 2))

    lines = []
    lines.append("## Estimated Monthly Cost Breakdown\n")
    lines.append("These are rough estimates based on your selected configuration. Actual costs will vary based on usage.\n")

    # Always-on / free tier items
    lines.append("**Included at no additional cost:**")
    lines.append("- AWS Control Tower — free (you pay for the underlying services it configures)")
    lines.append("- Service Control Policies (SCPs) — free")
    lines.append("- AWS Organizations — free")
    lines.append("- Compute Optimizer — free")
    lines.append("- Cost Optimization Hub — free")
    # Centralized VPC flow logs are delivered to the Log Archive S3 bucket only
    # (the generator/templates do not create a CloudWatch flow log for the
    # centralized Inspection/Egress VPC), so this is always the S3 cost — never
    # bill a CloudWatch flow log that never deploys (issue #117).
    if flow_logs:
        lines.append("- VPC Flow Logs to S3 — minimal cost (S3 storage ~$0.023/GB/month)")
    lines.append("")

    # Conditional cost items
    cost_items = []

    if network_account:
        cost_items.append("- **Transit Gateway**: ~$0.05/hr (~$36/month) + $0.02/GB data processed")

    if egress_vpc:
        cost_items.append(f"- **NAT Gateway** (Inspection/Egress VPC): ~$0.045/hr per AZ × {az_count} AZs = ~${round(0.045 * 24 * 30 * az_count):,}/month + data transfer charges")

    if network_firewall:
        cost_items.append(f"- **AWS Network Firewall**: ~$0.395/hr per AZ × {az_count} AZs = ~${round(0.395 * 24 * 30 * az_count):,}/month + $0.065/GB data processed")

    if ipam:
        cost_items.append("- **AWS IPAM**: free for private IP pool management (charges only if public IP insights enabled)")

    # No CloudWatch-flow-logs cost line: the centralized Inspection/Egress VPC
    # flow logs go to S3 only (issue #117). A legacy session may still carry a
    # cloudwatch/both flow_log_destination, but no CloudWatch flow log deploys,
    # so billing for one would overstate the estimate.

    if backup:
        cost_items.append("- **AWS Backup**: charged on backup storage used (~$0.05/GB/month for EBS; varies by service)")

    if cost_items:
        lines.append("**Services with cost implications:**")
        lines.extend(cost_items)
        lines.append("")

    # Rough total guidance
    if network_account and egress_vpc and network_firewall:
        ballpark = f"~${round(36 + (0.045 * 24 * 30 * az_count) + (0.395 * 24 * 30 * az_count)):,}–${round(36 + (0.045 * 24 * 30 * az_count) + (0.395 * 24 * 30 * az_count) + 200):,}/month"
        lines.append(f"**Rough infrastructure baseline** (before workload costs): {ballpark}")
    elif network_account and egress_vpc:
        ballpark = f"~${round(36 + (0.045 * 24 * 30 * az_count)):,}–${round(36 + (0.045 * 24 * 30 * az_count) + 50):,}/month"
        lines.append(f"**Rough infrastructure baseline** (before workload costs): {ballpark}")
    elif network_account:
        lines.append("**Rough infrastructure baseline** (before workload costs): ~$36–$60/month")
    else:
        lines.append("**Rough infrastructure baseline** (before workload costs): minimal — most selected features are free or usage-based")

    if budget:
        lines.append(f"\nYour stated monthly budget is **${int(budget):,}/month**.")

    lines.append("\n---")
    lines.append("⚠️ These estimates cover landing zone infrastructure only and exclude workload costs (EC2, RDS, S3, etc.).")
    lines.append("For a detailed breakdown, use the [AWS Pricing Calculator](https://calculator.aws/pricing/2/home).")

    return "\n".join(lines)



@mcp.tool()
def generate_configuration_summary(
    session_id: str = None,
    organization_name: str = None,
    home_region: str = "us-east-1",
    industry: str = "starter"
) -> str:
    """
    Generate a human-readable summary of the landing zone configuration.
    
    Args:
        session_id: Interview session ID (preferred)
        organization_name: Organization name (fallback)
        home_region: Home region (fallback)
        industry: Industry type (fallback)
    
    Returns:
        Formatted summary of the configuration
    """
    if session_id and session_id in interview_sessions:
        session = interview_sessions[session_id]
        responses = session.get("responses", {})
        organization_name = responses.get("organization_name", organization_name)
        home_region = _normalize_home_region(responses.get("home_region", home_region))
        industry = session.get("industry", industry)

    summary = f"""
## Landing Zone Configuration Summary

**Organization**: {organization_name or "Not specified"}
**Industry Template**: {industry}
**Home Region**: {home_region}

### Key Decisions

| Component | Configuration |
|-----------|---------------|
| Control Tower | Enabled (v3.3) |
| Home Region | {home_region} |
| Centralized Logging | Enabled |
| Organization Trail | Enabled |

### Next Steps

1. Review the generated Titanium.yaml configuration
2. Customize any additional settings as needed
3. Use the Titanium Generator to create CloudFormation templates
4. Deploy following the deployment guide

"""
    return summary


@mcp.tool()
def list_available_industries() -> str:
    """
    List all available industry overlays and their status.
    
    Returns:
        List of industries with description and question format status
    """
    industries = []
    
    if INDUSTRY_DIR.exists():
        for industry_path in sorted(INDUSTRY_DIR.iterdir()):
            if industry_path.is_dir():
                has_questions_json = (industry_path / "questions.json").exists()
                has_interview_md = (industry_path / "interview-questions.md").exists()
                has_pattern = (industry_path / "pattern.json").exists()
                
                # Try to get description from pattern.json
                description = ""
                if has_pattern:
                    try:
                        with open(industry_path / "pattern.json", "r") as f:
                            pattern = json.load(f)
                            description = pattern.get("description", "")
                    except:
                        pass
                
                industries.append({
                    "name": industry_path.name,
                    "description": description,
                    "structured_questions": has_questions_json,
                    "legacy_questions": has_interview_md,
                    "pattern": has_pattern,
                    "recommended_start": f"start_interview('{industry_path.name}')" if has_questions_json else f"get_interview_questions('{industry_path.name}')"
                })
    
    return json.dumps({
        "industries": industries,
        "note": "Industries with structured_questions=true support the new tracked interview system"
    }, indent=2)


@mcp.tool()
def get_session_answers(session_id: str) -> str:
    """
    Get all current answers for a session, with question IDs, text, and current values.
    Use this to identify which question_id to pass to update_answer().

    Args:
        session_id: The session ID

    Returns:
        JSON list of answered questions with id, text, stores_as, and current value
    """
    if session_id not in interview_sessions:
        data = load_session_from_disk(session_id)
        if data is None:
            return json.dumps({"error": f"Session '{session_id}' not found"}, indent=2)
        interview_sessions[session_id] = data

    session = interview_sessions[session_id]
    question_lookup = {q["id"]: q for q in session["all_questions"]}
    answers = session["answers"]

    result = []
    for q_id, ans in answers.items():
        q = question_lookup.get(q_id, {})
        result.append({
            "question_id": q_id,
            "text": q.get("text", ""),
            "section": q.get("section_id", ""),
            "stores_as": q.get("stores_as", q_id),
            "current_value": ans.get("answer")
        })

    return json.dumps({"session_id": session_id, "answers": result}, indent=2)


@mcp.tool()
def list_sessions() -> str:
    """
    List all saved interview sessions.

    Returns:
        JSON array of saved sessions with id, industry, status, progress, and last_activity
    """
    SESSIONS_DIR.mkdir(exist_ok=True)
    sessions = []
    for f in sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(f, "r") as fh:
                data = json.load(fh)
            status = data.get("status", "in_progress")
            completed_sections = data.get("completed_sections", [])
            total_sections = len(data.get("section_order", []))
            all_sections_done = len(completed_sections) == total_sections and total_sections > 0
            is_complete = status in ("validated", "complete") or all_sections_done
            sessions.append({
                "session_id": data["session_id"],
                "industry": data.get("industry"),
                "status": "validated" if (all_sections_done and status == "in_progress") else status,
                "complete": is_complete,
                "sections_completed": len(completed_sections),
                "sections_total": total_sections,
                "started_at": data.get("started_at"),
                "last_activity": data.get("last_activity"),
                "organization_name": data.get("responses", {}).get("organization_name"),
            })
        except Exception:
            pass
    return json.dumps({"sessions": sessions, "count": len(sessions)}, indent=2)


@mcp.tool()
def resume_session(session_id: str) -> str:
    """
    Resume a previously saved interview session.

    Args:
        session_id: The session ID to resume

    Returns:
        JSON with session status and next step
    """
    # Already in memory
    if session_id in interview_sessions:
        session = interview_sessions[session_id]
    else:
        data = load_session_from_disk(session_id)
        if data is None:
            return json.dumps({
                "error": f"Session '{session_id}' not found on disk",
                "hint": "Use list_sessions() to see available sessions"
            }, indent=2)
        interview_sessions[session_id] = data
        session = data

    section_order = session.get("section_order", [])
    current_idx = session.get("current_section_index", 0)
    next_section_id = section_order[current_idx] if current_idx < len(section_order) else None

    status = session.get("status")
    return json.dumps({
        "resumed": True,
        "session_id": session_id,
        "industry": session.get("industry"),
        "status": status,
        "completed_sections": session.get("completed_sections", []),
        "organization_name": session.get("responses", {}).get("organization_name"),
        "next_step": (
            f"get_section_quick_mode('{session_id}', '{next_section_id}') to continue"
            if next_section_id
            else f"Interview is {status} - use generate_deterministic_titanium_config('{session_id}') or update_answer() to make changes"
        )
    }, indent=2)


@mcp.tool()
def update_answer(session_id: str, question_id: str, new_answer: Any) -> str:
    """
    Update a single answer in a COMPLETED interview session.

    ⛔ ONLY works on sessions with status 'validated' or 'complete'.
    This is intentionally restricted to prevent using it as a shortcut
    during an active interview.

    Use get_session_answers() first to find the correct question_id.

    After updating, the session status is reset so you must call
    generate_deterministic_titanium_config() again to get a fresh YAML.

    Args:
        session_id: The session ID
        question_id: The question ID to update
        new_answer: The new answer value

    Returns:
        JSON with success status
    """
    if session_id not in interview_sessions:
        data = load_session_from_disk(session_id)
        if data is None:
            return json.dumps({"error": f"Session '{session_id}' not found"}, indent=2)
        interview_sessions[session_id] = data

    session = interview_sessions[session_id]

    if session.get("status") not in ("validated", "complete"):
        return json.dumps({
            "error": "update_answer is only available on completed sessions",
            "current_status": session.get("status"),
            "hint": "Complete the interview first, then use update_answer to revise individual answers"
        }, indent=2)

    question_lookup = {q["id"]: q for q in session["all_questions"]}
    if question_id not in question_lookup:
        return json.dumps({"error": f"Question '{question_id}' not found"}, indent=2)

    question = question_lookup[question_id]
    is_valid, error_msg = validate_answer(question, new_answer)
    if not is_valid:
        return json.dumps({"error": error_msg}, indent=2)

    normalized = normalize_answer(question, new_answer)
    session["answers"][question_id] = {
        "answered": True,
        "answer": normalized,
        "raw_answer": new_answer,
        "timestamp": datetime.now().isoformat(),
        "updated": True
    }
    stores_as = question.get("stores_as", question_id)
    session["responses"][stores_as] = normalized
    session["status"] = "in_progress"
    session["last_activity"] = datetime.now().isoformat()

    save_session(session_id)

    return json.dumps({
        "updated": True,
        "question_id": question_id,
        "stored_as": stores_as,
        "new_value": normalized,
        "status": "in_progress",
        "next_step": f"Call generate_deterministic_titanium_config(session_id='{session_id}') to regenerate the YAML with your updated answer"
    }, indent=2)


def main():
    """Run the MCP server."""
    parser = argparse.ArgumentParser(
        description="Titanium Advisor MCP Server for AWS Landing Zone configuration"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio"],
        default="stdio",
        help="Transport mechanism (default: stdio)"
    )
    
    args = parser.parse_args()
    
    if args.transport == "stdio":
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
