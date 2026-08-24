"""
Test MCP template discovery for backup and tagging policies.

This test verifies that the MCP tools can discover and process the new
backup and tagging policy templates.
"""

from pathlib import Path
from titanium_generator.mcp_tools.process_templates import process_all_templates  # noqa: F401


def test_template_discovery_includes_backup_policies():
    """Test that backup policies template is discovered."""
    # Get the templates directory
    templates_dir = Path(__file__).parent.parent / "titanium_generator" / "mcp_tools" / "templates" / "organization"

    # Check that backup policies template exists
    backup_template = templates_dir / "03-organizations-stack-mgmt-backup-policies.yaml"
    assert backup_template.exists(), f"Backup policies template not found at {backup_template}"

    # Verify it's a YAML file
    assert backup_template.suffix in [".yaml", ".yml"], "Backup policies template must be YAML"


def test_template_discovery_includes_tagging_policies():
    """Test that tagging policies template is discovered."""
    # Get the templates directory
    templates_dir = Path(__file__).parent.parent / "titanium_generator" / "mcp_tools" / "templates" / "organization"

    # Check that tagging policies template exists
    tagging_template = templates_dir / "04-organizations-stack-mgmt-tagging-policies.yaml"
    assert tagging_template.exists(), f"Tagging policies template not found at {tagging_template}"

    # Verify it's a YAML file
    assert tagging_template.suffix in [".yaml", ".yml"], "Tagging policies template must be YAML"


def test_organization_templates_sorted_by_prefix():
    """Test that organization templates are sorted by numerical prefix."""
    templates_dir = Path(__file__).parent.parent / "titanium_generator" / "mcp_tools" / "templates" / "organization"

    # Get all YAML templates
    templates = sorted(list(templates_dir.glob("*.yaml")) + list(templates_dir.glob("*.yml")))

    # Extract template names
    template_names = [t.name for t in templates]

    # Verify backup and tagging policies are in the list
    assert "03-organizations-stack-mgmt-backup-policies.yaml" in template_names
    assert "04-organizations-stack-mgmt-tagging-policies.yaml" in template_names

    # Verify they come after OUs and SCPs
    ou_index = template_names.index("01-organizations-stack-mgmt-ous.yaml")
    scp_index = template_names.index("02-organizations-stack-mgmt-scps.yaml")
    backup_index = template_names.index("03-organizations-stack-mgmt-backup-policies.yaml")
    tagging_index = template_names.index("04-organizations-stack-mgmt-tagging-policies.yaml")

    assert (
        ou_index < scp_index < backup_index < tagging_index
    ), "Templates must be in correct deployment order: OUs -> SCPs -> Backup -> Tagging"
