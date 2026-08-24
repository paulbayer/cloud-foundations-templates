"""
Modify CloudFormation template MCP tool.

This tool modifies a single CloudFormation template based on Titanium configuration
using the simplified architecture.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from ..config_parser import TitaniumConfigParser
from ..processor_registry import ProcessorRegistry
from ..template_modifier import TemplateModifier


def modify_template(titanium_path: str, template_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Modify a single CloudFormation template based on Titanium configuration.
    
    Args:
        titanium_path: Path to the Titanium.yaml file
        template_path: Path to the CloudFormation template
        output_path: Optional output path (defaults to template_path with .modified suffix)
        
    Returns:
        Dictionary with modification results and metadata
    """
    try:
        # Processors register themselves at import time via processor_registry
        # (imported above), so no explicit per-call import is needed here.

        # Validate input files exist
        if not os.path.exists(titanium_path):
            return {
                "success": False,
                "error": f"Titanium config file not found: {titanium_path}",
                "input_template": template_path
            }
        
        if not os.path.exists(template_path):
            return {
                "success": False,
                "error": f"Template file not found: {template_path}",
                "input_template": template_path
            }
        
        # Parse Titanium configuration
        parser = TitaniumConfigParser()
        config = parser.parse_file(titanium_path)
        
        # Determine output path
        if not output_path:
            template_file = Path(template_path)
            output_path = str(template_file.parent / f"{template_file.stem}.modified{template_file.suffix}")
        
        # Determine section type from template path or name
        section_type = _determine_section_type(template_path)
        if not section_type:
            return {
                "success": False,
                "error": f"Could not determine section type from template path: {template_path}",
                "input_template": template_path,
                "output_template": output_path
            }
        
        # Get processor and section configuration
        processor = ProcessorRegistry.get_processor(section_type)
        if not processor:
            return {
                "success": False,
                "error": f"No processor available for section type: {section_type}",
                "input_template": template_path,
                "output_template": output_path,
                "section": section_type
            }
        
        # Set full config for processors that support it (like organization processor)
        if hasattr(processor, 'set_full_config'):
            processor.set_full_config(config)
        
        section_config = parser.get_section_data(config, section_type)
        if not section_config:
            return {
                "success": False,
                "error": f"No configuration found for section: {section_type}",
                "input_template": template_path,
                "output_template": output_path,
                "section": section_type
            }
        
        # Read template content
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Process template
        modified_content = processor.process(template_content, section_config)
        modifications = processor.get_modifications()
        
        # Validate parameter naming convention in the modified template
        modifier = TemplateModifier()
        is_valid, validation_errors, parameter_classifications = modifier.validate_template_parameters(modified_content)
        
        # Write output
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        return {
            "success": True,
            "input_template": template_path,
            "output_template": output_path,
            "modifications": modifications,
            "parameters_modified": len(modifications),
            "section": section_type,
            "validation": {
                "naming_convention_valid": is_valid,
                "validation_errors": validation_errors,
                "parameter_classifications": parameter_classifications
            },
            "metadata": {
                "processor_class": processor.__class__.__name__,
                "original_size": len(template_content),
                "modified_size": len(modified_content),
                "output_directory": os.path.dirname(output_path),
                "naming_convention_compliant": is_valid
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "input_template": template_path,
            "output_template": output_path if 'output_path' in locals() else None,
            "section": section_type if 'section_type' in locals() else None
        }


def _determine_section_type(template_path: str) -> Optional[str]:
    """
    Determine section type from template path.
    
    Args:
        template_path: Path to the CloudFormation template
        
    Returns:
        Section type or None if cannot be determined
    """
    path = Path(template_path)
    
    # Check parent directory name first
    parent_name = path.parent.name.lower()
    if parent_name in ['organization', 'security', 'network', 'bootstrap', 'identity', 'logging', 'accounts', 'cost', 'finance']:
        if parent_name in ('cost', 'finance'):
            return 'cost_management'
        return parent_name
    
    # Check template filename for hints
    filename = path.name.lower()
    
    if any(keyword in filename for keyword in ['scp', 'policy', 'organization', 'ou']):
        return 'organization'
    elif any(keyword in filename for keyword in ['security', 'guardduty', 'securityhub', 'config']):
        return 'security'
    elif any(keyword in filename for keyword in ['network', 'vpc', 'tgw', 'firewall', 'dns']):
        return 'network'
    elif any(keyword in filename for keyword in ['bootstrap', 'stacksets', 'role']):
        return 'bootstrap'
    elif any(keyword in filename for keyword in ['identity', 'iam', 'sso']):
        return 'identity'
    elif any(keyword in filename for keyword in ['logging', 'cloudtrail']):
        return 'logging'
    elif any(keyword in filename for keyword in ['accounts']):
        return 'accounts'
    elif any(keyword in filename for keyword in ['cost', 'budget']):
        return 'cost_management'
    
    # Default fallback - try to guess from directory structure
    path_parts = [part.lower() for part in path.parts]
    for part in path_parts:
        if part in ['organization', 'security', 'network', 'bootstrap', 'identity', 'logging', 'accounts']:
            if part == 'accounts':
                return 'accounts'
            return part
    
    return None
