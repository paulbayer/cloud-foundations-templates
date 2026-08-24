# Titanium Template Modifier

A Python tool that reads Titanium.yaml configuration files and modifies CloudFormation template parameters to enable selective deployment of landing zone resources. Operates in dual mode: standalone CLI and MCP server for AI agent integration.

## Project Structure

```
titanium-generator/
├── main.py                        # CLI entry point (Click-based)
├── mcp_server.py                  # MCP server for AI agent integration
├── setup.py                       # Package configuration
├── setup.sh                       # Virtual environment setup script
├── requirements.txt               # Python dependencies
├── policy-examples/               # Example AWS Organization policies
│   ├── backup-policies/           # Backup policy JSON examples
│   └── tagging-policies/          # Tagging policy JSON examples
├── titanium_generator/            # Main package
│   ├── __init__.py
│   ├── config_parser.py           # Titanium.yaml parser and validator
│   ├── template_modifier.py       # CloudFormation parameter injection engine
│   ├── template_analyzer.py       # Template analysis and comparison
│   ├── base_processor.py          # SimpleProcessor base class
│   ├── processor_registry.py      # Processor registration and lookup
│   ├── automation_registry.py     # Section automation status tracking
│   ├── config/
│   │   └── automation_registry.yaml  # Automation status definitions
│   ├── processors/                # Section-specific processors
│   │   ├── organization_processor.py  # SCPs, OUs, policies
│   │   ├── security_processor.py      # GuardDuty, SecurityHub, Config
│   │   ├── network_processor.py       # VPCs, TGW, IPAM, DNS
│   │   ├── bootstrap_processor.py     # Config roles, StackSets integration
│   │   ├── identity_processor.py      # IAM, SSO, password policies
│   │   └── controltower_processor.py  # Control Tower landing zone
│   └── mcp_tools/                 # MCP tool implementations
│       ├── parse_titanium.py      # Parse and validate Titanium.yaml
│       ├── modify_template.py     # Modify a single template
│       ├── process_templates.py   # Batch process all templates
│       ├── llm_agent_guide.py     # Deployment guide generator for AI agents
│       └── templates/             # CloudFormation templates by section
│           ├── bootstrap/
│           ├── controltower/
│           ├── finance/
│           ├── identity/
│           ├── network/
│           ├── organization/
│           └── security/
└── tests/                         # Test suite
    ├── test_data/                 # Test fixtures (YAML samples)
    ├── test_config_parser.py
    ├── test_template_modifier.py
    ├── test_organization_processor.py
    ├── test_network_processor.py
    ├── test_network_error_handling.py
    ├── test_control_tower_detection.py
    ├── test_template_decision.py
    ├── test_template_naming_detection.py
    ├── test_tgw_template_filtering.py
    ├── test_parameter_resolution.py
    ├── test_target_detection.py
    ├── test_stack_commands.py
    ├── test_stackset_commands.py
    ├── test_mcp_template_discovery.py
    ├── test_ipam_pool_id_integration.py
    ├── test_titanium_yaml_with_pool_ids.py
    ├── test_real_titanium_yaml.py
    ├── test_backup_tagging_policies_integration.py
    ├── test_template_generation_integration.py
    ├── test_integration.py
    ├── run_all_integration_tests.py
    └── run_backup_tagging_integration_tests.py
```

## Features

- **CLI Interface**: Click-based CLI with `process`, `validate`, and `info` commands
- **MCP Server**: AI agent integration via Model Context Protocol with tool registry
- **Section Processors**: Dedicated processors for organization, security, network, bootstrap, identity, finance, and Control Tower sections
- **Template Analysis**: CloudFormation template parameter analysis and comparison with Titanium config
- **Automation Registry**: Tracks which sections are fully automated vs. require manual steps
- **LLM Agent Guide**: Generates structured deployment guides for AI agents with step-by-step instructions
- **Parameter Naming Convention**: Validates `t` (titanium-set) and `u` (user-provided) parameter prefixes
- **Template Selection**: Selects appropriate templates based on configuration (e.g., IPAM vs non-IPAM network templates)
- **Policy Examples**: Bundled backup and tagging policy JSON examples

## Installation

```bash
# Run the setup script
./setup.sh

# Or manually:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Usage

### CLI

```bash
# Process all templates
python main.py process --titanium-config ../Titanium.yaml --template-dir ./templates --output-dir ./output

# Process specific sections
python main.py process --titanium-config ../Titanium.yaml --template-dir ./templates --output-dir ./output --sections organization security

# Validate configuration
python main.py validate --titanium-config ../Titanium.yaml

# Show tool info
python main.py info
```

### MCP Server

```bash
# Start the MCP server
python mcp_server.py

# Test with a Titanium.yaml file
python mcp_server.py test ../Titanium.yaml
```

### Python API

```python
from titanium_generator import TitaniumConfigParser, TemplateModifier, ProcessorRegistry

# Parse configuration
parser = TitaniumConfigParser()
config = parser.parse_file("Titanium.yaml")
sections = parser.get_available_sections(config)

# Get a processor for a section
processor = ProcessorRegistry.get_processor("organization")
processor.set_full_config(config)

# Process a template
section_data = parser.get_section_data(config, "organization")
modified_template = processor.process(template_content, section_data)
```

## Architecture

### Template Modification Strategy

The tool uses two approaches depending on the configuration:

1. **Parameter Modification**: Updates existing parameter defaults in templates when the template structure matches the configuration
2. **Template Selection**: Selects entirely different templates when configuration values require different implementations (e.g., IPAM-enabled vs standard VPC templates)

### Section Processing

Each Titanium.yaml section has a dedicated processor inheriting from `SimpleProcessor` that:
- Extracts configuration items from the section
- Generates parameter updates (`t`-prefixed parameters derived from config)
- Identifies `u`-prefixed parameters that require user input at deployment time
- Modifies templates via the `TemplateModifier` engine

### Registered Processors

| Section | Processor | Handles |
|---------|-----------|---------|
| `organization` | `SimpleOrganizationProcessor` | SCPs, OUs, backup/tagging policies |
| `security` | `SimpleSecurityProcessor` | GuardDuty, SecurityHub, Config, Macie |
| `network` | `NetworkProcessor` | VPCs, TGW, IPAM, DNS, firewall |
| `bootstrap` | `BootstrapProcessor` | Config roles, StackSets integration |
| `identity` | `IdentityProcessor` | IAM password policy, SSO |
| `control_tower` | `ControlTowerProcessor` | Landing zone, logging, region denial |
| `cost_management` | `FinanceProcessor` | Budgets, Compute Optimizer, Cost Optimization Hub |

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=titanium_generator --cov-report=html

# Run specific test file
python -m pytest tests/test_network_processor.py -v

# Run integration tests
python tests/run_all_integration_tests.py
```

## Development

### Code Style
- PEP 8 compliant
- Type hints throughout
- Comprehensive docstrings

### Adding New Processors
1. Create a new file in `titanium_generator/processors/`
2. Inherit from `SimpleProcessor`
3. Use the `@register_processor('section_name')` decorator
4. Implement `extract_items()` and `generate_parameter_updates()`
5. Add tests in `tests/`

## License

This project is part of the AWS Landing Zone Configurer toolkit.
