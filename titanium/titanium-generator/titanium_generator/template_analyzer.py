"""
Template analyzer for extracting comprehensive parameter information.

This module analyzes CloudFormation templates to extract all parameters,
identify missing configurations, and generate comprehensive deployment guides.
"""

import yaml
import re
from typing import Dict, Any, List, Tuple, Optional, Set


class CloudFormationLoader(yaml.SafeLoader):
    """Custom YAML loader that handles CloudFormation intrinsic functions."""
    pass


def cloudformation_constructor(loader, node):
    """Constructor for CloudFormation intrinsic functions."""
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    elif isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    else:
        return None


# Register constructors for common CloudFormation functions
cf_functions = [
    'Ref', 'GetAtt', 'Join', 'Split', 'Select', 'Sub', 'Base64', 'GetAZs',
    'ImportValue', 'FindInMap', 'Equals', 'Not', 'And', 'Or', 'If', 'Condition',
    'Cidr', 'Transform', 'Length', 'ToJsonString', 'ForEach'
]

for func in cf_functions:
    CloudFormationLoader.add_constructor(f'!{func}', cloudformation_constructor)


class TemplateAnalyzer:
    """
    Analyzes CloudFormation templates to extract parameter information
    and identify configuration gaps.
    """
    
    def __init__(self):
        """Initialize the template analyzer."""
        self.analysis_results = {}
    
    def analyze_template(self, template_content: str, template_name: str = None) -> Dict[str, Any]:
        """
        Analyze a CloudFormation template to extract all parameter information.
        
        Args:
            template_content: CloudFormation template YAML content
            template_name: Optional name for the template
            
        Returns:
            Dictionary containing comprehensive parameter analysis
        """
        try:
            template_data = yaml.load(template_content, Loader=CloudFormationLoader)
        except yaml.YAMLError as e:
            return {
                'error': f"Failed to parse YAML: {str(e)}",
                'template_name': template_name,
                'parameters': {}
            }
        
        parameters = template_data.get('Parameters', {})
        
        analysis = {
            'template_name': template_name,
            'total_parameters': len(parameters),
            'parameters': {},
            'required_parameters': [],
            'optional_parameters': [],
            'parameters_with_defaults': [],
            'parameters_without_defaults': [],
            'deployment_control_parameters': [],
            'configuration_parameters': [],
            'cross_account_parameters': [],
            'summary': {}
        }
        
        # Analyze each parameter
        for param_name, param_config in parameters.items():
            param_analysis = self._analyze_parameter(param_name, param_config)
            analysis['parameters'][param_name] = param_analysis
            
            # Categorize parameters
            if param_analysis['has_default']:
                analysis['parameters_with_defaults'].append(param_name)
                analysis['optional_parameters'].append(param_name)
            else:
                analysis['parameters_without_defaults'].append(param_name)
                analysis['required_parameters'].append(param_name)
            
            # Categorize by purpose
            if param_analysis['category'] == 'deployment_control':
                analysis['deployment_control_parameters'].append(param_name)
            elif param_analysis['category'] == 'configuration':
                analysis['configuration_parameters'].append(param_name)
            elif param_analysis['category'] == 'cross_account':
                analysis['cross_account_parameters'].append(param_name)
        
        # Generate summary
        analysis['summary'] = {
            'requires_user_input': len(analysis['required_parameters']),
            'has_sensible_defaults': len(analysis['parameters_with_defaults']),
            'deployment_ready': len(analysis['required_parameters']) == 0,
            'needs_configuration': len(analysis['required_parameters']) > 0
        }
        
        return analysis
    
    def _analyze_parameter(self, param_name: str, param_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single parameter to extract detailed information.
        
        Args:
            param_name: Parameter name
            param_config: Parameter configuration from template
            
        Returns:
            Dictionary with parameter analysis
        """
        analysis = {
            'name': param_name,
            'type': param_config.get('Type', 'String'),
            'description': param_config.get('Description', ''),
            'default_value': param_config.get('Default'),
            'has_default': 'Default' in param_config,
            'allowed_values': param_config.get('AllowedValues', []),
            'constraints': {},
            'category': self._categorize_parameter(param_name, param_config),
            'purpose': self._determine_parameter_purpose(param_name, param_config),
            'deployment_impact': self._assess_deployment_impact(param_name, param_config)
        }
        
        # Extract constraints
        constraints = {}
        if 'MinLength' in param_config:
            constraints['min_length'] = param_config['MinLength']
        if 'MaxLength' in param_config:
            constraints['max_length'] = param_config['MaxLength']
        if 'MinValue' in param_config:
            constraints['min_value'] = param_config['MinValue']
        if 'MaxValue' in param_config:
            constraints['max_value'] = param_config['MaxValue']
        if 'AllowedPattern' in param_config:
            constraints['pattern'] = param_config['AllowedPattern']
        
        analysis['constraints'] = constraints
        
        return analysis
    
    def _categorize_parameter(self, param_name: str, param_config: Dict[str, Any]) -> str:
        """
        Categorize parameter by its purpose and usage pattern.
        
        Args:
            param_name: Parameter name
            param_config: Parameter configuration
            
        Returns:
            Category string
        """
        name_lower = param_name.lower()
        description = param_config.get('Description', '').lower()
        
        # Deployment control parameters (enable/disable features)
        if (name_lower.startswith('deploy') or 
            name_lower.startswith('enable') or
            name_lower.endswith('enabled') or
            'enable' in description):
            return 'deployment_control'
        
        # Cross-account parameters (account IDs, bucket names from other accounts)
        if ('account' in name_lower and 'id' in name_lower) or \
           ('bucket' in name_lower and 'name' in name_lower) or \
           'cross-account' in description or \
           'from other account' in description:
            return 'cross_account'
        
        # Network/infrastructure parameters
        if any(keyword in name_lower for keyword in ['vpc', 'subnet', 'cidr', 'ip', 'network', 'gateway']):
            return 'network'
        
        # Security parameters
        if any(keyword in name_lower for keyword in ['security', 'policy', 'role', 'permission', 'key']):
            return 'security'
        
        # Configuration parameters (everything else)
        return 'configuration'
    
    def _determine_parameter_purpose(self, param_name: str, param_config: Dict[str, Any]) -> str:
        """
        Determine the specific purpose of a parameter.
        
        Args:
            param_name: Parameter name
            param_config: Parameter configuration
            
        Returns:
            Purpose description
        """
        description = param_config.get('Description', '')
        if description:
            return description
        
        # Generate purpose from name if no description
        name_parts = re.findall(r'[A-Z][a-z]*', param_name)
        if name_parts:
            return f"Configuration for {' '.join(name_parts).lower()}"
        
        return f"Configuration parameter: {param_name}"
    
    def _assess_deployment_impact(self, param_name: str, param_config: Dict[str, Any]) -> str:
        """
        Assess the impact of this parameter on deployment.
        
        Args:
            param_name: Parameter name
            param_config: Parameter configuration
            
        Returns:
            Impact level: 'critical', 'important', 'optional'
        """
        name_lower = param_name.lower()
        
        # Critical parameters (deployment will fail without proper values)
        if not param_config.get('Default') and any(keyword in name_lower for keyword in 
                                                  ['account', 'bucket', 'organization', 'region']):
            return 'critical'
        
        # Important parameters (affect functionality significantly)
        if name_lower.startswith('deploy') or name_lower.startswith('enable'):
            return 'important'
        
        # Optional parameters (have defaults or minimal impact)
        return 'optional'
    
    def compare_with_titanium_config(self, template_analysis: Dict[str, Any], 
                                   titanium_config: Dict[str, Any], 
                                   section_name: str) -> Dict[str, Any]:
        """
        Compare template parameters with Titanium configuration to identify gaps.
        
        Args:
            template_analysis: Result from analyze_template()
            titanium_config: Titanium configuration dictionary
            section_name: Name of the section being analyzed
            
        Returns:
            Dictionary with comparison results and recommendations
        """
        section_config = titanium_config.get(section_name, {})
        
        comparison = {
            'template_name': template_analysis.get('template_name'),
            'section_name': section_name,
            'configured_parameters': [],
            'missing_parameters': [],
            'unused_config': [],
            'parameter_gaps': {},
            'recommendations': []
        }
        
        # Analyze each template parameter
        for param_name, param_info in template_analysis['parameters'].items():
            # Check if this parameter is covered by Titanium config
            is_configured = self._is_parameter_configured(param_name, param_info, section_config)
            
            if is_configured:
                comparison['configured_parameters'].append(param_name)
            else:
                comparison['missing_parameters'].append(param_name)
                comparison['parameter_gaps'][param_name] = {
                    'parameter_info': param_info,
                    'impact': param_info['deployment_impact'],
                    'has_default': param_info['has_default'],
                    'recommendation': self._generate_parameter_recommendation(param_name, param_info)
                }
        
        # Generate overall recommendations
        comparison['recommendations'] = self._generate_recommendations(comparison, template_analysis)
        
        return comparison
    
    def _is_parameter_configured(self, param_name: str, param_info: Dict[str, Any], 
                               section_config: Dict[str, Any]) -> bool:
        """
        Check if a parameter is configured in the Titanium config.
        
        Args:
            param_name: Parameter name
            param_info: Parameter information
            section_config: Section configuration from Titanium
            
        Returns:
            True if parameter is configured
        """
        # This is a simplified check - in reality, we'd need to understand
        # the mapping between Titanium config structure and CloudFormation parameters
        
        # Check for direct parameter name matches
        if param_name in section_config:
            return True
        
        # Check for common patterns
        name_lower = param_name.lower()
        
        # Deployment control parameters
        if name_lower.startswith('deploy'):
            feature_name = param_name[6:].lower()  # Remove 'Deploy' prefix
            return any(feature_name in str(v).lower() for v in section_config.values())
        
        # Enable parameters
        if name_lower.startswith('enable'):
            feature_name = param_name[6:].lower()  # Remove 'Enable' prefix
            return any(feature_name in str(v).lower() for v in section_config.values())
        
        return False
    
    def _generate_parameter_recommendation(self, param_name: str, param_info: Dict[str, Any]) -> str:
        """
        Generate a recommendation for handling a missing parameter.
        
        Args:
            param_name: Parameter name
            param_info: Parameter information
            
        Returns:
            Recommendation string
        """
        if param_info['has_default']:
            return f"Optional parameter with default value '{param_info['default_value']}'. Consider if default is appropriate for your use case."
        
        impact = param_info['deployment_impact']
        if impact == 'critical':
            return f"CRITICAL: This parameter must be provided before deployment. Add to Titanium configuration or provide during deployment."
        elif impact == 'important':
            return f"IMPORTANT: This parameter affects functionality. Review and configure appropriately."
        else:
            return f"Optional parameter. Review if configuration is needed for your environment."
    
    def _generate_recommendations(self, comparison: Dict[str, Any], 
                                template_analysis: Dict[str, Any]) -> List[str]:
        """
        Generate overall recommendations based on comparison results.
        
        Args:
            comparison: Comparison results
            template_analysis: Template analysis results
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        critical_missing = [p for p, info in comparison['parameter_gaps'].items() 
                          if info['impact'] == 'critical']
        
        if critical_missing:
            recommendations.append(
                f"⚠️  CRITICAL: {len(critical_missing)} critical parameters are not configured: {', '.join(critical_missing)}"
            )
        
        important_missing = [p for p, info in comparison['parameter_gaps'].items() 
                           if info['impact'] == 'important']
        
        if important_missing:
            recommendations.append(
                f"⚡ IMPORTANT: {len(important_missing)} important parameters need review: {', '.join(important_missing)}"
            )
        
        optional_missing = [p for p, info in comparison['parameter_gaps'].items() 
                          if info['impact'] == 'optional' and not info['has_default']]
        
        if optional_missing:
            recommendations.append(
                f"📋 OPTIONAL: {len(optional_missing)} optional parameters without defaults: {', '.join(optional_missing)}"
            )
        
        if template_analysis['summary']['deployment_ready']:
            recommendations.append("✅ Template is deployment-ready with current configuration")
        else:
            recommendations.append("❌ Template requires additional configuration before deployment")
        
        return recommendations
