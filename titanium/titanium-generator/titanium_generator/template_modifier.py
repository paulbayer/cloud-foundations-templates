"""
Simple CloudFormation template modifier.

This module provides direct string-based template modification without complex parsing,
focusing on updating parameter default values using regex patterns.

Supports the Titanium Generator parameter naming convention:
- 't' prefix: Parameters automatically set by Titanium Generator
- 'u' prefix: Parameters that must be provided by users at runtime
"""

import re
from typing import Dict, Any, List, Tuple


class TemplateModifier:
    """
    Simple template modifier that updates CloudFormation parameter defaults using regex.

    Supports the Titanium Generator parameter naming convention:
    - 't' prefix: parameters set by Titanium Generator
    - 'u' prefix: parameters supplied by the user at deployment time
    A parameter's role is determined by its first character; the previous
    per-suffix regex allowlists were brittle (every new parameter shape had to be
    added) and only ever produced non-fatal, recorded warnings.
    """

    def __init__(self):
        """Initialize the template modifier."""
        self.modifications_made = []

    def update_parameter_defaults(self, template_yaml: str, parameter_updates: Dict[str, str]) -> Tuple[str, List[str]]:
        """
        Update parameter default values in CloudFormation template YAML.

        Args:
            template_yaml: Original template YAML content
            parameter_updates: Dictionary of parameter_name -> new_default_value

        Returns:
            Tuple of (modified_yaml, list_of_modifications_made)
        """
        if not parameter_updates:
            return template_yaml, []

        # Split once and mutate the shared line list per parameter, rather than
        # splitting+rejoining the whole template for every parameter.
        lines = template_yaml.split("\n")
        modifications_made = []

        for param_name, new_default in parameter_updates.items():
            was_modified = self._apply_parameter_default(lines, param_name, new_default)

            if was_modified:
                modifications_made.append(f"Updated parameter '{param_name}' default to '{new_default}'")
            else:
                modifications_made.append(f"Info: Parameter '{param_name}' not found in template (expected — not all parameters apply to every template)")

        self.modifications_made = modifications_made
        return "\n".join(lines), modifications_made

    def inject_marker_region(
        self, template_yaml: str, marker_name: str, block_lines: List[str]
    ) -> Tuple[str, List[str]]:
        """
        Replace the content between TITANIUM:BEGIN/END <marker_name> with block_lines.

        Marker regions let the generator inject generated resources into a template
        without re-serializing it. A full YAML round-trip would drop every comment,
        including the design rationale the CloudFormation templates carry, so this is
        line-level text surgery: everything outside the marked region stays
        byte-identical.

        The marker comments themselves are preserved, so a region remains injectable
        on a subsequent run and generation is idempotent. Templates without the marker
        are returned unchanged, which is what lets one processor run against every
        template in its section.

        Args:
            template_yaml: Original template YAML content
            marker_name: Marker identifier, e.g. 'generated-organizational-units'
            block_lines: Lines to place inside the region (without trailing newlines)

        Returns:
            Tuple of (modified_yaml, list_of_modifications_made)
        """
        escaped = re.escape(marker_name)
        # Anchored at line start so prose that merely mentions the markers (such as the
        # explanatory comment in a template's Metadata block) is never matched.
        begin_re = re.compile(rf"^\s*#\s*TITANIUM:BEGIN\s+{escaped}\s*$")
        end_re = re.compile(rf"^\s*#\s*TITANIUM:END\s+{escaped}\s*$")

        lines = template_yaml.split("\n")
        begin_idx = None
        end_idx = None
        for idx, line in enumerate(lines):
            if begin_idx is None:
                if begin_re.match(line):
                    begin_idx = idx
            elif end_re.match(line):
                end_idx = idx
                break

        if begin_idx is None or end_idx is None:
            return template_yaml, []

        replaced_count = end_idx - begin_idx - 1
        new_lines = lines[: begin_idx + 1] + list(block_lines) + lines[end_idx:]

        modification = (
            f"Injected {len(block_lines)} line(s) into marker region "
            f"'{marker_name}' (replaced {replaced_count})"
        )
        self.modifications_made = self.modifications_made + [modification]
        return "\n".join(new_lines), [modification]

    def _apply_parameter_default(
        self, lines: List[str], param_name: str, new_default: str
    ) -> bool:
        """
        Update a single parameter's default value in place within ``lines``.

        Finds the named parameter's block and, if it has a ``Default:`` line,
        rewrites it; if it has none, inserts one so the generator-supplied value
        (sourced from the Titanium config) actually reaches the template. Without
        the insert path, a parameter declared with no ``Default:`` — e.g. the
        Control Tower retention periods (#79) — would silently keep no default and
        fail at deploy time with "Parameters must have values", since the guide
        does not pass t* parameters.

        The list is mutated directly so the caller can apply many updates to one
        line list without repeatedly splitting and rejoining the template.

        Args:
            lines: Template split into lines (mutated in place)
            param_name: Name of parameter to update
            new_default: New default value to set

        Returns:
            True if the parameter block was found (regardless of whether a Default
            was rewritten or inserted).
        """
        found_param = False
        idx = 0
        total = len(lines)

        while idx < total:
            line = lines[idx]
            stripped = line.strip()

            # A parameter name can appear more than once (e.g. a Metadata
            # ParameterLabels entry as well as the real Parameters definition), so
            # scan each occurrence and act only on the block that declares a Type:
            # — that is the actual parameter definition.
            if stripped.startswith(param_name + ":") and ":" in line:
                found_param = True
                param_indent = len(line) - len(line.lstrip())
                child_indent = None
                last_child_idx = idx
                default_idx = None
                has_type = False

                scan = idx + 1
                while scan < total:
                    block_line = lines[scan]
                    block_stripped = block_line.strip()
                    if block_stripped == "":
                        scan += 1
                        continue
                    current_indent = len(block_line) - len(block_line.lstrip())
                    if current_indent <= param_indent:
                        break  # left the block
                    if child_indent is None:
                        child_indent = current_indent
                    last_child_idx = scan
                    if block_stripped.startswith("Type:"):
                        has_type = True
                    if block_stripped.startswith("Default:"):
                        default_idx = scan
                    scan += 1

                if has_type:
                    formatted = self._format_parameter_value(new_default)
                    if default_idx is not None:
                        prefix = lines[default_idx]
                        indent = prefix[: len(prefix) - len(prefix.lstrip())]
                        lines[default_idx] = f"{indent}Default: {formatted}"
                    else:
                        # No Default line: insert one so the generator-supplied
                        # value (from the Titanium config) reaches the template and
                        # the parameter is deployable (#79).
                        indent = " " * (child_indent if child_indent is not None else param_indent + 2)
                        lines.insert(last_child_idx + 1, f"{indent}Default: {formatted}")
                    return found_param

                # Not the real definition (no Type:); keep scanning.
                idx = scan
                continue

            idx += 1

        return found_param

    def _format_parameter_value(self, value: str) -> str:
        """
        Format a parameter value for YAML output.

        Args:
            value: Raw parameter value

        Returns:
            Formatted value (quoted if necessary)
        """
        # Always quote string values to be safe
        if isinstance(value, str):
            # If value contains special characters or looks like it needs quotes
            if any(char in value for char in [" ", ":", "-", "!", "@", "#", "%", "^", "&", "*"]):
                return f'"{value}"'
            # Boolean-like defaults target Type: String parameters with
            # AllowedValues ["true","false"]; an unquoted YAML boolean parses as a
            # bool and would not match the allowed string values (cfn-lint E2015),
            # so quote them.
            elif value.lower() in ["true", "false"]:
                return f'"{value}"'
            # Numeric defaults (e.g. retention days) are Type: Number and must
            # stay unquoted so they remain numbers.
            elif value.isdigit():
                return value
            else:
                return f'"{value}"'

        return str(value)

    def validate_parameter_naming(self, parameters: Dict[str, Any]) -> List[str]:
        """
        Validate that all parameters follow the t/u naming convention.

        Args:
            parameters: Dictionary of parameter names and their configurations

        Returns:
            List of validation errors (empty if all parameters are valid)
        """
        errors = []

        for param_name in parameters.keys():
            if not param_name.startswith(("t", "u")):
                errors.append(f"Parameter '{param_name}' does not follow t/u naming convention")
            elif len(param_name) < 2:
                errors.append(f"Parameter '{param_name}' is too short for t/u convention")
            elif param_name[1].islower():
                errors.append(f"Parameter '{param_name}' should have uppercase second character")

        return errors

    def classify_parameter(self, param_name: str) -> str:
        """
        Classify a parameter as Titanium-set or User-provided by its first character.

        Args:
            param_name: Name of the parameter to classify

        Returns:
            'titanium' if the name is 't'-prefixed (set by Titanium Generator),
            'user' if 'u'-prefixed (supplied by the user),
            'unknown' otherwise
        """
        if param_name.startswith("t"):
            return "titanium"
        if param_name.startswith("u"):
            return "user"
        return "unknown"

    def validate_template_parameters(self, template_yaml: str) -> Tuple[bool, List[str], Dict[str, str]]:
        """
        Validate all parameters in a CloudFormation template for naming convention compliance.

        Args:
            template_yaml: CloudFormation template YAML content

        Returns:
            Tuple of (is_valid, list_of_errors, parameter_classifications)
        """
        errors = []
        classifications = {}

        # Extract parameters from template
        parameters = self._extract_parameters_with_config(template_yaml)

        if not parameters:
            return True, [], {}

        # Validate naming convention
        naming_errors = self.validate_parameter_naming(parameters)
        errors.extend(naming_errors)

        # Classify parameters
        for param_name in parameters.keys():
            classification = self.classify_parameter(param_name)
            classifications[param_name] = classification

            if classification == "unknown":
                errors.append(f"Parameter '{param_name}' could not be classified as Titanium or User parameter")

        return len(errors) == 0, errors, classifications

    def _extract_parameters_with_config(self, template_yaml: str) -> Dict[str, Dict[str, Any]]:
        """
        Extract parameters with their full configuration from CloudFormation template.

        Args:
            template_yaml: CloudFormation template YAML content

        Returns:
            Dictionary of parameter names to their configuration
        """
        parameters = {}

        # Find Parameters section
        lines = template_yaml.split("\n")
        in_parameters_section = False
        current_param = None
        current_param_config = {}

        for line in lines:
            stripped = line.strip()

            # Check if we're entering Parameters section
            if stripped == "Parameters:":
                in_parameters_section = True
                continue

            # Check if we're leaving Parameters section
            if in_parameters_section and line and not line.startswith(" "):
                in_parameters_section = False
                # Save last parameter if exists
                if current_param:
                    parameters[current_param] = current_param_config
                break

            # Check for parameter name (exactly 2 spaces, not a comment)
            if (
                in_parameters_section
                and line.startswith("  ")
                and not line.startswith("   ")
                and ":" in line
                and not stripped.startswith("#")
            ):
                # Save previous parameter if exists
                if current_param:
                    parameters[current_param] = current_param_config

                # Start new parameter
                param_line = line.strip()
                if param_line.endswith(":"):
                    current_param = param_line[:-1]
                    current_param_config = {}
                else:
                    # Parameter with inline value
                    parts = param_line.split(":", 1)
                    current_param = parts[0].strip()
                    current_param_config = {"inline_value": parts[1].strip()}

            # Check for parameter property (4+ spaces)
            elif in_parameters_section and current_param and line.startswith("    "):
                # Parameter property
                prop_line = line.strip()
                if ":" in prop_line:
                    key, value = prop_line.split(":", 1)
                    current_param_config[key.strip()] = value.strip()

        # Save last parameter if we ended in parameters section
        if current_param and in_parameters_section:
            parameters[current_param] = current_param_config

        return parameters

    def get_modifications_made(self) -> List[str]:
        """
        Get list of modifications made in the last operation.

        Returns:
            List of modification descriptions
        """
        return self.modifications_made.copy()
