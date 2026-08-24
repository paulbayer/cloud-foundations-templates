"""
Network processor for Titanium Template Modifier.

This module handles the network section which defines high-level network architecture
settings including VPC configurations, Transit Gateway, and connectivity options.
"""

import logging
from typing import Dict, Any, List, Optional
from ..base_processor import SimpleProcessor
from ..processor_registry import register_processor

logger = logging.getLogger(__name__)


@register_processor('network')
class NetworkProcessor(SimpleProcessor):
    """
    Processor for the Network section.

    This processor handles network architecture configurations including:
    - Architecture type selection (TGW, CloudWan, SharedVPC, Hybrid)
    - VPC configurations (endpoint, inspection, workload VPCs)
    - Transit Gateway settings
    - Hybrid connectivity options
    - Default VPC management
    """

    # Templates that target a dedicated Network account. When the config has no
    # advanced network features these are skipped (issue #34). Default-VPC deletion
    # is an org-wide StackSet, so it is intentionally NOT in this list.
    NETWORK_ACCOUNT_TEMPLATES = frozenset({
        '01-ipam-stack-mgmt-delegation.yaml',
        '02-ipam-stackset-network-sharing.yaml',
        '04a-tgw-stackset-network-egress-vpc.yaml',
        '04b-tgw-stackset-network-inspection-vpc-firewall.yaml',
        '05-dns-stackset-network-resolver.yaml',
        '06-vpc-stackset-network-endpoint-vpc.yaml',
        '07-vpc-stackset-network-workload-vpc.yaml',
    })

    # The two mutually-exclusive TGW templates; exactly one is generated based on
    # whether Network Firewall is enabled.
    _TGW_EGRESS_TEMPLATE = '04a-tgw-stackset-network-egress-vpc.yaml'
    _TGW_FIREWALL_TEMPLATE = '04b-tgw-stackset-network-inspection-vpc-firewall.yaml'

    # The centralized Endpoint VPC template. It has no whole-template deploy gate
    # internally, so opting out (tgwArchitecture.vpcs.endpointVpc.enabled=false)
    # is enforced here at generation time (issue #81).
    _ENDPOINT_VPC_TEMPLATE = '06-vpc-stackset-network-endpoint-vpc.yaml'

    # IPAM delegation (01) + sharing (02). When ipam.enabled=false these deploy as
    # no-ops (empty StackSet + org-wide instances that provision nothing), so they
    # are skipped at generation time rather than emitted (issue #82).
    _IPAM_TEMPLATES = frozenset({
        '01-ipam-stack-mgmt-delegation.yaml',
        '02-ipam-stackset-network-sharing.yaml',
    })

    # Hybrid DNS / Route53 Resolver StackSet. Opt-in (obs-085 added the interview
    # question); when route53Resolver.enabled=false it is skipped at generation
    # time so it does not appear as a deploy step and does not create resolver
    # endpoints (~$0.125/hr per ENI) the user opted out of (issue #95).
    _DNS_RESOLVER_TEMPLATE = '05-dns-stackset-network-resolver.yaml'

    # Workload VPC StackSet. Never deployed: workload VPCs belong to workload
    # accounts provisioned by Control Tower account vending, not to a
    # Titanium-managed StackSet (which would target the Network account). The
    # template is kept in the repo but is not actionable (issue #87).
    _WORKLOAD_VPC_TEMPLATE = '07-vpc-stackset-network-workload-vpc.yaml'

    # Centralized VPC Flow Logs S3 bucket (Log Archive). It has no whole-template
    # deploy gate internally: finalize_parameters sets tDeployVPCFlowLogsBucket
    # but that only toggles a parameter, so the template was emitted (and the
    # bucket deployed) even when flow logs were disabled. Skipping it at
    # generation time when the bucket is not needed matches obs-081/082/095
    # (issue #100).
    _FLOWLOGS_BUCKET_TEMPLATE = '03-vpc-stackset-logarchive-flowlogs-bucket.yaml'

    def should_skip_template(
        self,
        template_name: str,
        section_config: Dict[str, Any],
        full_config: Dict[str, Any],
    ) -> Optional[str]:
        """
        Skip network templates that this configuration should not produce.

        Rules, checked in this order (matching the previous orchestrator
        behavior):
        1. Minimal config: if no advanced network features are present, the
           Network-account templates are not needed (issue #34).
        2. TGW template selection: keep only the 04A/04B template that matches
           the Network Firewall configuration.
        3. Endpoint VPC opt-out: skip template 06 when the centralized Endpoint
           VPC is disabled (issue #81).
        4. IPAM opt-out: skip templates 01/02 when IPAM is disabled (issue #82).
        5. Workload VPC: template 07 is never deployed (issue #87).
        6. DNS resolver opt-out: skip template 05 when hybrid DNS / Route53
           Resolver is disabled (issue #95).
        7. Flow-logs bucket opt-out: skip template 03 when the centralized VPC
           Flow Logs bucket is not needed (issue #100).
        """
        if not section_config:
            return None

        # Rule 5 — the workload VPC StackSet is never actioned (checked first so
        # it is skipped regardless of any other network feature).
        if template_name == self._WORKLOAD_VPC_TEMPLATE:
            return 'Workload VPCs are provisioned by Control Tower account vending, not deployed here'

        # Rule 7 — the flow-logs bucket is a Log Archive StackSet, independent of
        # the Network account, so it is checked before the minimal-config rule.
        # Skip it when no S3 flow-log destination, no inspection/egress VPC, and
        # no advisor flow-logs-bucket opt-in require it.
        if template_name == self._FLOWLOGS_BUCKET_TEMPLATE and not self._flow_logs_bucket_needed(
            section_config, full_config
        ):
            return 'VPC flow logs bucket not enabled in configuration'

        # Rule 1 — no Network account required for minimal configs.
        if not self.has_advanced_network_features(section_config):
            if template_name in self.NETWORK_ACCOUNT_TEMPLATES:
                return 'No advanced network features configured — Network account not required'
            return None

        # Rule 3 — the Endpoint VPC is opt-in; skip 06 when it is disabled.
        if template_name == self._ENDPOINT_VPC_TEMPLATE and not self._endpoint_vpc_enabled(section_config):
            return 'Endpoint VPC disabled in configuration'

        # Rule 4 — IPAM delegation/sharing are pointless when IPAM is disabled.
        if template_name in self._IPAM_TEMPLATES and not self._ipam_enabled(section_config):
            return 'IPAM disabled in configuration'

        # Rule 6 — hybrid DNS / Route53 Resolver is opt-in; skip 05 when disabled.
        if template_name == self._DNS_RESOLVER_TEMPLATE and not self._route53_resolver_enabled(section_config):
            return 'Route53 Resolver (hybrid DNS) disabled in configuration'

        # Rule 2 — pick the correct TGW template for the firewall configuration.
        if template_name in (self._TGW_EGRESS_TEMPLATE, self._TGW_FIREWALL_TEMPLATE):
            try:
                correct_template = self.get_tgw_template_name(section_config)
            except Exception as e:
                # Can't determine the correct template — don't skip, just warn.
                logger.warning(f"Could not determine correct TGW template for {template_name}: {e}")
                return None

            if correct_template is None:
                return 'Transit Gateway or Inspection VPC not enabled in configuration'
            if template_name != correct_template:
                if template_name == self._TGW_EGRESS_TEMPLATE:
                    return 'Network Firewall is enabled - using Template 04B instead'
                return 'Network Firewall is disabled - using Template 04A instead'

        return None

    @staticmethod
    def has_advanced_network_features(section_config: Dict[str, Any]) -> bool:
        """
        Determine if the network config requires a dedicated Network account.
        
        Advanced features (TGW architecture, IPAM, hybrid connectivity) require a
        Network account. Minimal configs that only delete default VPCs or set
        availability zones do not.

        workloadVpcs is deliberately NOT a trigger: it derives from the Control
        Tower account-vending setting auto_create_workload_vpcs, which this
        solution does not act on, and its template (07) is never deployed (#87).

        Args:
            section_config: Network section from Titanium.yaml

        Returns:
            True if advanced network features are present, False otherwise
        """
        if not section_config:
            return False

        has_tgw_architecture = bool(section_config.get('tgwArchitecture', {}).get('transitGateway'))
        has_ipam = section_config.get('ipam', {}).get('enabled', False)
        has_hybrid = bool(section_config.get('hybridConnectivity', {}).get('enabled'))

        return has_tgw_architecture or has_ipam or has_hybrid

    @staticmethod
    def _ipam_enabled(section_config: Dict[str, Any]) -> bool:
        """Whether IPAM is enabled.

        Single source of truth shared by extract_items (whether to emit the IPAM
        item / set tDeployIPAM) and should_skip_template (whether to generate the
        IPAM templates). Preserves the historical default-on quirk: an ``ipam``
        block present without an explicit ``enabled`` flag is treated as enabled;
        an absent block is disabled (#82).
        """
        ipam_config = section_config.get('ipam', {}) or {}
        return bool(ipam_config.get('enabled', True if ipam_config else False))

    @staticmethod
    def _endpoint_vpc_enabled(section_config: Dict[str, Any]) -> bool:
        """Whether the centralized Endpoint VPC is enabled.

        Mirrors the path extract_items reads
        (tgwArchitecture.vpcs.endpointVpc.enabled) and defaults to False so the
        opt-in template 06 is not generated unless explicitly requested (#81).
        """
        vpcs = (section_config.get('tgwArchitecture', {}) or {}).get('vpcs', {}) or {}
        return bool((vpcs.get('endpointVpc', {}) or {}).get('enabled', False))

    @staticmethod
    def _route53_resolver_enabled(section_config: Dict[str, Any]) -> bool:
        """Whether hybrid DNS / Route53 Resolver is enabled.

        Mirrors the path extract_items reads
        (tgwArchitecture.route53Resolver.enabled) and defaults to False so the
        opt-in template 05 is not generated unless explicitly requested (#95).
        """
        tgw_arch = section_config.get('tgwArchitecture', {}) or {}
        return bool((tgw_arch.get('route53Resolver', {}) or {}).get('enabled', False))

    def _flow_logs_enabled(self, full_config: Optional[Dict[str, Any]]) -> bool:
        """Whether the user wants VPC flow logs at all.

        True when an S3 destination is configured, when the advisor opted in via
        the flow_logs_bucket_enabled pattern variable, or when the vpcFlowLogs
        section is explicitly enabled. False is the opt-out case (#107): the user
        set vpcFlowLogs.enabled=false, so no VPC flow log should be emitted even
        if the bucket happens to exist for Network Firewall logging.
        """
        vpc_flow_logs = (full_config or {}).get('vpcFlowLogs', {}) or {}
        if 's3' in (vpc_flow_logs.get('destinations', []) or []):
            return True
        if self.pattern_variables and self.pattern_variables.get('flow_logs_bucket_enabled', False):
            return True
        return bool(vpc_flow_logs.get('enabled', False))

    def _flow_logs_bucket_needed(
        self,
        section_config: Dict[str, Any],
        full_config: Optional[Dict[str, Any]],
    ) -> bool:
        """Whether the centralized VPC Flow Logs S3 bucket (template 03) is needed.

        Mirrors the deploy decision finalize_parameters makes for
        tDeployVPCFlowLogsBucket so the two cannot drift. The bucket is required
        when VPC flow logs are enabled (S3 destination / advisor opt-in /
        vpcFlowLogs.enabled), OR when Network Firewall is enabled — its logging
        configuration must deliver to S3, and the firewall will not deploy
        without it. An inspection/egress VPC no longer forces the bucket on when
        the user disabled flow logs (#107, revising #100), unless it runs
        Network Firewall. Otherwise it is skipped.
        """
        # 1. VPC flow logs explicitly enabled -> bucket needed for delivery.
        if self._flow_logs_enabled(full_config):
            return True

        # 2. Network Firewall needs S3 for its logging configuration regardless
        #    of the VPC-flow-logs toggle (firewall won't deploy without logging).
        vpcs = (section_config.get('tgwArchitecture', {}) or {}).get('vpcs', {}) or {}
        if (vpcs.get('inspectionVpc', {}) or {}).get('networkFirewall', False):
            return True

        return False

    def extract_items(self, section_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract network configuration items.
        
        Args:
            section_config: Network section from Titanium.yaml
            
        Returns:
            List of network configuration items
            
        Raises:
            ValueError: If legacy schema keys are detected
        """
        items = []
        
        if not section_config:
            return items
        
        # Legacy-key detection guard: reject old schema paths
        legacy_keys = []
        if 'standardArchitecture' in section_config:
            legacy_keys.append('standardArchitecture')
        if 'transitGateways' in section_config:
            legacy_keys.append('transitGateways')
        if legacy_keys:
            raise ValueError(
                "Legacy network schema detected. Please migrate: rename 'standardArchitecture' to "
                "'tgwArchitecture', remove 'connectivity' wrapper, and delete 'transitGateways' list. "
                "See requirements for the target schema."
            )
        
        # Guard: if no advanced network features, only process default VPC deletion.
        # Minimal configs (e.g. deleteDefaultVpcs + availabilityZones only) do not
        # require a Network account and should not produce IPAM/TGW/DNS/VPC items.
        if not self.has_advanced_network_features(section_config):
            default_vpc_delete = section_config.get('deleteDefaultVpcs', False)
            default_vpc = section_config.get('defaultVpc', {})
            # Support both top-level deleteDefaultVpcs and nested defaultVpc.delete
            if default_vpc_delete or default_vpc.get('delete', False):
                items.append({
                    'name': 'DefaultVpcDeletion',
                    'type': 'default_vpc',
                    'enabled': True,
                    'config': default_vpc if default_vpc else {'delete': True}
                })
            return items
        
        # Extract architecture type for template selection
        architecture_type = section_config.get('architectureType', 'TGW')
        items.append({
            'name': 'NetworkArchitecture',
            'type': 'architecture_type',
            'enabled': True,
            'config': {'architecture_type': architecture_type}
        })
        
        # Extract default VPC handling
        default_vpc = section_config.get('defaultVpc', {})
        if default_vpc.get('delete', False):
            items.append({
                'name': 'DefaultVpcDeletion',
                'type': 'default_vpc',
                'enabled': True,
                'config': default_vpc
            })
        
        # Extract TGW architecture settings (replaces standardArchitecture)
        tgw_arch = section_config.get('tgwArchitecture', {})
        if tgw_arch:
            # VPC configurations (only centralized infra VPCs: endpointVpc, inspectionVpc)
            vpcs = tgw_arch.get('vpcs', {})
            
            # Endpoint VPC
            endpoint_vpc = vpcs.get('endpointVpc', {})
            if endpoint_vpc.get('enabled', False):
                items.append({
                    'name': 'EndpointVpc',
                    'type': 'endpoint_vpc',
                    'enabled': True,
                    'config': endpoint_vpc
                })
            
            # Inspection VPC
            inspection_vpc = vpcs.get('inspectionVpc', {})
            if inspection_vpc.get('enabled', False):
                items.append({
                    'name': 'InspectionVpc',
                    'type': 'inspection_vpc',
                    'enabled': True,
                    'config': inspection_vpc
                })
            
            # Transit Gateway — direct child of tgwArchitecture (no connectivity wrapper, no enabled check)
            # Presence of tgwArchitecture implies TGW is deployed
            tgw = tgw_arch.get('transitGateway', {})
            if tgw:
                items.append({
                    'name': 'TransitGateway',
                    'type': 'transit_gateway',
                    'enabled': True,
                    'config': tgw
                })
            
            # Route53 Resolver — direct child of tgwArchitecture
            route53_resolver = tgw_arch.get('route53Resolver', {})
            if route53_resolver.get('enabled', False):
                items.append({
                    'name': 'Route53Resolver',
                    'type': 'route53_resolver',
                    'enabled': True,
                    'config': route53_resolver
                })
        
        # Workload VPCs are intentionally NOT extracted: their template (07) is
        # never deployed and workloadVpcs derives from the Control Tower
        # account-vending setting auto_create_workload_vpcs, which this solution
        # does not act on (#87).

        # Hybrid connectivity — architecture-independent, at network level
        hybrid = section_config.get('hybridConnectivity', {})
        if hybrid.get('enabled', False):
            items.append({
                'name': 'HybridConnectivity',
                'type': 'hybrid_connectivity',
                'enabled': True,
                'config': hybrid
            })
        
        # Extract IPAM configuration
        ipam_config = section_config.get('ipam', {})
        ipam_enabled = self._ipam_enabled(section_config)

        if ipam_config:  # If IPAM configuration exists, add it to items
            items.append({
                'name': 'IPAM',
                'type': 'ipam',
                'enabled': ipam_enabled,
                'config': ipam_config
            })
        
        return items
    
    def _validate_ipam_pool_id(self, pool_id: str) -> bool:
        """
        Validate IPAM pool ID format.
        
        AWS IPAM pool IDs follow the format: ipam-pool-<hex-string>
        Example: ipam-pool-0a1b2c3d4e5f6g7h8
        
        Args:
            pool_id: The IPAM pool ID to validate
            
        Returns:
            True if valid format, False otherwise
        """
        if not pool_id:
            return False
        
        # Check if it starts with 'ipam-pool-'
        if not pool_id.startswith('ipam-pool-'):
            return False
        
        # Extract the hex portion after 'ipam-pool-'
        hex_portion = pool_id[len('ipam-pool-'):]
        
        # Validate hex portion exists and contains only valid hex characters
        if not hex_portion:
            return False
        
        # Check if all characters are valid hex (0-9, a-f, A-F)
        try:
            int(hex_portion, 16)
            return True
        except ValueError:
            return False
    
    def validate_configuration(self, config_items: List[Dict[str, Any]]) -> None:
        """
        Validate network configuration dependencies before generating parameters.
        
        This method enforces bidirectional dependencies between network components:
        - Transit Gateway requires Egress VPC or Inspection VPC (centralized egress)
        - Inspection VPC requires Transit Gateway (for routing)
        - Network Firewall requires both Transit Gateway and Inspection VPC
        
        Args:
            config_items: List of network configuration items
            
        Raises:
            ValueError: If configuration dependencies are not met
        """
        # Track deployment flags for validation
        transit_gateway_enabled = False
        inspection_vpc_enabled = False
        egress_vpc_enabled = False  # Note: Egress VPC is represented as Inspection VPC without firewall
        network_firewall_enabled = False
        
        # First pass: collect deployment flags
        for item in config_items:
            item_type = item.get('type', '')
            enabled = item.get('enabled', False)
            
            if item_type == 'transit_gateway' and enabled:
                transit_gateway_enabled = True
            elif item_type == 'inspection_vpc' and enabled:
                config = item.get('config', {})
                # Check if Network Firewall is enabled
                if config.get('networkFirewall', False):
                    network_firewall_enabled = True
                    inspection_vpc_enabled = True
                else:
                    # Inspection VPC without firewall acts as Egress VPC
                    egress_vpc_enabled = True
        
        # Validate Inspection VPC dependencies (check this first before Network Firewall)
        if inspection_vpc_enabled and not transit_gateway_enabled:
            raise ValueError(
                "Invalid network configuration: Inspection VPC requires Transit Gateway for traffic routing. "
                "Please enable network.tgwArchitecture.transitGateway in your Titanium YAML configuration."
            )
        
        # Validate Egress VPC dependencies (Inspection VPC without firewall)
        if egress_vpc_enabled and not transit_gateway_enabled:
            raise ValueError(
                "Invalid network configuration: Egress VPC requires Transit Gateway for traffic routing. "
                "Please enable network.tgwArchitecture.transitGateway in your Titanium YAML configuration."
            )
        
        # Validate Network Firewall dependencies
        if network_firewall_enabled:
            if not transit_gateway_enabled:
                raise ValueError(
                    "Invalid network configuration: Network Firewall requires Transit Gateway to be enabled. "
                    "Please enable network.tgwArchitecture.transitGateway in your Titanium YAML configuration."
                )
            if not inspection_vpc_enabled:
                raise ValueError(
                    "Invalid network configuration: Network Firewall requires Inspection VPC to be enabled. "
                    "Please enable network.tgwArchitecture.vpcs.inspectionVpc in your Titanium YAML configuration."
                )
        
        # A Transit Gateway with no Egress/Inspection VPC is a legitimate (if
        # minimal) staged setup — a network account that has stood up a TGW but
        # not yet its centralized egress path. It used to raise here, which hard-
        # failed generation and, because every other network template is skipped
        # in that scenario, surfaced the error misattributed to the flow-logs
        # bucket template (issue #99). It is now a non-fatal warning: with no
        # egress/inspection VPC the TGW templates (04a/04b) are skipped, so the
        # network phase is simply a no-op rather than an error.
        if transit_gateway_enabled:
            has_centralized_egress = egress_vpc_enabled or inspection_vpc_enabled
            if not has_centralized_egress:
                logger.warning(
                    "Transit Gateway is configured with no Egress or Inspection VPC, so no "
                    "centralized internet egress will be deployed. Enable "
                    "network.tgwArchitecture.vpcs.inspectionVpc to add centralized egress."
                )
    
    def validate_items(self, config_items: List[Dict[str, Any]]) -> None:
        """Enforce cross-item network configuration dependencies before dispatch."""
        self.validate_configuration(config_items)

    def _item_handlers(self):
        return {
            'architecture_type': self._handle_architecture_type,
            'default_vpc': self._handle_default_vpc,
            'endpoint_vpc': self._handle_vpc,
            'inspection_vpc': self._handle_vpc,
            'transit_gateway': self._handle_transit_gateway,
            'hybrid_connectivity': self._handle_hybrid_connectivity,
            'route53_resolver': self._handle_route53_resolver,
            'ipam': self._handle_ipam,
        }

    def _default_item_handler(self, item, updates):
        # Standard deploy parameter for other components.
        self._emit_deploy_flag(item, updates, prefix="tDeploy", default_enabled=False)

    def _handle_architecture_type(self, item, updates):
        architecture_type = item.get('config', {}).get('architecture_type', 'TGW')
        updates['tNetworkArchitectureType'] = architecture_type

    def _handle_default_vpc(self, item, updates):
        config = item.get('config', {})
        updates['tDeployDefaultVpcDeletion'] = self._bool(item.get('enabled', False))

        # Exclude accounts
        exclude_accounts = config.get('excludeAccounts', [])
        if exclude_accounts:
            updates['tDefaultVpcExcludeAccounts'] = ",".join(exclude_accounts)

    def _handle_vpc(self, item, updates):
        name = item['name']
        config = item.get('config', {})
        item_type = item.get('type', '')
        updates[f"tDeploy{name}"] = self._bool(item.get('enabled', False))

        # Availability zones
        az_count = config.get('availabilityZones', 2)
        updates[f"t{name}AvailabilityZones"] = str(az_count)

        # Subnets per AZ
        subnets_per_az = config.get('subnetsPerAZ', 2)
        updates[f"t{name}SubnetsPerAZ"] = str(subnets_per_az)

        # VPC-specific parameters
        if item_type == 'endpoint_vpc':
            # An endpoint VPC exists to host centralized service endpoints, so
            # enabling it turns the endpoints on by default (issue #92). The advisor
            # never emits centralEndpoints, and template 06 gates EVERY endpoint
            # (S3 gateway + interface endpoints + SG) on tCentralEndpoints; defaulting
            # this to False produced a green-but-empty endpoint VPC. Default True to
            # match template 06's own default, while still honoring an explicit
            # centralEndpoints: false as an advanced opt-out.
            central_endpoints = config.get('centralEndpoints', True)
            updates['tCentralEndpoints'] = self._bool(central_endpoints)
        elif item_type == 'inspection_vpc':
            network_firewall = config.get('networkFirewall', False)
            updates['tDeployNetworkFirewall'] = self._bool(network_firewall)

            firewall_policy = config.get('firewallPolicy', 'NetworkFirewallPolicy')
            updates['tFirewallPolicyName'] = firewall_policy
            # FirewallPolicyName would be user-provided, so no 't' version needed

    def _handle_transit_gateway(self, item, updates):
        config = item.get('config', {})
        updates['tDeployTransitGateway'] = self._bool(item.get('enabled', False))

        # Route table structure
        route_structure = config.get('routeTableStructure', 'segregated')
        updates['tTransitGatewayRouteTableStructure'] = route_structure

        # Route tables
        route_tables = config.get('routeTables', [])
        if route_tables:
            updates['tTransitGatewayRouteTables'] = ",".join(route_tables)

        # TGW name and ASN (new fields from schema refactor)
        tgw_name = config.get('name')
        if tgw_name:
            updates['tTransitGatewayName'] = tgw_name

        tgw_asn = config.get('asn')
        if tgw_asn is not None:
            updates['tTransitGatewayAsn'] = str(tgw_asn)

    def _handle_hybrid_connectivity(self, item, updates):
        config = item.get('config', {})
        updates['tDeployHybridConnectivity'] = self._bool(item.get('enabled', False))

        connectivity_type = config.get('type', 'DirectConnect')
        updates['tHybridConnectivityType'] = connectivity_type

    def _handle_route53_resolver(self, item, updates):
        config = item.get('config', {})
        updates['tDeployHybridDNS'] = self._bool(item.get('enabled', False))

        # Outbound domains
        outbound_domains = config.get('outboundDomains', [])
        if outbound_domains:
            updates['tOnPremDomains'] = ",".join(outbound_domains)

        # On-premise DNS servers
        dns_servers = config.get('onPremDnsServers', [])
        if dns_servers:
            updates['tOnPremDnsServers'] = ",".join(dns_servers)

        # Allowed source CIDRs
        allowed_cidrs = config.get('allowedSourceCidrs', [])
        if allowed_cidrs:
            updates['tAllowedSourceCidrs'] = ",".join(allowed_cidrs)

    def _handle_ipam(self, item, updates):
        config = item.get('config', {})
        updates['tDeployIPAM'] = self._bool(item.get('enabled', False))

        # IPAM region
        ipam_region = config.get('region', 'us-west-2')
        updates['tIPAMRegion'] = ipam_region

        # Extract pool configurations
        pools = config.get('pools', [])
        if pools is None:
            pools = []

        global_pool_cidr = None
        regional_pool_cidr = None
        regional_pool_ids = []  # Support multiple regional pools

        for pool in pools:
            pool_name = pool.get('name', '')
            provisioned_cidrs = pool.get('provisionedCidrs', [])
            pool_id = pool.get('id', '')

            if pool_name == 'global-pool' and provisioned_cidrs:
                global_pool_cidr = provisioned_cidrs[0]  # Take first CIDR
            elif 'regional-pool' in pool_name:
                if provisioned_cidrs:
                    regional_pool_cidr = provisioned_cidrs[0]  # Take first CIDR

                # Extract and validate pool ID (must start with 'ipam-pool-')
                if pool_id:
                    if self._validate_ipam_pool_id(pool_id):
                        regional_pool_ids.append(pool_id)
                    else:
                        # Log warning but don't fail - allow deployment to proceed
                        print(f"Warning: Invalid IPAM pool ID format: {pool_id}")

        # Set CIDR parameters
        if global_pool_cidr:
            updates['tGlobalIPAMPoolCIDR'] = global_pool_cidr

        if regional_pool_cidr:
            updates['tRegionalPoolCIDR'] = regional_pool_cidr

        # Set regional pool ID parameter (first pool if multiple exist)
        if regional_pool_ids:
            updates['tRegionalIPAMPoolId'] = regional_pool_ids[0]

            if len(regional_pool_ids) > 1:
                print(f"Info: Multiple regional IPAM pools found: {regional_pool_ids}")
                print(f"Info: Using first pool for VPC templates: {regional_pool_ids[0]}")

    def finalize_parameters(self, config_items, updates):
        """
        Decide whether the VPC Flow Logs S3 bucket (and its retention) is needed,
        and whether the per-VPC flow log resources should be created.

        This depends on the whole item set plus full_config / pattern_variables,
        so it runs after per-item dispatch.

        The bucket (tDeployVPCFlowLogsBucket) is deployed when VPC flow logs are
        enabled (S3 destination / advisor opt-in / vpcFlowLogs.enabled) OR when
        Network Firewall is enabled — the firewall's logging configuration must
        deliver to S3 and it will not deploy without it.

        The per-VPC flow logs (tEnableVpcFlowLogs) are gated *separately* on the
        flow-logs-enabled decision only, so that when the user disabled flow logs
        (vpcFlowLogs.enabled=false) no VPC flow log is emitted even though the
        bucket still exists for firewall logging (#107).
        """
        flow_logs_enabled = self._flow_logs_enabled(self.full_config)

        # Network Firewall enabled -> needs S3 bucket for firewall logs, even
        # when VPC flow logs are disabled.
        firewall_enabled = any(
            item.get('type') == 'inspection_vpc'
            and item.get('enabled')
            and item.get('config', {}).get('networkFirewall', False)
            for item in config_items
        )

        deploy_vpc_flow_logs_bucket = flow_logs_enabled or firewall_enabled

        updates['tDeployVPCFlowLogsBucket'] = self._bool(deploy_vpc_flow_logs_bucket)
        # Per-VPC flow log resources follow the user's flow-logs choice, not the
        # bucket's existence, so a firewall-only bucket does not resurrect them.
        updates['tEnableVpcFlowLogs'] = self._bool(flow_logs_enabled)

        # If deploying the bucket, extract retention settings.
        if deploy_vpc_flow_logs_bucket:
            retention_days = None

            # Retention from vpcFlowLogs.retentionDays (advisor output format).
            if self.full_config and 'vpcFlowLogs' in self.full_config:
                retention_days = self.full_config['vpcFlowLogs'].get('retentionDays')

            # Fallback to pattern variable if missing.
            if retention_days is None and self.pattern_variables:
                retention_days = self.pattern_variables.get('vpc_flow_retention')

            # Default to 90 days if none specified.
            if retention_days:
                updates['tBucketRetentionDays'] = str(retention_days)
            else:
                updates['tBucketRetentionDays'] = "90"
    
    def get_template_selection_criteria(self, section_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate template selection criteria based on network configuration.
        
        This can be used by template selectors to choose the most appropriate
        network template based on the architecture type and other factors.
        
        Args:
            section_config: Network section configuration
            
        Returns:
            Dictionary with template selection criteria
        """
        criteria = {}
        
        # Architecture type is the primary selection criterion
        architecture_type = section_config.get('architectureType', 'TGW') 
        criteria['architecture_type'] = architecture_type
        
        # Additional criteria based on enabled components
        tgw_arch = section_config.get('tgwArchitecture', {})
        vpcs = tgw_arch.get('vpcs', {})
        
        criteria['has_endpoint_vpc'] = vpcs.get('endpointVpc', {}).get('enabled', False)
        criteria['has_inspection_vpc'] = vpcs.get('inspectionVpc', {}).get('enabled', False)
        # Workload VPCs are now at network level
        criteria['has_workload_vpcs'] = section_config.get('workloadVpcs', {}).get('enabled', False)
        # Transit Gateway — presence of tgwArchitecture implies TGW is deployed (no enabled flag)
        criteria['has_transit_gateway'] = bool(tgw_arch.get('transitGateway', {}))
        # Hybrid connectivity is now at network level
        criteria['has_hybrid_connectivity'] = section_config.get('hybridConnectivity', {}).get('enabled', False)
        
        # IPAM criteria
        ipam_config = section_config.get('ipam', {})
        criteria['has_ipam'] = ipam_config.get('enabled', False)
        
        return criteria
    
    def should_use_template_04a(self, section_config: Dict[str, Any]) -> bool:
        """
        Determine if Template 04A (TGW + Egress VPC) should be used.
        
        Template 04A is used when:
        - Transit Gateway is present (tgwArchitecture exists with transitGateway)
        - Inspection VPC is enabled BUT Network Firewall is disabled
        - This provides centralized egress without deep packet inspection
        
        Args:
            section_config: Network section configuration
            
        Returns:
            True if Template 04A should be used, False otherwise
        """
        tgw_arch = section_config.get('tgwArchitecture', {})
        vpcs = tgw_arch.get('vpcs', {})
        
        # Transit Gateway — presence implies deployed (no enabled flag)
        transit_gateway_enabled = bool(tgw_arch.get('transitGateway', {}))
        
        # Check if Inspection VPC is enabled
        inspection_vpc_config = vpcs.get('inspectionVpc', {})
        inspection_vpc_enabled = inspection_vpc_config.get('enabled', False)
        
        # Check if Network Firewall is disabled
        network_firewall_enabled = inspection_vpc_config.get('networkFirewall', False)
        
        # Template 04A: TGW + Egress VPC (Inspection VPC without firewall)
        # Use when TGW and Inspection VPC are enabled, but Network Firewall is disabled
        return transit_gateway_enabled and inspection_vpc_enabled and not network_firewall_enabled
    
    def should_use_template_04b(self, section_config: Dict[str, Any]) -> bool:
        """
        Determine if Template 04B (TGW + Inspection VPC + Network Firewall) should be used.
        
        Template 04B is used when:
        - Transit Gateway is present (tgwArchitecture exists with transitGateway)
        - Inspection VPC is enabled
        - Network Firewall is enabled
        - This provides centralized egress with deep packet inspection
        
        Args:
            section_config: Network section configuration
            
        Returns:
            True if Template 04B should be used, False otherwise
        """
        tgw_arch = section_config.get('tgwArchitecture', {})
        vpcs = tgw_arch.get('vpcs', {})
        
        # Transit Gateway — presence implies deployed (no enabled flag)
        transit_gateway_enabled = bool(tgw_arch.get('transitGateway', {}))
        
        # Check if Inspection VPC is enabled
        inspection_vpc_config = vpcs.get('inspectionVpc', {})
        inspection_vpc_enabled = inspection_vpc_config.get('enabled', False)
        
        # Check if Network Firewall is enabled
        network_firewall_enabled = inspection_vpc_config.get('networkFirewall', False)
        
        # Template 04B: TGW + Inspection VPC + Network Firewall
        # Use when TGW, Inspection VPC, and Network Firewall are all enabled
        return transit_gateway_enabled and inspection_vpc_enabled and network_firewall_enabled
    
    def get_tgw_template_name(self, section_config: Dict[str, Any]) -> Optional[str]:
        """
        Determine which TGW template should be used based on configuration.
        
        Returns the appropriate template name:
        - "04a-tgw-stackset-network-egress-vpc.yaml" for centralized egress without firewall
        - "04b-tgw-stackset-network-inspection-vpc-firewall.yaml" for centralized egress with firewall
        - None if neither template should be used
        
        Args:
            section_config: Network section configuration
            
        Returns:
            Template filename or None
        """
        if self.should_use_template_04b(section_config):
            return "04b-tgw-stackset-network-inspection-vpc-firewall.yaml"
        elif self.should_use_template_04a(section_config):
            return "04a-tgw-stackset-network-egress-vpc.yaml"
        else:
            return None
