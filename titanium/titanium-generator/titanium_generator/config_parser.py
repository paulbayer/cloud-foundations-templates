"""
Simple Titanium configuration parser.

This module provides a lightweight parser that works directly with YAML dictionaries
without complex data model validation.
"""

import yaml
from typing import Dict, Any, List, Optional


class TitaniumConfigParser:
    """
    Simple parser for Titanium.yaml configuration files.
    
    This parser focuses on simplicity and direct access to configuration data
    without complex validation or data model transformation.
    """
    
    def __init__(self):
        """Initialize the parser."""
        pass
    
    def parse(self, yaml_content: str, source_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse Titanium.yaml configuration from string content.
        
        Args:
            yaml_content: Raw YAML content string
            source_name: Optional source identifier for error reporting
            
        Returns:
            Dictionary containing the parsed configuration
            
        Raises:
            yaml.YAMLError: If YAML parsing fails
            ValueError: If required fields are missing
        """
        try:
            config = yaml.safe_load(yaml_content)
            
            if not isinstance(config, dict):
                raise ValueError(f"Configuration must be a dictionary, got {type(config).__name__}")
            
            # Basic validation of required fields
            self._validate_required_fields(config, source_name)
            
            return config
            
        except yaml.YAMLError as e:
            error_msg = f"Failed to parse YAML"
            if source_name:
                error_msg += f" from {source_name}"
            error_msg += f": {str(e)}"
            raise yaml.YAMLError(error_msg) from e
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse Titanium.yaml configuration from file.
        
        Args:
            file_path: Path to the Titanium.yaml file
            
        Returns:
            Dictionary containing the parsed configuration
            
        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self.parse(content, file_path)
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Titanium configuration file not found: {file_path}")
    
    def get_available_sections(self, config: Dict[str, Any]) -> List[str]:
        """
        Get list of available sections for processing.
        
        Args:
            config: Parsed configuration dictionary
            
        Returns:
            List of section names that have content
        """
        available_sections = []
        
        # Section name mapping from Titanium.yaml keys to processor names
        section_mapping = {
            'organization': 'organization',
            'centralSecurityServices': 'security',
            'iamPasswordPolicy': 'identity',
            'logging': 'logging',
            'network': 'network',
            'accounts': 'accounts',
            'cloudFinancialManagement': 'cost_management',
            'controlTower': 'control_tower',
            'bootstrap': 'bootstrap'
        }
        
        for yaml_key, processor_name in section_mapping.items():
            if yaml_key in config and config[yaml_key] is not None:
                # Check if section has content (not just empty dict)
                section_data = config[yaml_key]
                if isinstance(section_data, dict) and section_data:
                    available_sections.append(processor_name)
                elif not isinstance(section_data, dict):
                    # Non-dict sections are considered available if present
                    available_sections.append(processor_name)
        
        return available_sections
    
    def get_section_data(self, config: Dict[str, Any], section_name: str) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific section.
        
        Args:
            config: Parsed configuration dictionary
            section_name: Name of the section (processor name)
            
        Returns:
            Section data dictionary or None if not found
        """
        # Reverse mapping from processor names to YAML keys
        key_mapping = {
            'organization': 'organization',
            'security': 'centralSecurityServices',
            'identity': 'iamPasswordPolicy',
            'logging': 'logging',
            'network': 'network',
            'accounts': 'accounts',
            'cost_management': 'cloudFinancialManagement',
            'control_tower': 'controlTower',
            'bootstrap': 'bootstrap'
        }
        
        yaml_key = key_mapping.get(section_name)
        if yaml_key and yaml_key in config:
            return config[yaml_key]
        
        return None
    
    @staticmethod
    def get_control_tower_enabled(config: Dict[str, Any]) -> bool:
        """
        Extract controlTower.enable flag from configuration.

        This is the single source of truth for the Control Tower flag; callers
        that don't hold a parser instance can invoke it as
        ``TitaniumConfigParser.get_control_tower_enabled(config)``.

        Args:
            config: Parsed configuration dictionary

        Returns:
            Boolean indicating if Control Tower is enabled (defaults to False)
        """
        if 'controlTower' not in config:
            return False
        
        control_tower = config['controlTower']
        if not isinstance(control_tower, dict):
            return False
        
        return control_tower.get('enable', False)
    
    def _validate_required_fields(self, config: Dict[str, Any], source_name: Optional[str] = None) -> None:
        """
        Validate that required fields are present.
        
        Args:
            config: Configuration dictionary to validate
            source_name: Optional source name for error reporting
            
        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ['homeRegion', 'enabledRegions']
        missing_fields = []
        
        for field in required_fields:
            if field not in config:
                missing_fields.append(field)
        
        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            if source_name:
                error_msg += f" in {source_name}"
            raise ValueError(error_msg)
        
        # Validate enabledRegions is a list
        if not isinstance(config['enabledRegions'], list):
            error_msg = "enabledRegions must be a list"
            if source_name:
                error_msg += f" in {source_name}"
            raise ValueError(error_msg)
