"""
Parse Titanium configuration MCP tool.

This tool parses and validates Titanium.yaml files using the simplified architecture.
"""

import os
from typing import Dict, Any
from ..config_parser import TitaniumConfigParser


def parse_titanium_config(titanium_path: str) -> Dict[str, Any]:
    """
    Parse and validate a Titanium YAML configuration file.
    
    Args:
        titanium_path: Path to the Titanium.yaml file
        
    Returns:
        Dictionary containing parsed config and validation results
    """
    try:
        # Validate file exists
        if not os.path.exists(titanium_path):
            return {
                "success": False,
                "error": f"Titanium config file not found: {titanium_path}",
                "validation_errors": []
            }
        
        # Parse configuration
        parser = TitaniumConfigParser()
        config = parser.parse_file(titanium_path)
        
        # Get available sections
        sections = parser.get_available_sections(config)
        
        return {
            "success": True,
            "config": config,
            "sections": sections,
            "validation_errors": [],
            "file_path": titanium_path,
            "metadata": {
                "total_sections": len(sections),
                "file_size_bytes": os.path.getsize(titanium_path),
                "parser_type": "simplified"
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "validation_errors": [str(e)],
            "file_path": titanium_path
        }
