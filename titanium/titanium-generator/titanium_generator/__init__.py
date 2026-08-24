"""
Simplified Titanium Template Modifier Architecture.

This module provides a significantly simplified approach to modifying CloudFormation
templates based on Titanium.yaml configuration, focusing on:
1. Simple YAML parsing without complex data models
2. Direct string-based template modification
3. Convention-based parameter naming
4. Minimal abstraction layers
"""

from .config_parser import TitaniumConfigParser
from .template_modifier import TemplateModifier
from .processor_registry import ProcessorRegistry
from .base_processor import SimpleProcessor

__all__ = [
    'TitaniumConfigParser',
    'TemplateModifier', 
    'ProcessorRegistry',
    'SimpleProcessor'
]
