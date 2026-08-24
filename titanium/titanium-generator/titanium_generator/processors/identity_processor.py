"""
Identity processor for Titanium Template Modifier.

This module handles the identity section which defines IAM password policy,
access analyzer, and Identity Center configurations.
"""

from typing import Dict, Any, List
from ..base_processor import SimpleProcessor
from ..processor_registry import register_processor


@register_processor('identity')
class IdentityProcessor(SimpleProcessor):
    """
    Processor for the Identity section.
    
    This processor handles identity and access management configurations including:
    - IAM password policy settings
    - Access Analyzer configuration
    - Identity Center (SSO) configurations
    - Common roles and permission sets
    """
    
    def extract_items(self, section_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract identity configuration items.
        
        Args:
            section_config: Identity section data from Titanium.yaml.
                When routed via config_parser.get_section_data('identity'), this is
                the raw iamPasswordPolicy dict (e.g., {allowUsersToChangePassword: true, ...}).
                The method detects this by checking for password policy keys directly
                in section_config vs. the nested 'iamPasswordPolicy' key.
            
        Returns:
            List of identity configuration items
        """
        items = []
        
        # Handle IAM Password Policy
        # The config parser maps 'identity' -> 'iamPasswordPolicy', so section_config
        # is the raw password policy dict. Detect this by checking for known password
        # policy keys directly in section_config.
        password_policy_keys = {'allowUsersToChangePassword', 'hardExpiry', 'requireUppercaseCharacters',
                                'requireLowercaseCharacters', 'requireSymbols', 'requireNumbers',
                                'minimumPasswordLength', 'passwordReusePrevention', 'maxPasswordAge'}
        
        if 'iamPasswordPolicy' in section_config:
            # Nested structure: an explicit iamPasswordPolicy key wrapping the policy
            password_policy = section_config['iamPasswordPolicy']
            items.append({
                'name': 'IAMPasswordPolicy',
                'type': 'iam_password_policy',
                'enabled': True,
                'config': password_policy
            })
        elif password_policy_keys & set(section_config.keys()):
            # Direct password policy dict from config_parser.get_section_data('identity')
            items.append({
                'name': 'IAMPasswordPolicy',
                'type': 'iam_password_policy',
                'enabled': True,
                'config': section_config
            })
        
        # Handle Access Analyzer
        if 'accessAnalyzer' in section_config:
            access_analyzer = section_config['accessAnalyzer']
            
            # External access analyzer
            if access_analyzer.get('externalAccess', False):
                items.append({
                    'name': 'AccessAnalyzerExternalAccess',
                    'type': 'access_analyzer_external',
                    'enabled': True,
                    'config': {'type': 'external_access'}
                })
            
            # Unused access analyzer
            if access_analyzer.get('unusedAccess', False):
                items.append({
                    'name': 'AccessAnalyzerUnusedAccess',
                    'type': 'access_analyzer_unused',
                    'enabled': True,
                    'config': {'type': 'unused_access'}
                })
        
        # Handle IAM Identity Center
        if 'iamIdentityCenter' in section_config:
            identity_center = section_config['iamIdentityCenter']
            
            items.append({
                'name': 'IAMIdentityCenter',
                'type': 'iam_identity_center',
                'enabled': True,
                'config': identity_center
            })
            
            # Extract common roles
            common_roles = identity_center.get('commonRoles', [])
            for role in common_roles:
                items.append({
                    'name': f"IdentityCenterRole{role['name']}",
                    'type': 'identity_center_role',
                    'enabled': True,
                    'config': role
                })
        
        return items
    
    def _item_handlers(self):
        return {
            'iam_password_policy': self._handle_password_policy,
            'access_analyzer_external': self._handle_access_analyzer,
            'access_analyzer_unused': self._handle_access_analyzer,
            'iam_identity_center': self._handle_identity_center,
            'identity_center_role': self._handle_identity_center_role,
        }

    def _default_item_handler(self, item, updates):
        # Standard deploy parameter for other components.
        self._emit_deploy_flag(item, updates)

    def _handle_password_policy(self, item, updates):
        config = item.get('config', {})
        updates['tDeployIAMPasswordPolicy'] = self._bool(item['enabled'])

        # Password policy parameters (t-prefix: values from Titanium.yaml)
        updates['tAllowUsersToChangePassword'] = self._bool(config.get('allowUsersToChangePassword', True))
        updates['tHardExpiry'] = self._bool(config.get('hardExpiry', False))
        updates['tRequireUppercaseCharacters'] = self._bool(config.get('requireUppercaseCharacters', True))
        updates['tRequireLowercaseCharacters'] = self._bool(config.get('requireLowercaseCharacters', True))
        updates['tRequireSymbols'] = self._bool(config.get('requireSymbols', True))
        updates['tRequireNumbers'] = self._bool(config.get('requireNumbers', True))

        # Numeric parameters
        updates['tMinimumPasswordLength'] = str(config.get('minimumPasswordLength', 14))
        updates['tPasswordReusePrevention'] = str(config.get('passwordReusePrevention', 24))
        updates['tMaxPasswordAge'] = str(config.get('maxPasswordAge', 90))

    def _handle_access_analyzer(self, item, updates):
        config = item.get('config', {})
        self._emit_deploy_flag(item, updates)

        analyzer_type = config.get('type', '')
        if analyzer_type == 'external_access':
            updates['AccessAnalyzerType'] = 'ACCOUNT'
        elif analyzer_type == 'unused_access':
            updates['AccessAnalyzerType'] = 'ACCOUNT_UNUSED_ACCESS'

    def _handle_identity_center(self, item, updates):
        config = item.get('config', {})
        updates['DeployIAMIdentityCenter'] = self._bool(item['enabled'])

        # Delegated admin account
        delegated_admin = config.get('delegatedAdminAccount', 'Management')
        updates['IdentityCenterDelegatedAdminAccount'] = delegated_admin

        # MFA Configuration
        mfa_config = config.get('mfaConfiguration', {})
        mfa_required = mfa_config.get('mfaRequired', True)
        updates['MFARequired'] = self._bool(mfa_required)

        # ABAC (Attribute-Based Access Control)
        enable_abac = config.get('enableABAC', False)
        updates['EnableABAC'] = self._bool(enable_abac)

        # External Provider
        external_provider = config.get('externalProvider', {})
        if external_provider.get('enabled', False):
            updates['EnableExternalProvider'] = "true"
            updates['ExternalProviderType'] = external_provider.get('externalProvider', 'Okta')
            updates['SAMLIntegration'] = self._bool(external_provider.get('samlIntegration', False))
            updates['SCIMIntegration'] = self._bool(external_provider.get('SCIMIntegration', False))
        else:
            updates['EnableExternalProvider'] = "false"

    def _handle_identity_center_role(self, item, updates):
        name = item['name']
        config = item.get('config', {})
        self._emit_deploy_flag(item, updates)

        # Role description
        description = config.get('description', '')
        if description:
            updates[f"{name}Description"] = description

        # Session duration
        session_duration = config.get('sessionDuration', 3600)
        updates[f"{name}SessionDuration"] = str(session_duration)

        # Policies
        policies = config.get('policies', [])
        if policies:
            updates[f"{name}Policies"] = ",".join(policies)
