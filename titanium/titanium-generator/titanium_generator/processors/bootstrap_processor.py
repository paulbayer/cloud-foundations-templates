"""
Bootstrap processor for Titanium Template Modifier.

This module handles the bootstrap section which contains infrastructure preparation
resources required before main infrastructure deployment, including Config roles
and CloudFormation StackSets Organizations integration.
"""

from typing import Dict, Any, List
from ..base_processor import SimpleProcessor
from ..processor_registry import register_processor


@register_processor('bootstrap')
class BootstrapProcessor(SimpleProcessor):
    """
    Processor for the Bootstrap section.
    
    This processor handles bootstrap infrastructure components including:
    - Config recorder roles for management account
    - CloudFormation StackSets Organizations integration
    - Target account configurations
    """
    
    def extract_items(self, section_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract bootstrap configuration items.
        
        Args:
            section_config: Bootstrap section from Titanium.yaml
            
        Returns:
            List of bootstrap configuration items
        """
        items = []
        
        if not section_config or not section_config.get('enabled', True):
            return items
        
        # Extract Config Role configuration
        config_role = section_config.get('configRole', {})
        if config_role.get('enabled', True):  # Default enabled if bootstrap is enabled
            items.append({
                'name': 'ConfigRecorderRole',
                'type': 'config_recorder_role',
                'enabled': True,
                'config': config_role
            })
        
        # Extract Organizations Integration for CloudFormation
        orgs_integration_cfn = section_config.get('organizationsIntegrationCfn', {})
        if orgs_integration_cfn.get('enabled', True):
            items.append({
                'name': 'StackSetsOrganizationsIntegration',
                'type': 'organizations_integration_cfn',
                'enabled': orgs_integration_cfn.get('enabled', True),
                'config': orgs_integration_cfn
            })
        
        return items

    # No _item_handlers / _default_item_handler overrides: the bootstrap templates
    # (01-config-stack-mgmt-role.yaml, 02-stacksets-stack-mgmt-enable.yaml) only have
    # 'u' (user-provided, deploy-time) parameters, so there are no 't' parameters to
    # derive from Titanium config. The inherited dispatch emits nothing for these
    # items (empty handler map + base no-op default). Add handlers here if a future
    # bootstrap template gains derivable 't' parameters.
