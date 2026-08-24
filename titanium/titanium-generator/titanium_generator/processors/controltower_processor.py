"""
Control Tower processor for Titanium Template Modifier.

This module handles the controlTower section which defines AWS Control Tower
landing zone settings including version, logging, and security configurations.
"""

from typing import Dict, Any, List
from ..base_processor import SimpleProcessor
from ..processor_registry import register_processor


@register_processor('control_tower')
class ControlTowerProcessor(SimpleProcessor):
    """
    Processor for the Control Tower section.
    
    This processor handles Control Tower configurations including:
    - Landing zone version settings
    - Logging configuration (organization trail, bucket retention)
    - Security settings (Identity Center access, region denial)
    - Network factory configuration
    """
    
    def extract_items(self, section_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract Control Tower configuration items.
        
        Args:
            section_config: controlTower section from Titanium.yaml
            
        Returns:
            List of Control Tower configuration items
        """
        items = []
        
        if not section_config or not section_config.get('enable', False):
            return items
        
        # Main Control Tower configuration
        items.append({
            'name': 'ControlTower',
            'type': 'control_tower_main',
            'enabled': section_config.get('enable', False),
            'config': section_config
        })
        
        # Landing Zone configuration
        landing_zone = section_config.get('landingZone', {})
        if landing_zone:
            items.append({
                'name': 'ControlTowerLandingZone',
                'type': 'landing_zone',
                'enabled': True,
                'config': landing_zone
            })
            
            # Logging configuration
            logging_config = landing_zone.get('logging', {})
            if logging_config:
                items.append({
                    'name': 'ControlTowerLogging',
                    'type': 'control_tower_logging',
                    'enabled': True,
                    'config': logging_config
                })
            
            # Security configuration
            security_config = landing_zone.get('security', {})
            if security_config:
                items.append({
                    'name': 'ControlTowerSecurity',
                    'type': 'control_tower_security',
                    'enabled': True,
                    'config': security_config
                })
            
            # Network configuration
            network_config = landing_zone.get('network', {})
            if network_config:
                items.append({
                    'name': 'ControlTowerNetwork',
                    'type': 'control_tower_network',
                    'enabled': True,
                    'config': network_config
                })
        
        return items
    
    def _item_handlers(self):
        return {
            'control_tower_main': self._handle_main,
            'landing_zone': self._handle_landing_zone,
            'control_tower_logging': self._handle_logging,
            'control_tower_security': self._handle_security,
            'control_tower_network': self._handle_network,
        }

    def _default_item_handler(self, item, updates):
        # Standard deploy parameter for other components.
        self._emit_deploy_flag(item, updates)

    def _handle_main(self, item, updates):
        updates['DeployControlTower'] = self._bool(item['enabled'])

    def _handle_landing_zone(self, item, updates):
        config = item.get('config', {})
        updates['DeployLandingZone'] = self._bool(item['enabled'])

        # Landing Zone version - titanium-set parameter
        version = config.get('version', '4.0')
        updates['LandingZoneVersion'] = version
        updates['tVersion'] = version

        # Governed regions - titanium-set parameter
        governed_regions = config.get('governedRegions', ['us-east-1'])
        if isinstance(governed_regions, list):
            updates['tGovernedRegions'] = ','.join(governed_regions)
        else:
            updates['tGovernedRegions'] = str(governed_regions)

        # Hub OU name - titanium-set parameter.
        #
        # Landing zone 4.0 removed organizationStructure from the manifest, so
        # Control Tower no longer creates the Security or Sandbox OUs.
        # controltower/01 now creates a single hub OU to hold the service
        # integration accounts, named by tSecurityOuName. The Sandbox OU (and the
        # remaining OUs) are owned by organization/01, so no tSandboxOuName is
        # emitted - that parameter no longer exists in the template.
        #
        # organizationStructure is still read here for backward compatibility with
        # hand-written configs; the advisor has never emitted it, so in practice
        # this falls through to the default.
        org_structure = config.get('organizationStructure', {})
        security_ou = org_structure.get('security', {}).get('name', 'Security')
        updates['tSecurityOuName'] = security_ou

    def _handle_logging(self, item, updates):
        config = item.get('config', {})
        # Organization Trail
        org_trail = config.get('controlTowerOrganizationTrail', True)
        updates['ControlTowerOrganizationTrail'] = self._bool(org_trail)

        # Organization Trail (alternative name)
        org_trail_alt = config.get('organizationTrail', True)
        updates['OrganizationTrail'] = self._bool(org_trail_alt)

        # Bucket retention settings - both old and new parameter names
        logging_retention = config.get('loggingBucketRetentionDays', 365)
        updates['LoggingBucketRetentionDays'] = str(logging_retention)
        updates['tLoggingBucketRetentionPeriod'] = str(logging_retention)

        access_logging_retention = config.get('accessLoggingBucketRetentionDays', 3650)
        updates['AccessLoggingBucketRetentionDays'] = str(access_logging_retention)
        updates['tAccessLoggingBucketRetentionPeriod'] = str(access_logging_retention)

    def _handle_security(self, item, updates):
        # Identity Center management is not driven from config here: the CT template
        # has no EnableIdentityCenterAccess parameter, and Control Tower is assumed
        # to manage Identity Center (see #77). The former emission targeted a
        # non-existent parameter and was a silent no-op, so it has been removed.
        config = item.get('config', {})
        deny_region = config.get('denyRegion', True)
        updates['DenyRegion'] = self._bool(deny_region)

    def _handle_network(self, item, updates):
        # Network Factory is always disabled here: the config value is not currently
        # wired to a live template parameter, so both the "configured" and "unset"
        # cases resolve to the same defaults.
        updates['EnableNetworkFactory'] = "false"
        updates['NetworkFactoryConfiguration'] = ""
