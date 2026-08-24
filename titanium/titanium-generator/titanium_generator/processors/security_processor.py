"""
Simplified security processor for Titanium Template Modifier.

This module demonstrates how the security section can be processed
with significantly less code while maintaining the same functionality.
"""

import logging
from typing import Dict, Any, List
from ..base_processor import SimpleProcessor
from ..processor_registry import register_processor

logger = logging.getLogger(__name__)


@register_processor('security')
class SimpleSecurityProcessor(SimpleProcessor):
    """
    Simplified processor for the Security section of Titanium.yaml.
    
    This processor handles security service configurations from the
    centralSecurityServices section and generates CloudFormation template
    parameters following the t/u naming convention.
    
    Supported Services:
        - AWS Config: Configuration recorder and delivery channel settings
        - Security Hub: Compliance standards and delegated admin
        - GuardDuty: Threat detection service
        - Macie: Data security and privacy service
        - Detective: Security investigation service
        - Audit Manager: Compliance auditing service
        - EBS Default Volume Encryption: Encryption settings
        - S3 Public Access Block: S3 security settings
    
    Parameter Naming Convention:
        - t-parameters: Titanium-set values (derived from Titanium.yaml)
        - u-parameters: User-provided values (supplied at deployment)
    
    This processor uses convention-based parameter naming instead of complex
    matching logic, making it easier to maintain and extend.
    """
    
    def extract_items(self, section_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract security configuration items from Titanium.yaml.
        
        This method processes the centralSecurityServices section and extracts
        configuration for AWS Config, Security Hub, and other security services.
        It handles backward compatibility by gracefully handling missing sections.
        
        Args:
            section_config: The centralSecurityServices section from Titanium.yaml
                           containing security service configurations
            
        Returns:
            List of configuration items, where each item is a dictionary with:
                - name: Service name (e.g., 'ConfigRecorder', 'SecurityHub')
                - type: Service type identifier (e.g., 'aws_config', 'securityHub')
                - enabled: Boolean indicating if the service is enabled
                - config: Service-specific configuration dictionary
        
        Note:
            - If awsConfig section is missing, no AWS Config items are generated
            - If a service section is missing, it is skipped gracefully
            - Disabled services are still included with enabled=False to generate
              parameters with "false" values for proper CloudFormation handling
        """
        items = []
        
        # Extract AWS Config configuration
        # Backward compatibility: Only process if awsConfig section exists in Titanium.yaml
        # This allows existing configurations without awsConfig to continue working
        aws_config = section_config.get('awsConfig')
        if aws_config is not None:
            # Always add AWS Config item if section exists, even if disabled
            # This ensures parameters are generated with "false" values when disabled,
            # which is required for proper CloudFormation template parameter handling
            enable_recorder = aws_config.get('enableConfigurationRecorder', False)
            items.append({
                'name': 'ConfigRecorder',
                'type': 'aws_config',
                'enabled': enable_recorder,
                'config': aws_config
            })
        else:
            # Log info when awsConfig section is missing (backward compatibility)
            logger.info("awsConfig section not found in Titanium.yaml. Skipping AWS Config parameter generation.")
        
        # Extract delegated admin configuration for Security Hub
        # When delegatedAdminAccount is set to a value other than 'Management',
        # Security Hub administration is delegated to the specified account
        delegated_admin = section_config.get('delegatedAdminAccount')
        if delegated_admin and delegated_admin != 'Management':
            items.append({
                'name': 'SecurityHubDelegatedAdmin',
                'type': 'security_hub_delegate',
                'enabled': True,
                'config': {'admin_account': delegated_admin}
            })
        
        # Extract each security service using simple pattern matching
        # This dictionary maps Titanium.yaml keys to service names used in parameter generation
        services = {
            'guardduty': 'GuardDuty',
            'securityHub': 'SecurityHub', 
            'macie': 'Macie',
            'detective': 'Detective',
            'auditManager': 'AuditManager',
            'ebsDefaultVolumeEncryption': 'EBSDefaultVolumeEncryption',
            's3PublicAccessBlock': 'S3PublicAccessBlock'
        }
        
        for service_key, service_name in services.items():
            if service_key in section_config:
                service_config = section_config[service_key]
                # Only process if the service configuration is a dictionary
                # This prevents errors if the service is configured as a simple boolean
                if isinstance(service_config, dict):
                    items.append({
                        'name': service_name,
                        'type': service_key,
                        'enabled': service_config.get('enable', True),
                        'config': service_config
                    })
        
        # Log info if securityHub section is missing (backward compatibility)
        if 'securityHub' not in section_config:
            logger.info("securityHub section not found in Titanium.yaml. Skipping Security Hub parameter generation.")
        
        return items
    
    def _item_handlers(self):
        return {
            'aws_config': self._handle_aws_config,
            'security_hub_delegate': self._handle_security_hub_delegate,
            'securityHub': self._handle_security_hub,
        }

    def _default_item_handler(self, item, updates):
        # Standard deploy parameter for other security services (guardduty, macie,
        # detective, auditManager, ebsDefaultVolumeEncryption, s3PublicAccessBlock).
        self._emit_deploy_flag(item, updates)

    def finalize_parameters(self, config_items, updates):
        """
        Cross-cutting exclusions that apply to every service item regardless of type.

        Comma-delimited lists of regions/accounts where a service should not deploy
        (e.g. GuardDutyExcludeRegions, MacieExcludeAccounts).
        """
        for item in config_items:
            name = item['name']
            config = item.get('config', {})

            if 'excludeRegions' in config:
                exclude_regions = config['excludeRegions']
                if exclude_regions:
                    updates[f"{name}ExcludeRegions"] = ",".join(exclude_regions)

            if 'excludeAccounts' in config:
                exclude_accounts = config['excludeAccounts']
                if exclude_accounts:
                    updates[f"{name}ExcludeAccounts"] = ",".join(exclude_accounts)

    def _handle_aws_config(self, item, updates):
        # Maps to the AWS Config template parameters. Only generates 't' parameters
        # derivable from Titanium.yaml; 'u' parameters are supplied at deploy time.
        config = item.get('config', {})

        # Home region is titanium-set: which region aggregates Config data.
        updates['tHomeRegionName'] = config.get('homeRegion', 'us-east-1')

        # enableConfigurationRecorder -> tAllSupported (non-bool treated as false).
        enable_recorder = config.get('enableConfigurationRecorder', True)
        if not isinstance(enable_recorder, bool):
            logger.warning(
                f"Invalid type for enableConfigurationRecorder: {type(enable_recorder).__name__}. "
                f"Expected bool. Treating as false."
            )
            enable_recorder = False
        updates['tAllSupported'] = self._bool(enable_recorder)

        # enableGlobalResourceTypes -> tIncludeGlobalResourceTypes (non-bool -> false).
        enable_global = config.get('enableGlobalResourceTypes', True)
        if not isinstance(enable_global, bool):
            logger.warning(
                f"Invalid type for enableGlobalResourceTypes: {type(enable_global).__name__}. "
                f"Expected bool. Treating as false."
            )
            enable_global = False
        updates['tIncludeGlobalResourceTypes'] = self._bool(enable_global)

        # deliveryChannelFrequency -> tFrequency (invalid values default to 24hours).
        frequency = config.get('deliveryChannelFrequency', '24hours')
        valid_frequencies = ['1hour', '3hours', '6hours', '12hours', '24hours']
        if frequency not in valid_frequencies:
            logger.warning(
                f"Invalid deliveryChannelFrequency value '{frequency}'. "
                f"Must be one of {valid_frequencies}. Using default '24hours'."
            )
            frequency = '24hours'
        updates['tFrequency'] = frequency

        # resourceTypes -> tResourceTypes (comma-delimited; empty when AllSupported).
        resource_types = config.get('resourceTypes', [])
        updates['tResourceTypes'] = ','.join(resource_types) if resource_types else ''

    def _handle_security_hub_delegate(self, item, updates):
        # The delegated-admin template only has 'u' parameters (supplied at deploy
        # time), so no 't' parameters are generated here.
        pass

    def _handle_security_hub(self, item, updates):
        # Security Hub standards are auto-mapped for organization-wide deployment.
        config = item.get('config', {})
        standards = config.get('standards', [])

        if not standards:
            logger.info("Security Hub standards list is empty. No standard parameters will be generated.")

        standards_mapping = {
            "AWS Foundational Security Best Practices v1.0.0": "tEnableAFSBPStandard",
            "CIS AWS Foundations Benchmark v1.2.0": "tEnableCIS12Standard",
            "CIS AWS Foundations Benchmark v1.4.0": "tEnableCIS14Standard",
            "NIST Special Publication 800-53 Revision 5": "tEnableNISTStandard",
            "PCI DSS v3.2.1": "tEnablePCIStandard"
        }

        # Only standards present in Titanium.yaml generate parameters; absent ones
        # use template defaults, and unknown ones are skipped with a warning.
        for standard in standards:
            standard_name = standard.get('name', '')
            enabled_standard = standard.get('enable', False)

            if standard_name in standards_mapping:
                updates[standards_mapping[standard_name]] = self._bool(enabled_standard)
            else:
                logger.warning(
                    f"Unknown Security Hub standard '{standard_name}'. "
                    f"Known standards: {list(standards_mapping.keys())}. Skipping."
                )
