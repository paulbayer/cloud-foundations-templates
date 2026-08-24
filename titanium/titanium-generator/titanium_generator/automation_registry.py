"""
Automation Registry for Titanium Generator.

Loads and queries the automation registry YAML file that serves as the
single source of truth for which sections/subsections are fully automated,
partially automated, or manual.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import yaml

logger = logging.getLogger(__name__)

# Valid status values
VALID_SECTION_STATUSES = {"fully_automated", "partially_automated", "manual"}
VALID_SUBSECTION_STATUSES = {"automated", "manual"}

# Default registry path relative to this file's directory
_DEFAULT_REGISTRY_PATH = os.path.join(
    os.path.dirname(__file__), "config", "automation_registry.yaml"
)


class AutomationRegistryError(Exception):
    """Raised when the automation registry cannot be loaded or is invalid."""


@dataclass
class SubsectionAutomationStatus:
    """Automation status for a single subsection within a section."""

    name: str
    status: str
    description: str


@dataclass
class ManualStepTemplate:
    """Template for a manual deployment step defined in the registry."""

    title: str
    description: str
    why_manual: str
    console_steps: List[str] = field(default_factory=list)
    cli_commands: List[str] = field(default_factory=list)
    config_references: List[str] = field(default_factory=list)


@dataclass
class SectionAutomationStatus:
    """Automation status for a top-level configuration section."""

    section_name: str
    status: str
    automated_percentage: int
    subsections: List[SubsectionAutomationStatus] = field(default_factory=list)
    manual_step_templates: List[ManualStepTemplate] = field(default_factory=list)


class AutomationRegistry:
    """Loads and queries the automation registry YAML file.

    The registry is the single source of truth for automation coverage.
    It maps each configuration section to its automation status and
    provides manual step templates for sections that are not fully
    automated.
    """

    def __init__(self, registry_path: Optional[str] = None):
        """Load registry from the given path or the default location.

        Args:
            registry_path: Path to the registry YAML file. If ``None``,
                uses ``titanium_generator/config/automation_registry.yaml``.

        Raises:
            AutomationRegistryError: If the file is missing, contains
                malformed YAML, or is missing required fields.
        """
        self._path = registry_path or _DEFAULT_REGISTRY_PATH
        self._sections: Dict[str, SectionAutomationStatus] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------

    def get_section_status(self, section_name: str) -> SectionAutomationStatus:
        """Return automation status for a top-level section.

        Args:
            section_name: Registry section key (e.g. ``"bootstrap"``).

        Raises:
            KeyError: If the section is not in the registry.
        """
        if section_name not in self._sections:
            raise KeyError(
                f"Section '{section_name}' not found in automation registry"
            )
        return self._sections[section_name]

    def get_subsection_status(
        self, section_name: str, subsection_name: str
    ) -> SubsectionAutomationStatus:
        """Return automation status for a specific subsection.

        Args:
            section_name: Registry section key.
            subsection_name: Subsection key within the section.

        Raises:
            KeyError: If the section or subsection is not found.
        """
        section = self.get_section_status(section_name)
        for sub in section.subsections:
            if sub.name == subsection_name:
                return sub
        raise KeyError(
            f"Subsection '{subsection_name}' not found in section '{section_name}'"
        )

    def get_manual_sections(self) -> List[str]:
        """Return names of sections that are *not* fully automated."""
        return [
            name
            for name, status in self._sections.items()
            if status.status != "fully_automated"
        ]

    def get_manual_step_template(
        self, section_name: str
    ) -> Optional[List[ManualStepTemplate]]:
        """Return manual step templates for a section, if any.

        Args:
            section_name: Registry section key.

        Returns:
            List of ``ManualStepTemplate`` objects, or ``None`` if the
            section has no manual step templates defined.

        Raises:
            KeyError: If the section is not in the registry.
        """
        section = self.get_section_status(section_name)
        return section.manual_step_templates or None

    def is_fully_automated(self, section_name: str) -> bool:
        """Check whether a section is fully automated.

        Args:
            section_name: Registry section key.

        Raises:
            KeyError: If the section is not in the registry.
        """
        return self.get_section_status(section_name).status == "fully_automated"

    @property
    def sections(self) -> Dict[str, SectionAutomationStatus]:
        """All loaded section statuses keyed by section name."""
        return dict(self._sections)

    # ------------------------------------------------------------------
    # Internal loading / validation
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load and validate the registry YAML file."""
        raw = self._read_file()
        data = self._parse_yaml(raw)
        self._validate_and_build(data)

    def _read_file(self) -> str:
        """Read the raw YAML content from disk."""
        if not os.path.isfile(self._path):
            raise AutomationRegistryError(
                f"Automation registry not found at {self._path}. "
                "Cannot determine automation coverage."
            )
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                return fh.read()
        except OSError as exc:
            raise AutomationRegistryError(
                f"Failed to read automation registry at {self._path}: {exc}"
            ) from exc

    def _parse_yaml(self, raw: str) -> Dict[str, Any]:
        """Parse raw YAML content into a dict."""
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise AutomationRegistryError(
                f"Automation registry at {self._path} contains invalid YAML: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise AutomationRegistryError(
                f"Automation registry at {self._path} must be a YAML mapping, "
                f"got {type(data).__name__}"
            )
        return data

    def _validate_and_build(self, data: Dict[str, Any]) -> None:
        """Validate top-level structure and build section objects."""
        if "sections" not in data:
            raise AutomationRegistryError(
                "Automation registry is missing required field 'sections'"
            )

        sections_data = data["sections"]
        if not isinstance(sections_data, dict):
            raise AutomationRegistryError(
                "Automation registry 'sections' must be a mapping"
            )

        for section_name, section_data in sections_data.items():
            try:
                section_status = self._build_section(section_name, section_data)
                self._sections[section_name] = section_status
            except AutomationRegistryError:
                raise
            except Exception as exc:
                logger.warning(
                    "Skipping unknown or invalid section '%s': %s",
                    section_name,
                    exc,
                )

    def _build_section(
        self, section_name: str, data: Any
    ) -> SectionAutomationStatus:
        """Build a ``SectionAutomationStatus`` from raw section data."""
        if not isinstance(data, dict):
            raise AutomationRegistryError(
                f"Automation registry is missing required field 'status' "
                f"for section '{section_name}'"
            )

        # Required fields
        for req_field in ("status", "automated_percentage", "subsections"):
            if req_field not in data:
                raise AutomationRegistryError(
                    f"Automation registry is missing required field "
                    f"'{req_field}' for section '{section_name}'"
                )

        status = data["status"]
        if status not in VALID_SECTION_STATUSES:
            raise AutomationRegistryError(
                f"Section '{section_name}' has invalid status '{status}'. "
                f"Must be one of {VALID_SECTION_STATUSES}"
            )

        automated_percentage = data["automated_percentage"]
        if not isinstance(automated_percentage, int) or not (
            0 <= automated_percentage <= 100
        ):
            raise AutomationRegistryError(
                f"Section '{section_name}' has invalid automated_percentage "
                f"'{automated_percentage}'. Must be an integer 0-100."
            )

        # Subsections
        subsections = self._build_subsections(section_name, data["subsections"])

        # Optional manual step templates
        templates: List[ManualStepTemplate] = []
        if "manual_step_templates" in data:
            templates = self._build_manual_step_templates(
                section_name, data["manual_step_templates"]
            )

        return SectionAutomationStatus(
            section_name=section_name,
            status=status,
            automated_percentage=automated_percentage,
            subsections=subsections,
            manual_step_templates=templates,
        )

    def _build_subsections(
        self, section_name: str, data: Any
    ) -> List[SubsectionAutomationStatus]:
        """Build subsection status objects from raw data."""
        if not isinstance(data, dict):
            raise AutomationRegistryError(
                f"Subsections for section '{section_name}' must be a mapping"
            )

        result: List[SubsectionAutomationStatus] = []
        for sub_name, sub_data in data.items():
            if not isinstance(sub_data, dict):
                logger.warning(
                    "Skipping invalid subsection '%s' in section '%s'",
                    sub_name,
                    section_name,
                )
                continue

            sub_status = sub_data.get("status")
            if sub_status not in VALID_SUBSECTION_STATUSES:
                raise AutomationRegistryError(
                    f"Subsection '{sub_name}' in section '{section_name}' "
                    f"has invalid status '{sub_status}'. "
                    f"Must be one of {VALID_SUBSECTION_STATUSES}"
                )

            result.append(
                SubsectionAutomationStatus(
                    name=sub_name,
                    status=sub_status,
                    description=sub_data.get("description", ""),
                )
            )
        return result

    def _build_manual_step_templates(
        self, section_name: str, data: Any
    ) -> List[ManualStepTemplate]:
        """Build manual step template objects from raw data."""
        if not isinstance(data, list):
            raise AutomationRegistryError(
                f"manual_step_templates for section '{section_name}' must be a list"
            )

        result: List[ManualStepTemplate] = []
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                logger.warning(
                    "Skipping invalid manual_step_template at index %d "
                    "in section '%s'",
                    idx,
                    section_name,
                )
                continue

            for req_field in ("title", "description", "why_manual"):
                if req_field not in item:
                    raise AutomationRegistryError(
                        f"Manual step template at index {idx} in section "
                        f"'{section_name}' is missing required field '{req_field}'"
                    )

            result.append(
                ManualStepTemplate(
                    title=item["title"],
                    description=item["description"],
                    why_manual=item["why_manual"],
                    console_steps=item.get("console_steps", []),
                    cli_commands=item.get("cli_commands", []),
                    config_references=item.get("config_references", []),
                )
            )
        return result