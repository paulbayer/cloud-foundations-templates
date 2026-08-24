"""
Simple processor registry for Titanium sections.

This module provides a lightweight registry for section processors without
complex factory patterns or dependency injection.
"""

from typing import Dict, Type, Optional
from .base_processor import SimpleProcessor


class ProcessorRegistry:
    """
    Simple registry for section processors.
    
    This registry uses a straightforward dictionary-based approach without
    complex initialization or dependency management.
    """
    
    # Class-level registry to store processor classes
    _processors: Dict[str, Type[SimpleProcessor]] = {}
    
    @classmethod
    def register(cls, section_name: str, processor_class: Type[SimpleProcessor]) -> None:
        """
        Register a processor for a specific section.
        
        Args:
            section_name: Name of the Titanium section
            processor_class: Processor class to register
        """
        cls._processors[section_name] = processor_class
    
    @classmethod
    def get_processor(cls, section_name: str) -> Optional[SimpleProcessor]:
        """
        Get a processor instance for the specified section.
        
        Args:
            section_name: Name of the Titanium section
            
        Returns:
            Processor instance or None if not found
        """
        processor_class = cls._processors.get(section_name)
        if processor_class:
            return processor_class(section_name)
        return None
    
    @classmethod
    def is_supported(cls, section_name: str) -> bool:
        """
        Check if a section is supported by a registered processor.
        
        Args:
            section_name: Name of the Titanium section
            
        Returns:
            True if section is supported, False otherwise
        """
        return section_name in cls._processors
    
    @classmethod
    def get_supported_sections(cls) -> list[str]:
        """
        Get list of all supported sections.
        
        Returns:
            List of section names with registered processors
        """
        return list(cls._processors.keys())
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered processors (useful for testing)."""
        cls._processors.clear()


# Decorator for easy processor registration
def register_processor(section_name: str):
    """
    Decorator to register a processor for a section.
    
    Args:
        section_name: Name of the Titanium section
        
    Example:
        @register_processor('organization')
        class OrganizationProcessor(SimpleProcessor):
            pass
    """
    def decorator(processor_class: Type[SimpleProcessor]):
        ProcessorRegistry.register(section_name, processor_class)
        return processor_class
    return decorator


# Import processors to register them
from .processors.organization_processor import SimpleOrganizationProcessor
from .processors.security_processor import SimpleSecurityProcessor
from .processors.bootstrap_processor import BootstrapProcessor
from .processors.network_processor import NetworkProcessor
from .processors.identity_processor import IdentityProcessor
from .processors.controltower_processor import ControlTowerProcessor
from .processors.finance_processor import FinanceProcessor
