"""
Simple base processor for Titanium sections.

This module provides a simple base class that processors can inherit from,
focusing on convention-based parameter generation without complex abstraction.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .template_modifier import TemplateModifier
from .config_parser import TitaniumConfigParser

logger = logging.getLogger(__name__)


class SimpleProcessor:
    """
    Simple base processor for Titanium configuration sections.
    
    This processor uses convention-based parameter naming and direct template
    modification to achieve the same results as the complex architecture with
    much less code.
    """
    
    def __init__(self, section_name: str = None):
        """
        Initialize the simple processor.
        
        Args:
            section_name: Name of the Titanium section this processor handles
        """
        self.section_name = section_name
        self.template_modifier = TemplateModifier()
        self.modifications = []
        self.full_config = None
        self.pattern_variables = None
    
    def set_full_config(self, full_config: Dict[str, Any]):
        """
        Set the full Titanium configuration for processors that need access to other sections.
        
        Args:
            full_config: Complete Titanium configuration
        """
        self.full_config = full_config
    
    def set_pattern_variables(self, pattern_variables: Dict[str, Any]):
        """
        Set pattern variables for processors that need access to industry-specific defaults.
        
        Pattern variables provide industry-specific configuration defaults that can be used
        as fallback values when explicit configuration is not provided in the Titanium YAML.
        
        Args:
            pattern_variables: Dictionary of pattern variables from industry patterns
        """
        self.pattern_variables = pattern_variables
    
    def is_control_tower_enabled(self) -> bool:
        """
        Check if Control Tower is enabled from the full configuration.
        
        This method provides consistent access to the Control Tower flag across
        all template processors. The flag value is read from the full_config
        and remains consistent throughout the generation process.
        
        Logs the Control Tower detection status with timestamp and configuration
        source for debugging and audit purposes.
        
        Returns:
            Boolean indicating if Control Tower is enabled (defaults to False)
            
        Raises:
            RuntimeError: If full_config has not been set via set_full_config()
        """
        if self.full_config is None:
            raise RuntimeError(
                "Full configuration has not been set. "
                "Call set_full_config() before accessing Control Tower flag."
            )
        
        # Single source of truth for the Control Tower flag.
        is_enabled = TitaniumConfigParser.get_control_tower_enabled(self.full_config)
        
        # Log detection status for audit trail
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(
            f"Control Tower Detection [{self.section_name}]: enabled={is_enabled}, "
            f"timestamp={timestamp_str}"
        )
        
        return is_enabled
    
    def should_skip_template(
        self,
        template_name: str,
        section_config: Dict[str, Any],
        full_config: Dict[str, Any],
    ) -> Optional[str]:
        """
        Decide whether a template in this section should NOT be generated.

        Lets a processor own the "which templates does this config produce?"
        decision instead of the orchestrator hardcoding filenames. Return a
        human-readable skip reason to suppress the template, or None to generate
        it. The base processor never skips.

        Args:
            template_name: Filename of the template under consideration
            section_config: This section's configuration
            full_config: The complete Titanium configuration

        Returns:
            Skip reason string, or None to generate the template
        """
        return None

    def process(self, template_yaml: str, section_config: Dict[str, Any]) -> str:
        """
        Process a CloudFormation template with Titanium section configuration.
        
        Args:
            template_yaml: CloudFormation template YAML content
            section_config: Configuration dictionary for this section
            
        Returns:
            Modified template YAML content
        """
        # Clear previous modifications
        self.modifications = []
        
        if not section_config:
            return template_yaml
        
        # Extract configuration items
        config_items = self.extract_items(section_config)
        if not config_items:
            return template_yaml
        
        # Generate parameter updates
        parameter_updates = self.generate_parameter_updates(config_items)
        if not parameter_updates:
            return template_yaml
        
        # Apply updates to template
        modified_yaml, modifications = self.template_modifier.update_parameter_defaults(
            template_yaml, parameter_updates
        )
        
        self.modifications = modifications
        return modified_yaml
    
    def extract_items(self, section_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract configuration items from section config.
        
        This method should be overridden by concrete processors.
        
        Args:
            section_config: Configuration dictionary for this section
            
        Returns:
            List of configuration items as dictionaries
        """
        # Default implementation - extract based on common patterns
        items = []
        
        # Handle list-based configurations (like SCPs, OUs)
        for key, value in section_config.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and 'name' in item:
                        items.append({
                            'name': item['name'],
                            'type': key,
                            'enabled': item.get('enable', item.get('enabled', True)),
                            'config': item
                        })
            elif isinstance(value, dict) and value.get('enable', True):
                # Handle service-based configurations (like GuardDuty, SecurityHub)
                items.append({
                    'name': self.normalize_name(key),
                    'type': key,
                    'enabled': value.get('enable', True),
                    'config': value
                })
        
        return items
    
    def generate_parameter_updates(self, config_items: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Generate parameter updates by dispatching each item to a per-type handler.

        Subclasses register handlers via ``_item_handlers()``; items whose type has
        no registered handler fall through to ``_default_item_handler`` (base:
        emit nothing). ``validate_items()`` runs first and ``finalize_parameters()``
        last, as optional whole-list hooks for cross-item logic.

        Args:
            config_items: List of configuration items

        Returns:
            Dictionary of parameter_name -> new_default_value
        """
        self.validate_items(config_items)

        parameter_updates: Dict[str, str] = {}
        handlers = self._item_handlers()
        for item in config_items:
            handler = handlers.get(item.get('type', ''))
            if handler is not None:
                handler(item, parameter_updates)
            else:
                self._default_item_handler(item, parameter_updates)

        self.finalize_parameters(config_items, parameter_updates)
        return parameter_updates

    def _item_handlers(self) -> Dict[str, Any]:
        """
        Return a ``{item_type: handler}`` map for per-type parameter generation.

        Each handler has signature ``handler(item, updates)`` and mutates ``updates``
        in place. The base registers none (so every item hits
        ``_default_item_handler``); concrete processors override this.
        """
        return {}

    def validate_items(self, config_items: List[Dict[str, Any]]) -> None:
        """Optional whole-list validation hook run before dispatch. Base: no-op."""
        pass

    def finalize_parameters(self, config_items: List[Dict[str, Any]], updates: Dict[str, str]) -> None:
        """
        Optional whole-list hook run after per-item dispatch.

        Use for parameters that depend on the full item set / full_config rather than
        a single item (e.g. network VPC-flow-logs bucket, security exclude lists).
        Base: no-op.
        """
        pass

    @staticmethod
    def _bool(value: Any) -> str:
        """Render a value as the CloudFormation string ``"true"``/``"false"``."""
        return "true" if value else "false"

    def _emit_deploy_flag(
        self,
        item: Dict[str, Any],
        updates: Dict[str, str],
        prefix: str = "Deploy",
        default_enabled: bool = True,
    ) -> None:
        """
        Emit the standard ``{prefix}{Name} = true/false`` deployment flag for an item.

        Shared by the processors whose catch-all default is a single deploy flag;
        ``prefix`` selects the convention (``Deploy`` vs titanium-set ``tDeploy``).
        """
        updates[f"{prefix}{item['name']}"] = self._bool(item.get('enabled', default_enabled))

    def _default_item_handler(self, item: Dict[str, Any], updates: Dict[str, str]) -> None:
        """
        Handle an item whose type has no registered handler. Base: emit nothing.

        Processors override this with their catch-all: a single deploy flag (via
        ``_emit_deploy_flag``) or the full convention (via ``_apply_convention``).
        """
        pass

    def _apply_convention(self, item: Dict[str, Any], updates: Dict[str, str]) -> None:
        """
        Opt-in convention-based parameter emission using the t/u naming convention
        ('t' = titanium-set, 'u' = user-provided). Not the dispatch default; call it
        explicitly from a handler that wants this shape (e.g. organization SCPs):

        - ``tDeploy{Name}`` deployment control (always)
        - ``t{Name}Description`` when the item config carries a description
        - configuration-specific parameters via ``_add_config_specific_parameters``
        """
        name = item['name']
        enabled = item.get('enabled', True)
        config = item.get('config', {})

        # 1. Deploy parameter: tDeploy{Name} (titanium-set deployment control)
        updates[f"tDeploy{name}"] = self._bool(enabled)

        # 2. Description parameter: t{Name}Description (titanium-set if from config)
        if 'description' in config:
            updates[f"t{name}Description"] = config['description']

        # 3. Configuration-specific parameters
        self._add_config_specific_parameters(item, updates)

    def _add_config_specific_parameters(self, item: Dict[str, Any], updates: Dict[str, str]) -> None:
        """
        Add configuration-specific parameters based on item type and config.
        
        Args:
            item: Configuration item
            updates: Dictionary to add parameter updates to
        """
        name = item['name']
        config = item.get('config', {})
        item_type = item.get('type', '')
        
        # Handle deployment targets (common pattern)
        # These are typically user-provided at deployment time, so use 'u' prefix
        if 'deploymentTargets' in config:
            targets = config['deploymentTargets']
            if isinstance(targets, dict):
                # Organizational units - user-provided
                if 'organizationalUnits' in targets:
                    ou_param = f"u{name}Targets"
                    ou_list = targets['organizationalUnits']
                    updates[ou_param] = ",".join(ou_list) if ou_list else ""
                
                # Account targets - user-provided
                if 'accounts' in targets:
                    account_param = f"u{name}AccountTargets"
                    account_list = targets['accounts'] or []
                    updates[account_param] = ",".join(account_list) if account_list else ""
        
        # Handle exclude regions (security services pattern)
        # These are typically titanium-set configuration choices
        if 'excludeRegions' in config:
            exclude_param = f"t{name}ExcludeRegions"
            exclude_list = config['excludeRegions']
            updates[exclude_param] = ",".join(exclude_list) if exclude_list else ""
        
        # Handle exclude accounts - titanium-set configuration choices
        if 'excludeAccounts' in config:
            exclude_param = f"t{name}ExcludeAccounts"
            exclude_list = config['excludeAccounts']
            updates[exclude_param] = ",".join(exclude_list) if exclude_list else ""
        
        # Handle policy files - titanium-set configuration choices
        if 'policy' in config:
            policy_param = f"t{name}PolicyFile"
            updates[policy_param] = config['policy']
    
    def normalize_name(self, name: str) -> str:
        """
        Normalize a name for CloudFormation parameter naming conventions.
        
        Args:
            name: Original name
            
        Returns:
            Normalized name in PascalCase
        """
        # Handle camelCase/snake_case conversion
        # Convert snake_case to camelCase first
        if '_' in name:
            parts = name.split('_')
            name = parts[0] + ''.join(word.capitalize() for word in parts[1:])
        
        # Convert to PascalCase
        # Split on capital letters and rejoin
        words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', name)
        if not words:
            # Fallback: just capitalize
            return name.capitalize()
        
        return ''.join(word.capitalize() for word in words)
    
    def get_modifications(self) -> List[str]:
        """
        Get list of modifications made during the last processing operation.
        
        Returns:
            List of modification descriptions
        """
        return self.modifications.copy()
    
    def __str__(self) -> str:
        """String representation."""
        return f"SimpleProcessor(section={self.section_name})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"SimpleProcessor(section={self.section_name}, modifications={len(self.modifications)})"
