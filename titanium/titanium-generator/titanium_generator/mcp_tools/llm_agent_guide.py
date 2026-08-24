"""
LLM Agent Guide Generator for interactive step-by-step deployment.

This module generates interactive deployment guides specifically designed for LLM/GenAI agents
that can execute commands step-by-step with user confirmation and dynamic parameter resolution.
"""

import os
import re
import yaml
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from ..config_parser import TitaniumConfigParser
from ..naming import ssm_slug


class LLMAgentGuideGenerator:
    """
    LLM Agent Guide Generator that creates interactive, step-by-step deployment guides
    for GenAI agents with dynamic parameter resolution and user confirmation prompts.
    """
    
    def __init__(self):
        """Initialize the LLM agent guide generator."""
        self.step_counter = 0
        # Maps a normalized policy name -> its configured target OU names.
        # Populated per guide from the Titanium config; used to turn each
        # u<Policy>Targets parameter into a ready-to-run SSM lookup (issue #75).
        self._policy_targets = {}
    
    def generate_decision_matrix(self, is_control_tower_enabled: bool) -> str:
        """
        Generate decision matrix table showing Config deployment decisions.
        
        Args:
            is_control_tower_enabled: Whether Control Tower is enabled
            
        Returns:
            Markdown table with decision matrix
        """
        matrix = """## AWS Config Deployment Decision Matrix

| Control Tower Enabled | Config Recorder Generated | Config Source | Notes |
|----------------------|---------------------------|---------------|-------|
| Yes | No | Control Tower manages Config in member accounts | Config recorder template skipped to avoid conflicts. Manual Config setup needed for management account if required. |
| No | Yes | Standalone Config recorder deployment | Config recorder template generated for management account. Full Config deployment in all accounts. |

### Decision Logic

The Titanium generator uses the `controlTower.enable` flag in Titanium.yaml to determine whether to generate the Config recorder template:

- **When Control Tower is enabled** (`controlTower.enable: true`):
  - Config recorder template (`0-config-recorder-mgmt.yaml`) is **NOT generated**
  - Reason: Control Tower automatically manages AWS Config in member accounts
  - Note: Control Tower does NOT deploy Config in the management account
  
- **When Control Tower is disabled** (`controlTower.enable: false` or absent):
  - Config recorder template (`0-config-recorder-mgmt.yaml`) **IS generated**
  - Reason: Standalone deployment requires Config recorder in management account
  - Note: Config role template is always generated regardless of Control Tower status

"""
        return matrix
    
    def _generate_control_tower_documentation(self) -> str:
        """Generate Control Tower-specific documentation section."""
        documentation = """## Control Tower and AWS Config Behavior

### How Control Tower Manages AWS Config

AWS Control Tower automatically deploys and manages AWS Config in your landing zone with specific behavior:

#### Member Accounts
- **Automatic Deployment**: Control Tower deploys Config recorder to all member accounts
- **Automatic Management**: Control Tower manages Config settings and updates
- **No Manual Setup**: You should NOT manually deploy Config to member accounts
- **Conflict Prevention**: Deploying Config templates to member accounts will cause conflicts

#### Management Account
- **No Automatic Deployment**: Control Tower does NOT deploy Config recorder to the management account
- **Manual Setup Required**: If you need Config in the management account, you must set it up manually
- **Use Case**: Required for Security Hub organization-wide monitoring in the management account

### AWS Config Recorder Limits

**Important**: AWS Config allows only ONE configuration recorder per region per account.

- If Control Tower has deployed a Config recorder, you cannot deploy another
- Attempting to deploy a second recorder will result in an error
- This is why the Titanium generator skips the Config recorder template when Control Tower is enabled

### Security Hub and AWS Config

Security Hub requires AWS Config to be enabled in accounts where it operates:

- **With Control Tower**: Security Hub works with Control Tower's Config deployment in member accounts
- **Management Account**: If you want Security Hub in the management account, you must manually enable Config there
- **Without Control Tower**: The Titanium generator ensures Config recorder is deployed for Security Hub

### Manual Config Setup for Management Account (Control Tower Enabled)

If you need AWS Config in the management account when Control Tower is enabled:

1. **Enable Config Manually** in the AWS Console:
   - Navigate to AWS Config in your management account
   - Click "Get started" or "Settings"
   - Configure Config recorder with appropriate settings
   - Use the IAM role created by the `01-config-stack-mgmt-role.yaml` template

2. **Or Use AWS CLI**:
   ```bash
   # Create Config recorder
   aws configservice put-configuration-recorder \\
     --configuration-recorder name=default,roleARN=arn:aws:iam::<mgmt-account-id>:role/TitaniumConfigRole \\
     --recording-group allSupported=true,includeGlobalResourceTypes=true
   
   # Create delivery channel
   aws configservice put-delivery-channel \\
     --delivery-channel name=default,s3BucketName=<your-config-bucket>
   
   # Start Config recorder
   aws configservice start-configuration-recorder --configuration-recorder-name default
   ```

"""
        return documentation
    
    def _parse_cloudformation_template(self, template_content: str) -> Dict[str, Any]:
        """
        Parse CloudFormation template with support for intrinsic functions.
        
        This method extracts Parameters and Metadata sections without parsing
        intrinsic functions, which allows us to get parameter definitions and
        deployment metadata even from complex templates.
        
        Args:
            template_content: Raw CloudFormation template content
            
        Returns:
            Dictionary with 'Parameters' and 'Metadata' keys
        """
        import re
        
        result = {'Parameters': {}, 'Metadata': {}}
        
        # Extract Parameters section
        params_match = re.search(
            r'^Parameters:\s*\n((?:(?!^[A-Z][a-zA-Z]*:).*\n)*)',
            template_content,
            re.MULTILINE
        )
        
        if params_match:
            params_section = 'Parameters:\n' + params_match.group(1)
            
            safe_params = params_section
            safe_params = re.sub(r'!Ref \w+', '"REF_PLACEHOLDER"', safe_params)
            safe_params = re.sub(r'!GetAtt [\w.]+', '"GETATT_PLACEHOLDER"', safe_params)
            safe_params = re.sub(r'!Sub .*', '"SUB_PLACEHOLDER"', safe_params)
            safe_params = re.sub(r'!Equals.*', '"EQUALS_PLACEHOLDER"', safe_params)
            safe_params = re.sub(r'!Not.*', '"NOT_PLACEHOLDER"', safe_params)
            safe_params = re.sub(r'!And.*', '"AND_PLACEHOLDER"', safe_params)
            safe_params = re.sub(r'!Or.*', '"OR_PLACEHOLDER"', safe_params)
            safe_params = re.sub(r'!If.*', '"IF_PLACEHOLDER"', safe_params)
            safe_params = re.sub(r'!Join.*', '"JOIN_PLACEHOLDER"', safe_params)
            safe_params = re.sub(r'!Select.*', '"SELECT_PLACEHOLDER"', safe_params)
            
            try:
                parsed = yaml.safe_load(safe_params)
                result['Parameters'] = parsed.get('Parameters', {})
            except Exception as e:
                print(f"Warning: Failed to parse Parameters section: {str(e)}")
        
        # Extract Metadata section (no intrinsic functions expected here)
        metadata_match = re.search(
            r'^Metadata:\s*\n((?:(?!^[A-Z][a-zA-Z]*:).*\n)*)',
            template_content,
            re.MULTILINE
        )
        
        if metadata_match:
            metadata_section = 'Metadata:\n' + metadata_match.group(1)
            try:
                parsed_metadata = yaml.safe_load(metadata_section)
                result['Metadata'] = parsed_metadata.get('Metadata', {})
            except Exception as e:
                print(f"Warning: Failed to parse Metadata section: {str(e)}")
        
        return result
    
    def generate_agent_guide(self, config: Dict[str, Any], 
                           processing_results: Dict[str, Any], 
                           output_dir: str) -> Path:
        """
        Generate interactive LLM agent deployment guide.
        
        Args:
            config: Titanium configuration
            processing_results: Template processing results
            output_dir: Output directory for deployment guide
            
        Returns:
            Path to generated LLM agent guide
        """
        # Extract configuration details
        home_region = self._extract_home_region(config)
        account_mappings = self._extract_account_mappings(config)
        self._policy_targets = self._build_policy_target_map(config)
        
        # Generate interactive steps
        deployment_steps = self._generate_deployment_steps(
            config, processing_results, home_region, account_mappings
        )
        
        # Create the guide content
        guide_content = self._generate_agent_guide_content(
            config, processing_results, deployment_steps, home_region
        )
        
        # Write the guide
        guide_path = Path(output_dir) / 'LLM_AGENT_DEPLOYMENT_GUIDE.md'
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide_content)
        
        # Also generate JSON format for programmatic use
        json_guide = self._generate_json_guide(deployment_steps, config, home_region)
        json_path = Path(output_dir) / 'llm_agent_steps.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_guide, f, indent=2)
        
        return guide_path
    
    def _generate_deployment_steps(self, config: Dict[str, Any], 
                                 processing_results: Dict[str, Any],
                                 home_region: str,
                                 account_mappings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate structured deployment steps for LLM agent execution.
        
        Args:
            config: Titanium configuration
            processing_results: Template processing results
            home_region: Home region
            account_mappings: Account mappings
            
        Returns:
            List of structured deployment steps
        """
        steps = []
        
        # Pre-deployment setup steps
        steps.extend(self._generate_setup_steps(config, home_region))
        
        # Define deployment phases in order
        # 'identity' sits after 'organization' (OUs exist) and before 'security':
        # the org-wide IAM password policy is a foundational control. Its templates
        # are processed into processing_results['identity'] but had no deploy step
        # because this list omitted the phase, leaving the StackSet orphaned (#80).
        phase_order = ['bootstrap', 'controltower', 'organization', 'identity', 'security', 'network', 'finance']
        
        for phase_name in phase_order:
            if phase_name in processing_results and processing_results[phase_name]['templates_processed'] > 0:
                phase_steps = self._generate_phase_steps(
                    phase_name, processing_results[phase_name], 
                    config, home_region, account_mappings
                )
                steps.extend(phase_steps)
        
        # Post-deployment verification steps
        steps.extend(self._generate_verification_steps(config, processing_results))
        
        return steps
    
    def _generate_setup_steps(self, config: Dict[str, Any], home_region: str) -> List[Dict[str, Any]]:
        """Generate pre-deployment setup steps."""
        steps = []
        
        # Step 1: Environment validation
        self.step_counter += 1
        steps.append({
            "step_id": f"setup_{self.step_counter:03d}",
            "phase": "setup",
            "title": "Validate AWS Environment",
            "description": "Verify AWS CLI configuration and account access",
            "agent_instructions": [
                "Ask user to confirm they are logged into the AWS Management Account",
                "Ask user to confirm AWS CLI is configured with appropriate permissions",
                "Ask user to confirm they have Organizations admin permissions"
            ],
            "commands": [
                {
                    "description": "Check AWS identity",
                    "command": "aws sts get-caller-identity",
                    "expected_output": "Should show Management Account ID",
                    "confirmation_prompt": "Please confirm this shows your Management Account ID and you have the correct permissions to proceed."
                }
            ],
            "success_criteria": "User confirms correct account and permissions",
            "failure_actions": ["Stop deployment", "Ask user to configure AWS CLI properly"]
        })
        
        # Step 2: Collect AWS environment parameters
        self.step_counter += 1
        steps.append({
            "step_id": f"setup_{self.step_counter:03d}",
            "phase": "setup",
            "title": "Collect AWS Organization Information",
            "description": "Gather required AWS Organization and account details",
            "agent_instructions": [
                "Execute commands to collect AWS environment information",
                "Ask user to confirm each collected value is correct",
                "Store values for use in subsequent deployment steps"
            ],
            "commands": [
                {
                    "description": "Get Organization ID",
                    "command": "aws organizations describe-organization --query 'Organization.Id' --output text",
                    "store_as": "ORG_ID",
                    "confirmation_prompt": "Is this Organization ID correct? This will be used for all deployments."
                },
                {
                    "description": "Get Root OU ID", 
                    "command": "aws organizations list-roots --query 'Roots[0].Id' --output text",
                    "store_as": "ROOT_OU_ID",
                    "confirmation_prompt": "Is this Root OU ID correct?"
                },
                {
                    "description": "Get Management Account ID",
                    "command": "aws sts get-caller-identity --query 'Account' --output text",
                    "store_as": "MGMT_ACCOUNT_ID",
                    "confirmation_prompt": "Confirm this is your Management Account ID."
                }
            ],
            "success_criteria": "All IDs collected and confirmed by user",
            "failure_actions": ["Retry commands", "Ask user to check AWS configuration"]
        })
        
        # Step 2b: Verify enabledRegions are governed by the Control Tower
        # landing zone. Control Tower is an external prerequisite, so the advisor
        # cannot validate this at interview time (issue #109). Here at deploy
        # time CT is reachable, so verify BEFORE any org-wide SERVICE_MANAGED
        # StackSet runs: those cannot deploy to a region CT does not govern, and
        # such instances fail in the ungoverned region.
        enabled_regions = config.get('enabledRegions', [])
        if enabled_regions:
            regions_str = ", ".join(enabled_regions) if isinstance(enabled_regions, list) else str(enabled_regions)
            self.step_counter += 1
            steps.append({
                "step_id": f"setup_{self.step_counter:03d}",
                "phase": "setup",
                "title": "Verify Regions Are Governed by Control Tower",
                "description": (
                    f"Your configuration enables these regions: {regions_str}. Control Tower is a "
                    "prerequisite and governs which regions org-wide StackSets can deploy to. Confirm "
                    "every enabled region is in the landing zone's governedRegions BEFORE deploying, "
                    "so multi-region StackSets (e.g. EBS default encryption) do not fail in an "
                    "ungoverned region."
                ),
                "agent_instructions": [
                    "Resolve the landing zone identifier, then read its governed regions",
                    f"Compare the governed regions against the enabled regions: {regions_str}",
                    "If any enabled region is NOT governed, STOP and tell the user to either remove "
                    "that region from Titanium.yaml enabledRegions (and the LimitRegionUsage SCP) or "
                    "extend the Control Tower landing zone to govern it before deploying"
                ],
                "commands": [
                    {
                        "description": "Get the Control Tower landing zone ARN",
                        "command": "aws controltower list-landing-zones --query 'landingZones[0].arn' --output text",
                        "store_as": "LANDING_ZONE_ARN",
                        "expected_output": "The landing zone ARN (empty/None means Control Tower is not set up — a prerequisite)"
                    },
                    {
                        "description": "Read the regions the landing zone governs",
                        "command": "aws controltower get-landing-zone --landing-zone-identifier \"$LANDING_ZONE_ARN\" --query 'landingZone.manifest.governedRegions' --output json",
                        "store_as": "GOVERNED_REGIONS",
                        "expected_output": f"A JSON array of governed regions; it must be a superset of: {regions_str}",
                        "confirmation_prompt": f"Confirm every enabled region ({regions_str}) appears in the governed regions above before continuing."
                    }
                ],
                "manual_steps": [
                    "Alternatively: AWS Control Tower console -> Landing zone settings -> Region table",
                    f"Confirm each of these enabled regions is governed: {regions_str}",
                    "If a region is not governed: remove it from enabledRegions (and the LimitRegionUsage "
                    "SCP) in Titanium.yaml and regenerate, or update the Control Tower landing zone to "
                    "govern it"
                ],
                "success_criteria": "Every enabledRegions entry is present in the landing zone's governedRegions",
                "failure_actions": [
                    "Stop deployment before org-wide StackSets run",
                    "Reconcile enabledRegions with the Control Tower governed regions"
                ]
            })

        # Step 3: Collect account-specific IDs
        self.step_counter += 1
        steps.append({
            "step_id": f"setup_{self.step_counter:03d}",
            "phase": "setup",
            "title": "Collect Specialized Account IDs",
            "description": "Identify existing specialized accounts (Audit, Log Archive, Network)",
            "agent_instructions": [
                "Try to identify specialized accounts that may already exist",
                "Ask user to confirm if accounts exist or if they should be created later",
                "Store account IDs if they exist, or mark as 'TO_BE_CREATED'"
            ],
            "commands": [
                {
                    "description": "Look for Audit account",
                    "command": "aws organizations list-accounts --query 'Accounts[?Name==`Audit`].Id' --output text",
                    "store_as": "AUDIT_ACCOUNT_ID",
                    "confirmation_prompt": "If an account ID was returned, confirm this is your Audit account. If empty, confirm you want to create an Audit account later."
                },
                {
                    "description": "Look for Log Archive account",
                    "command": "aws organizations list-accounts --query 'Accounts[?Name==`Log Archive`].Id' --output text", 
                    "store_as": "LOGARCHIVE_ACCOUNT_ID",
                    "confirmation_prompt": "If an account ID was returned, confirm this is your Log Archive account. If empty, confirm you want to create a Log Archive account later."
                },
                {
                    "description": "Look for Network account",
                    "command": "aws organizations list-accounts --query 'Accounts[?(Name==`Network` || Name==`Networking`)].Id' --output text",
                    "store_as": "NETWORK_ACCOUNT_ID", 
                    "confirmation_prompt": "If an account ID was returned, confirm this is your Network account. If empty, confirm you want to create a Network account later."
                }
            ],
            "success_criteria": "Account IDs identified or marked for creation",
            "failure_actions": ["Continue with deployment", "Accounts will be created as needed"]
        })
        
        return steps
    
    def _generate_phase_steps(self, phase_name: str, phase_data: Dict[str, Any],
                            config: Dict[str, Any], home_region: str,
                            account_mappings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate steps for a specific deployment phase."""
        steps = []
        
        phase_description = self._get_phase_description(phase_name)
        
        # Get files and filter out non-existent templates
        files = phase_data.get('files', [])
        
        # Filter to only include files that actually exist
        existing_files = []
        for file_info in files:
            template_path = file_info.get('output_path', '')
            if os.path.exists(template_path):
                existing_files.append(file_info)
            else:
                print(f"Warning: Template {file_info.get('name')} not found at {template_path}, skipping")
        
        # Sort files by numeric prefix in filename
        # Extract number from filenames like "01-template.yaml", "04a-template.yaml", "04b-template.yaml"
        def get_sort_key(file_info):
            name = file_info.get('name', '')
            # Extract leading digits and optional letter (e.g., "01", "04a", "04b")
            import re
            match = re.match(r'^(\d+)([a-z]?)', name)
            if match:
                number = int(match.group(1))
                letter = match.group(2) or ''
                return (number, letter)
            return (999, '')  # Put files without numeric prefix at end
        
        sorted_files = sorted(existing_files, key=get_sort_key)
        
        # Determine if Control Tower is enabled (needed for OU enrollment injection)
        is_control_tower_enabled = TitaniumConfigParser.get_control_tower_enabled(config)
        
        # Track whether we need to inject OU enrollment step (between template 01 and 02 in organization phase)
        ou_enrollment_injected = False
        # Track whether we injected the Access Analyzer delegation gate (before template 10 in security phase)
        accessanalyzer_gate_injected = False

        # Generate steps for each template in sorted order
        for file_info in sorted_files:
            template_name = file_info.get('name', '')

            # Verify Control Tower OU enrollment between OUs (01) and SCPs (02) in the
            # organization phase when Control Tower is enabled. Enrollment itself is
            # performed by template 01's discovery Lambda (adopt-or-enable), so this
            # is a gate rather than an action: SCPs attached to an unenrolled OU are
            # not enforced by the landing zone.
            if (phase_name == 'organization' and is_control_tower_enabled
                    and not ou_enrollment_injected and template_name.startswith('02')):
                enrollment_step = self._generate_ou_enrollment_verification_step(config, home_region)
                steps.append(enrollment_step)
                ou_enrollment_injected = True

            # Verify the Access Analyzer delegated admin (registered by template 09)
            # is active before the organization analyzer StackSet (template 10) runs.
            # Registration is eventually consistent; template 10 fails with "not a
            # delegated administrator" if it races an un-propagated 09 (issue #104).
            if (phase_name == 'security' and not accessanalyzer_gate_injected
                    and template_name.startswith('10-accessanalyzer')):
                gate_step = self._generate_accessanalyzer_delegation_gate_step(config, home_region)
                steps.append(gate_step)
                accessanalyzer_gate_injected = True

            template_steps = self._generate_template_steps(
                file_info, phase_name, config, home_region, account_mappings
            )
            steps.extend(template_steps)
        
        return steps
    
    def _generate_ou_enrollment_verification_step(self, config: Dict[str, Any], home_region: str) -> Dict[str, Any]:
        """
        Generate the Control Tower OU enrollment verification step.

        Enrollment is performed by template 01's discovery Lambda, which adopts an
        already-enrolled OU and otherwise fires EnableBaseline without waiting for it
        to finish (issue #91). Because that enrollment is asynchronous and
        best-effort, this gate matters more, not less: it must pass before SCP
        deployment (template 02), because policies attached to an OU that Control
        Tower has not baselined are not enforced by the landing zone.

        Key constraints:
        - The hub OU is governed by the landing zone directly and is not enrolled here
        - Baseline version 5.0 is required for landing zone v4.0
        - Enrollment can still be IN_PROGRESS (or not yet started, if Control Tower
          rejected a concurrent operation) when the template 01 stack completes;
          re-running template 01 is idempotent and re-attempts any missing OU
        """
        self.step_counter += 1

        # OUs the solution creates and enrolls. The hub OU is declared in the Control
        # Tower manifest and governed by the landing zone, so it is not in this list.
        # Path and shape must match controltower_processor, which derives the hub OU
        # name from controlTower.landingZone.organizationStructure.security.name. Note
        # the capital T and the landingZone nesting; reading 'controltower' yields {}
        # and silently falls through to the default.
        landing_zone = config.get('controlTower', {}).get('landingZone', {}) or {}
        org_structure = landing_zone.get('organizationStructure', {}) or {}
        if isinstance(org_structure, str):
            hub_ou_name = org_structure
        else:
            security_struct = org_structure.get('security', {}) or {}
            hub_ou_name = (security_struct.get('name', 'Security')
                           if isinstance(security_struct, dict) else 'Security')
        ous_enrolled = []
        org_config = config.get('organization', {})
        for ou in org_config.get('organizationalUnits', []):
            ou_name = ou if isinstance(ou, str) else ou.get('name', '')
            if ou_name and ou_name != hub_ou_name and ou_name not in ous_enrolled:
                ous_enrolled.append(ou_name)

        if not ous_enrolled:
            ous_enrolled = ['Infrastructure', 'Workloads', 'Sandbox']

        ou_list = ', '.join(ous_enrolled)

        return {
            "step_id": f"org_{self.step_counter:03d}",
            "phase": "organization",
            "title": "Verify Control Tower OU enrollment (GATE)",
            "description": (
                "Confirm every OU provisioned by template 01 reached baseline status "
                "SUCCEEDED. Enrollment is performed by template 01's discovery Lambda "
                "(adopt-or-enable), asynchronously, not by hand. This is a gate before "
                "SCP deployment: an SCP attached to an unenrolled OU is not enforced by "
                "the landing zone."
            ),
            "agent_instructions": [
                "Do NOT run enable-baseline by hand. Template 01's discovery Lambda "
                "enrolls these OUs (adopting any that are already enrolled); calling "
                "enable-baseline on an already-enrolled OU fails.",
                f"OUs expected to be enrolled: {ou_list}",
                f"The hub OU '{hub_ou_name}' is governed by the landing zone directly and is "
                "not expected in this list.",
                "Enrollment is asynchronous: an OU may still be IN_PROGRESS, or (if Control "
                "Tower rejected a concurrent baseline operation) not yet started, when the "
                "stack completes. If an OU is missing or not SUCCEEDED, re-run template 01 "
                "(it is idempotent and re-attempts missing OUs) rather than enrolling "
                "manually; inspect the discovery Lambda's CloudWatch logs for the reason.",
            ],
            "commands": [
                {
                    "description": "List enrolled baselines and their status",
                    "command": (
                        "aws controltower list-enabled-baselines "
                        f"--region {home_region} "
                        "--query 'enabledBaselines[].{Target:targetIdentifier,"
                        "Status:statusSummary.status}' --output table"
                    ),
                    "confirmation_prompt": (
                        f"Confirm the OUs ({ou_list}) appear with status SUCCEEDED."
                    ),
                },
                {
                    "description": "Confirm the OU IDs were published to SSM for template 02",
                    "command": (
                        "aws ssm get-parameters-by-path "
                        "--path '/titanium/organization/ou-ids' --recursive "
                        f"--region {home_region} "
                        "--query 'Parameters[].{Name:Name,Value:Value}' --output table"
                    ),
                    "confirmation_prompt": (
                        "Confirm one <ou-name>-ou-id parameter exists per OU. Template 02 "
                        "resolves its deployment targets from these."
                    ),
                },
            ],
            "success_criteria": (
                f"Every OU ({ou_list}) shows baseline status SUCCEEDED and has a "
                "corresponding SSM parameter under /titanium/organization/ou-ids"
            ),
            "failure_actions": [
                "If an OU is absent from list-enabled-baselines: its EnableBaseline may not "
                "have started (Control Tower rejects concurrent baseline operations). Re-run "
                "template 01 — it adopts already-enrolled OUs and re-attempts the rest — then "
                "re-check. Confirm organization.organizationalUnits lists the OU.",
                "If status is FAILED: read the reason in the template 01 discovery Lambda's "
                "CloudWatch logs (log group /aws/lambda/<stack-name>-OrgDiscovery)",
                "If status is IN_PROGRESS: wait and re-check; enrollment is asynchronous",
                "Check enrollment status: aws controltower list-enabled-baselines --region "
                + home_region,
            ],
        }

    def _generate_accessanalyzer_delegation_gate_step(self, config: Dict[str, Any], home_region: str) -> Dict[str, Any]:
        """
        Generate the Access Analyzer delegated-admin verification step (GATE).

        Template 09 registers the Audit account as the Access Analyzer delegated
        administrator via organizations:RegisterDelegatedAdministrator; template 10
        then creates the ORGANIZATION analyzer in that account. The registration is
        eventually consistent, so template 10 fails with "Account <audit> is not a
        delegated administrator" if it runs before 09 propagates (issue #104).

        Template 09's Lambda now polls for propagation before completing, so a
        straight-through run usually succeeds; this gate is the belt-and-suspenders
        for an agent driving the guide quickly, mirroring the org Step-13 enrollment
        gate.
        """
        self.step_counter += 1
        return {
            "step_id": f"security_{self.step_counter:03d}",
            "phase": "security",
            "title": "Verify Access Analyzer delegated admin is active (GATE)",
            "description": (
                "Confirm the Audit account is registered as the Access Analyzer "
                "delegated administrator (from template 09) before deploying the "
                "organization analyzer StackSet (template 10). Registration is "
                "asynchronous; template 10 fails with 'not a delegated administrator' "
                "if it runs before propagation completes."
            ),
            "agent_instructions": [
                "Do NOT register the delegated admin by hand — template 09 does this.",
                "This is a propagation gate: only proceed to template 10 once the "
                "Audit account appears as an ACTIVE delegated administrator for "
                "access-analyzer.amazonaws.com.",
                "If it is not yet listed, wait ~30s and re-check; registration is "
                "eventually consistent.",
            ],
            "commands": [
                {
                    "description": "List Access Analyzer delegated administrators",
                    "command": (
                        "aws organizations list-delegated-administrators "
                        "--service-principal access-analyzer.amazonaws.com "
                        "--query 'DelegatedAdministrators[].{Id:Id,Status:Status}' --output table"
                    ),
                    "confirmation_prompt": (
                        "Confirm the Audit account appears with Status ACTIVE before deploying template 10."
                    ),
                },
            ],
            "success_criteria": (
                "The Audit account is listed as an ACTIVE delegated administrator for "
                "access-analyzer.amazonaws.com"
            ),
            "failure_actions": [
                "If the account is not listed: wait ~30s and re-check — template 09's "
                "registration is still propagating.",
                "If it is still missing after a few minutes: re-run template 09 (it is "
                "idempotent) and inspect its Lambda's CloudWatch logs "
                "(/aws/lambda/titanium-accessanalyzer-delegation).",
                "If template 10 already failed with 'not a delegated administrator': wait "
                "until this gate passes, then re-deploy template 10.",
            ],
        }

    def _generate_template_steps(self, file_info: Dict[str, Any], phase_name: str,
                               config: Dict[str, Any], home_region: str,
                               account_mappings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate steps for deploying a specific template."""
        steps = []
        
        template_name = file_info['name']
        template_path = file_info['output_path']
        
        # Analyze template for parameters
        try:
            with open(template_path, 'r') as f:
                template_content = f.read()
            
            # Use custom YAML loader that handles CloudFormation intrinsic functions
            template_data = self._parse_cloudformation_template(template_content)
            parameters = template_data.get('Parameters', {})
            metadata = template_data.get('Metadata', {})
            
            # Extract u-parameters that need user input
            u_parameters = self._extract_u_parameters(parameters, config, phase_name)
            
        except Exception as e:
            # Log error but continue with empty parameters
            print(f"Warning: Failed to parse template {template_name}: {str(e)}")
            u_parameters = {}
            metadata = {}
        
        # Step 1: Parameter resolution (if needed)
        if u_parameters:
            self.step_counter += 1
            param_step = self._generate_parameter_resolution_step(
                template_name, u_parameters, phase_name
            )
            steps.append(param_step)
        
        # Step 2: Template deployment
        self.step_counter += 1
        deploy_step = self._generate_deployment_step(
            template_name, file_info, phase_name, home_region, 
            account_mappings, u_parameters, metadata
        )
        steps.append(deploy_step)
        
        # Step 3: Deployment verification
        self.step_counter += 1
        verify_step = self._generate_template_verification_step(
            template_name, phase_name, home_region
        )
        steps.append(verify_step)
        
        return steps
    
    def _generate_parameter_resolution_step(self, template_name: str, 
                                          u_parameters: Dict[str, Any],
                                          phase_name: str) -> Dict[str, Any]:
        """Generate step for resolving u-parameters with user input."""
        
        parameter_prompts = []
        for param_name, param_info in u_parameters.items():
            prompt_info = self._generate_parameter_prompt(param_name, param_info, phase_name)
            parameter_prompts.append(prompt_info)
        
        return {
            "step_id": f"{phase_name}_{self.step_counter:03d}",
            "phase": phase_name,
            "title": f"Resolve Parameters for {template_name}",
            "description": f"Collect required parameter values for {template_name} deployment",
            "agent_instructions": [
                f"The template {template_name} requires {len(u_parameters)} parameter(s) that need user input",
                "Ask the user to provide or confirm each parameter value",
                "Validate parameter formats where specified",
                "Store resolved parameters for use in deployment command"
            ],
            "parameter_prompts": parameter_prompts,
            "success_criteria": "All required parameters collected and validated",
            "failure_actions": ["Ask user to provide missing parameters", "Validate parameter formats"]
        }
    
    # GuardDuty allows one detector per account/region, and org-auto-enabled
    # detectors survive stack deletion, so a create fails with AlreadyExists on a
    # non-greenfield account. The template stays a plain detector; this pre-flight
    # lets the agent skip the stack when a detector already exists (issue #89).
    _GUARDDUTY_DETECTOR_TEMPLATE = "03-guardduty-stackset-audit-detector.yaml"

    def _preflight_check(self, template_name: str, home_region: str) -> Optional[Dict[str, Any]]:
        """Return a pre-flight command that lets the agent skip a template when
        its resource already exists, or None.

        Deployment assumes a greenfield account; this only adds a graceful skip so
        a re-run or an SRA/Control-Tower-managed account that already has the
        resource does not hard-fail (issue #89).
        """
        if template_name == self._GUARDDUTY_DETECTOR_TEMPLATE:
            return {
                "description": "Pre-flight: check for an existing GuardDuty detector in the Audit account",
                "command": f"aws guardduty list-detectors --region {home_region} --query 'DetectorIds' --output text",
                "expected_output": "Empty on a greenfield account; a detector ID if GuardDuty is already enabled (Control Tower / SRA / a prior run)",
                "skip_guidance": (
                    "Run this in the Audit account first. If it returns a detector ID, GuardDuty is "
                    "already enabled — SKIP this stack; deploying it would fail with 'a detector "
                    "already exists for the current account'. If it returns nothing, proceed."
                ),
                "confirmation_prompt": "Did the pre-flight return a detector ID? If yes, skip this stack; if no, proceed with deployment.",
            }
        return None

    def _generate_deployment_step(self, template_name: str, file_info: Dict[str, Any],
                                phase_name: str, home_region: str,
                                account_mappings: Dict[str, Any],
                                u_parameters: Dict[str, Any],
                                template_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate deployment step for a template."""
        
        if template_metadata is None:
            template_metadata = {}
        
        stack_name = f"Titanium-{template_name.replace('.yaml', '')}"
        # Use pathlib so this works on Windows (backslash) paths too — a raw
        # split('/') would return a single element and IndexError (#67).
        section = Path(file_info['output_path']).parent.name
        
        # Determine if this is a management account stack or StackSet
        is_mgmt_only = self._is_management_account_only(template_name)
        
        if is_mgmt_only:
            command_info = self._generate_stack_command_info(
                stack_name, section, template_name, home_region, u_parameters
            )
        else:
            command_info = self._generate_stackset_command_info(
                stack_name, section, template_name, phase_name,
                home_region, account_mappings, u_parameters, template_metadata
            )

        commands = command_info['commands']
        agent_instructions = [
            f"Ready to deploy {template_name}",
            "Ask user for final confirmation before executing deployment",
            "Execute the deployment command",
            "Monitor deployment progress"
        ]

        # Some resources can't be created over pre-existing state (e.g. only one
        # GuardDuty detector per account/region). Rather than add adopt-or-create
        # custom resources, prepend a pre-flight check that lets the agent skip
        # the stack when the resource already exists (issue #89).
        preflight = self._preflight_check(template_name, home_region)
        if preflight:
            commands = [preflight] + commands
            agent_instructions = [
                "Run the pre-flight check first.",
                preflight["skip_guidance"],
            ] + agent_instructions

        return {
            "step_id": f"{phase_name}_{self.step_counter:03d}",
            "phase": phase_name,
            "title": f"Deploy {template_name.replace('.yaml', '').replace('-', ' ').title()}",
            "description": command_info['description'],
            "agent_instructions": agent_instructions,
            "deployment_type": "stack" if is_mgmt_only else "stackset",
            "commands": commands,
            "confirmation_prompt": f"Ready to deploy {template_name}? This will {command_info['description'].lower()}. Proceed with deployment? (yes/no)",
            "success_criteria": command_info['success_criteria'],
            "failure_actions": [
                "Check CloudFormation console for error details",
                "Verify parameters are correct",
                "Check AWS permissions",
                "Ask user if they want to retry or skip this template"
            ]
        }
    
    def _generate_template_verification_step(self, template_name: str, 
                                           phase_name: str, 
                                           home_region: str) -> Dict[str, Any]:
        """Generate verification step for a deployed template."""
        
        stack_name = f"Titanium-{template_name.replace('.yaml', '')}"
        is_mgmt_only = self._is_management_account_only(template_name)
        
        if is_mgmt_only:
            verify_commands = [
                {
                    "description": "Check stack status",
                    "command": f"aws cloudformation describe-stacks --stack-name {stack_name} --region {home_region} --query 'Stacks[0].StackStatus' --output text",
                    "expected_output": "CREATE_COMPLETE or UPDATE_COMPLETE"
                }
            ]
        else:
            verify_commands = [
                {
                    "description": "Check StackSet status",
                    "command": f"aws cloudformation describe-stack-set --stack-set-name {stack_name} --query 'StackSet.Status' --output text",
                    "expected_output": "ACTIVE"
                },
                {
                    "description": "Check stack instances",
                    "command": f"aws cloudformation list-stack-instances --stack-set-name {stack_name} --query 'Summaries[].Status' --output text",
                    "expected_output": "All instances should show CURRENT"
                }
            ]
        
        return {
            "step_id": f"{phase_name}_{self.step_counter:03d}",
            "phase": phase_name,
            "title": f"Verify {template_name} Deployment",
            "description": f"Confirm {template_name} deployed successfully",
            "agent_instructions": [
                "Execute verification commands to check deployment status",
                "Report status to user",
                "If deployment failed, provide troubleshooting guidance"
            ],
            "commands": verify_commands,
            "success_criteria": "All verification commands show successful deployment",
            "failure_actions": [
                "Check CloudFormation console for detailed error information",
                "Ask user if they want to retry deployment or continue with next step"
            ]
        }
    
    def _generate_verification_steps(self, config: Dict[str, Any], 
                                   processing_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate post-deployment verification steps."""
        steps = []
        
        # Overall deployment verification
        self.step_counter += 1
        steps.append({
            "step_id": f"verify_{self.step_counter:03d}",
            "phase": "verification",
            "title": "Overall Deployment Verification",
            "description": "Verify all components deployed successfully",
            "agent_instructions": [
                "Execute comprehensive verification commands",
                "Report overall deployment status to user",
                "Provide summary of what was deployed"
            ],
            "commands": [
                {
                    "description": "List all stacks",
                    "command": "aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query 'StackSummaries[?starts_with(StackName, `Titanium-`)].{Name:StackName,Status:StackStatus}' --output table",
                    "expected_output": "All Titanium stacks should show CREATE_COMPLETE"
                },
                {
                    "description": "List all StackSets", 
                    "command": "aws cloudformation list-stack-sets --query 'Summaries[?starts_with(StackSetName, `Titanium-`)].{Name:StackSetName,Status:Status}' --output table",
                    "expected_output": "All Titanium StackSets should show ACTIVE"
                }
            ],
            "success_criteria": "All stacks and StackSets show successful status",
            "failure_actions": ["Provide detailed troubleshooting guidance"]
        })
        
        # Region restriction guidance (if enabledRegions is configured)
        enabled_regions = config.get('enabledRegions', [])
        if enabled_regions:
            regions_str = ", ".join(enabled_regions) if isinstance(enabled_regions, list) else str(enabled_regions)
            self.step_counter += 1
            steps.append({
                "step_id": f"verify_{self.step_counter:03d}",
                "phase": "post-deployment",
                "title": "Post-Deployment: Region Restriction",
                "description": (
                    "Region restriction is enforced through AWS Control Tower's Region Deny control — "
                    "a separate SCP is not required. Verify that Region Deny is enabled in your "
                    "Control Tower landing zone settings for all regions outside your allowed list."
                ),
                "agent_instructions": [
                    f"Inform user that their allowed regions are: {regions_str}",
                    "Instruct user to verify Region Deny is enabled in Control Tower",
                    "If Control Tower is not used, advise using tDeployLimitRegionUsage parameter in the Organization SCP StackSet"
                ],
                "manual_steps": [
                    "Open the AWS Control Tower console → Landing zone settings",
                    "Confirm 'Region deny setting' is set to 'Enabled'",
                    f"Confirm the governed regions match your Titanium.yaml enabledRegions list: {regions_str}",
                    "If Control Tower is not used, you can manually create an SCP using the tDeployLimitRegionUsage parameter in the Organization SCP StackSet"
                ],
                "success_criteria": "Region Deny is enabled and governed regions match configuration",
                "failure_actions": ["Guide user through Control Tower Region Deny setup"]
            })
        
        return steps
    
    def _extract_u_parameters(self, parameters: Dict[str, Any], 
                            config: Dict[str, Any], 
                            section_name: str) -> Dict[str, Any]:
        """Extract parameters that need user input (u-parameters).
        
        This method identifies parameters that require user input at deployment time.
        It excludes:
        - t-prefixed parameters (Titanium-set, derived from Titanium.yaml)
        - Parameters with default values that don't need user input
        - VPC CIDR parameters when IPAM is enabled (IPAM handles CIDR allocation)
        
        New t-prefixed parameters include:
        - tAllSupported, tIncludeGlobalResourceTypes, tFrequency, tResourceTypes (AWS Config)
        - tEnableAFSBPStandard, tEnableCIS12Standard, etc. (Security Hub standards)
        """
        u_parameters = {}
        
        # Check if IPAM is enabled in the Titanium config
        ipam_enabled = False
        network_config = config.get('network', {})
        ipam_config = network_config.get('ipam', {})
        if isinstance(ipam_config, dict):
            ipam_enabled = ipam_config.get('enabled', False)
        
        # VPC CIDR parameters that are not needed when IPAM is enabled
        ipam_managed_cidr_params = {
            'uInspectionVpcCidr', 'uEndpointVpcCidr', 'uWorkloadVpcCidr',
            'uDNSResolverVpcCidr', 'uEgressVpcCidr',
        }
        
        for param_name, param_config in parameters.items():
            # Skip t-prefixed parameters - these are Titanium-set and don't need user input
            if param_name.startswith('t'):
                continue
            
            # Only include u-prefixed parameters that need user input
            if param_name.startswith('u'):
                # Skip VPC CIDR parameters when IPAM is enabled
                if ipam_enabled and param_name in ipam_managed_cidr_params:
                    continue
                
                # Try to auto-resolve some common parameters
                auto_resolved = self._try_auto_resolve_parameter(param_name, param_config, config, section_name)
                
                if not auto_resolved:
                    u_parameters[param_name] = param_config
        
        return u_parameters
    
    def _try_auto_resolve_parameter(self, param_name: str, param_info: Dict[str, Any],
                                  config: Dict[str, Any], section_name: str) -> bool:
        """Try to auto-resolve parameter from config or environment.
        
        Note: This only auto-resolves parameters that have defaults in the template
        or config. Parameters that need user input (even if we can suggest values)
        should NOT be auto-resolved so they appear in the CloudFormation commands.
        """
        # Only auto-resolve if parameter has a default value in the template
        return bool(param_info.get('Default'))
    
    def _generate_parameter_prompt(self, param_name: str, param_info: Dict[str, Any],
                                 phase_name: str) -> Dict[str, Any]:
        """Generate user prompt for a specific parameter."""
        
        param_type = param_info.get('Type', 'String')
        description = param_info.get('Description', f'Parameter {param_name}')
        
        # Generate context-aware prompts
        if param_name.endswith('AccountId'):
            if 'Network' in param_name:
                prompt = f"Please provide the Network Account ID for {param_name}. This should be a 12-digit AWS account ID where network resources will be deployed."
                suggested_value = "${NETWORK_ACCOUNT_ID}"
            elif 'Audit' in param_name or 'Security' in param_name:
                prompt = f"Please provide the Audit/Security Account ID for {param_name}. This should be a 12-digit AWS account ID for security monitoring."
                suggested_value = "${AUDIT_ACCOUNT_ID}"
            elif 'LogArchive' in param_name or 'Logging' in param_name:
                prompt = f"Please provide the Log Archive Account ID for {param_name}. This should be a 12-digit AWS account ID for log storage."
                suggested_value = "${LOGARCHIVE_ACCOUNT_ID}"
            else:
                prompt = f"Please provide the Account ID for {param_name}. This should be a 12-digit AWS account ID."
                suggested_value = "${MGMT_ACCOUNT_ID}"
            
            validation = "Must be a 12-digit number"
            
        elif param_name.endswith('BucketName'):
            prompt = f"Please provide or confirm the S3 bucket name for {param_name}. {description}"
            suggested_value = self._generate_bucket_name_suggestion(param_name)
            validation = "Must be a valid S3 bucket name (lowercase, no spaces)"
            
        elif param_name.endswith('RootId'):
            prompt = f"Please provide the AWS Organization Root ID for {param_name} (e.g. r-abcd). Get it with: aws organizations list-roots --query 'Roots[0].Id' --output text"
            suggested_value = "${ROOT_OU_ID}"
            validation = "Must be an organization root ID (r-xxxx)"

        elif 'Organization' in param_name:
            if 'Unit' in param_name:
                prompt = f"Please provide the Organizational Unit ID for {param_name}. You can use the Root OU ID if deploying organization-wide."
                suggested_value = "${ROOT_OU_ID}"
            else:
                prompt = f"Please provide the Organization ID for {param_name}."
                suggested_value = "${ORG_ID}"
            validation = "Must be a valid AWS Organizations ID"
            
        else:
            prompt = f"Please provide a value for {param_name}. {description}"
            suggested_value = None
            validation = f"Must be a valid {param_type}"
        
        return {
            "parameter_name": param_name,
            "parameter_type": param_type,
            "description": description,
            "prompt": prompt,
            "suggested_value": suggested_value,
            "validation": validation,
            "required": True
        }
    
    def _generate_live_parameter_prompt(self, param_name: str, param_info: Dict[str, Any]) -> str:
        """Generate a live prompt for parameter collection during deployment."""
        
        param_type = param_info.get('Type', 'String')
        description = param_info.get('Description', f'Parameter {param_name}')
        
        # Generate context-aware prompts for live collection
        if param_name.endswith('AccountId'):
            if 'Network' in param_name:
                return f"Please provide the Network Account ID for {param_name}. This should be a 12-digit AWS account ID where network resources will be deployed."
            elif 'Audit' in param_name or 'Security' in param_name:
                return f"Please provide the Audit/Security Account ID for {param_name}. This should be a 12-digit AWS account ID for security monitoring."
            elif 'LogArchive' in param_name or 'Logging' in param_name:
                return f"Please provide the Log Archive Account ID for {param_name}. This should be a 12-digit AWS account ID for log storage."
            else:
                return f"Please provide the Account ID for {param_name}. This should be a 12-digit AWS account ID."
                
        elif param_name.endswith('BucketName'):
            suggestion = self._generate_bucket_name_suggestion(param_name)
            return f"Please provide or confirm the S3 bucket name for {param_name}. {description}."
            
        elif param_name.startswith('u') and param_name.endswith('Targets'):
            stem = param_name[1:-len('Targets')]
            targets = self._policy_targets.get(self._normalize_policy_key(stem))
            if targets:
                ou_list = ", ".join(targets)
                return (
                    f"{param_name}: the organizational units this policy attaches to. "
                    f"Per your configuration these are: {ou_list}. The deploy command "
                    f"already resolves each to its OU ID at run time from SSM "
                    f"({self.OU_ID_SSM_PREFIX}/<ou>-ou-id, Root from .../root-id), so no "
                    f"manual input is needed — just confirm the OU list is correct."
                )
            return (
                f"Please provide the target OU IDs for {param_name} as a comma-separated "
                f"list. Look them up from SSM under {self.OU_ID_SSM_PREFIX}/."
            )

        elif param_name.endswith('RootId'):
            return f"Please provide the AWS Organization Root ID for {param_name} (e.g. r-abcd). You can get this by running: aws organizations list-roots --query 'Roots[0].Id' --output text"

        elif 'Organization' in param_name:
            if 'Unit' in param_name:
                return f"Please provide the Organizational Unit ID for {param_name}. You can get this by running: aws organizations list-roots --query 'Roots[0].Id' --output text"
            else:
                return f"Please provide the Organization ID for {param_name}. You can get this by running: aws organizations describe-organization --query 'Organization.Id' --output text"

        else:
            return f"Please provide a value for {param_name}. {description} (Type: {param_type})"
    
    def _generate_bucket_name_suggestion(self, param_name: str) -> str:
        """Generate suggested bucket name."""
        if 'VPCFlowLogs' in param_name:
            return "titanium-vpc-flow-logs-<LOGARCHIVE_ACCOUNT_ID>-<REGION>"
        elif 'AccessLogs' in param_name:
            return "aws-accelerator-s3-access-logs-<LOGARCHIVE_ACCOUNT_ID>-<REGION>"
        else:
            return f"titanium-{param_name.lower().replace('bucketname', '')}-<ACCOUNT_ID>-<REGION>"
    
    # SSM path prefix under which template 01 publishes each OU's ID
    # (/titanium/organization/ou-ids/<slug>-ou-id, root at .../root-id).
    OU_ID_SSM_PREFIX = "/titanium/organization/ou-ids"

    @staticmethod
    def _ou_ssm_slug(ou_name: str) -> str:
        """Slug an OU name into its SSM path segment.

        Delegates to the shared ``ssm_slug`` helper so these paths stay
        byte-identical to the ones SimpleOrganizationProcessor publishes.
        """
        return ssm_slug(ou_name)

    @staticmethod
    def _normalize_policy_key(name: str) -> str:
        """Normalize a policy name for matching config names to template params.

        Tolerates the singular/plural drift between advisor policy names and
        template parameter stems (e.g. 'DailyBackups' vs 'uDailyBackupTargets').
        """
        return re.sub(r"[^a-z0-9]", "", name.lower()).rstrip("s")

    def _build_policy_target_map(self, config: Dict[str, Any]) -> Dict[str, list]:
        """Map normalized policy name -> its configured target OU names."""
        org = config.get("organization", {}) or {}
        mapping = {}
        for key in ("serviceControlPolicies", "taggingPolicies", "backupPolicies"):
            for policy in org.get(key, []) or []:
                name = policy.get("name")
                if not name:
                    continue
                targets = (policy.get("deploymentTargets", {}) or {}).get(
                    "organizationalUnits", []
                ) or []
                mapping[self._normalize_policy_key(name)] = targets
        return mapping

    def _resolve_targets_param_value(self, param_name: str):
        """Ready-to-run --parameters value for a u<Policy>Targets parameter.

        Resolves each configured target OU to its ID at deploy time via SSM
        (Root -> .../root-id). Returns None when the parameter isn't a policy
        targets parameter or the policy has no configured targets, in which case
        the caller falls back to a manual placeholder.
        """
        if not (param_name.startswith("u") and param_name.endswith("Targets")):
            return None
        stem = param_name[1:-len("Targets")]
        targets = self._policy_targets.get(self._normalize_policy_key(stem))
        if not targets:
            return None
        subs = []
        for ou in targets:
            if str(ou).lower() == "root":
                path = f"{self.OU_ID_SSM_PREFIX}/root-id"
            else:
                path = f"{self.OU_ID_SSM_PREFIX}/{self._ou_ssm_slug(ou)}-ou-id"
            subs.append(
                f"$(aws ssm get-parameter --name {path} "
                "--query Parameter.Value --output text)"
            )
        # Internal commas are escaped (\\,) so the CLI shorthand treats them as
        # CommaDelimitedList separators rather than key=value separators; the
        # value is quoted so command substitution stays a single argument.
        return '"' + "\\,".join(subs) + '"'

    def _generate_stack_command_info(self, stack_name: str, section: str,
                                   template_name: str, home_region: str,
                                   u_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate CloudFormation stack command information."""
        
        commands = []
        
        # If parameters are needed, add parameter collection step
        if u_parameters:
            commands.append({
                "description": "Collect required parameters from user",
                "action": "collect_parameters",
                "parameters": [
                    {
                        "name": param_name,
                        "type": param_info.get("Type", "String"),
                        "description": param_info.get("Description", f"Parameter {param_name}"),
                        "prompt": self._generate_live_parameter_prompt(param_name, param_info)
                    }
                    for param_name, param_info in u_parameters.items()
                ]
            })
            
            # Build parameter string. Policy target parameters (u<Policy>Targets)
            # are populated with ready-to-run SSM lookups for the configured
            # target OUs; everything else keeps a <placeholder> for the user.
            param_pairs = []
            for name in u_parameters.keys():
                resolved = self._resolve_targets_param_value(name)
                value = resolved if resolved is not None else f"<{name}>"
                param_pairs.append(f"ParameterKey={name},ParameterValue={value}")
            param_string = "--parameters " + " ".join(param_pairs)

            create_cmd = f"aws cloudformation create-stack --stack-name {stack_name} --template-body file://{section}/{template_name} {param_string} --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --region {home_region}"
        else:
            create_cmd = f"aws cloudformation create-stack --stack-name {stack_name} --template-body file://{section}/{template_name} --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --region {home_region}"
        
        commands.append({
            "description": f"Create CloudFormation stack {stack_name}",
            "command_template": create_cmd,
            "agent_note": "Replace <parameter_name> placeholders with actual values collected from user" if u_parameters else "Execute command as-is",
            "expected_output": "StackId returned"
        })
        
        # Wait command
        commands.append({
            "description": "Wait for stack creation to complete",
            "command": f"aws cloudformation wait stack-create-complete --stack-name {stack_name} --region {home_region}",
            "expected_output": "Command completes without error"
        })
        
        return {
            "description": f"Deploy {template_name} as CloudFormation stack in Management Account",
            "commands": commands,
            "success_criteria": "Stack shows CREATE_COMPLETE status"
        }
    
    def _generate_stackset_command_info(self, stack_name: str, section: str,
                                      template_name: str, phase_name: str,
                                      home_region: str, account_mappings: Dict[str, Any],
                                      u_parameters: Dict[str, Any],
                                      template_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate CloudFormation StackSet command information."""
        
        if template_metadata is None:
            template_metadata = {}
        
        # Check if this template requires all-region deployment
        deployment_regions = template_metadata.get('DeploymentRegions', '').upper()
        is_all_regions = deployment_regions == 'ALL_ENABLED'
        
        commands = []
        
        # Collect all parameters needed (template params + deployment targets)
        all_params_needed = []
        
        # Add template parameters
        if u_parameters:
            for param_name, param_info in u_parameters.items():
                all_params_needed.append({
                    "name": param_name,
                    "type": param_info.get("Type", "String"),
                    "description": param_info.get("Description", f"Parameter {param_name}"),
                    "prompt": self._generate_live_parameter_prompt(param_name, param_info)
                })
        
        # Add deployment target parameters
        all_params_needed.append({
            "name": "ROOT_OU_ID",
            "type": "String",
            "description": "Root Organizational Unit ID",
            "prompt": "Please provide the Root OU ID. You can get this by running: aws organizations list-roots --query 'Roots[0].Id' --output text"
        })
        
        # Determine target account based on new naming convention
        if self._is_logarchive_account_stackset(template_name):
            all_params_needed.append({
                "name": "LOGARCHIVE_ACCOUNT_ID",
                "type": "String",
                "description": "Log Archive Account ID for log storage resources",
                "prompt": "Please provide the Log Archive Account ID (12-digit AWS account ID for log storage)"
            })
        elif self._is_network_account_stackset(template_name):
            all_params_needed.append({
                "name": "NETWORK_ACCOUNT_ID",
                "type": "String", 
                "description": "Network Account ID for network resources",
                "prompt": "Please provide the Network Account ID (12-digit AWS account ID where network resources will be deployed)"
            })
        elif self._is_audit_account_stackset(template_name):
            all_params_needed.append({
                "name": "AUDIT_ACCOUNT_ID",
                "type": "String",
                "description": "Audit Account ID for security resources", 
                "prompt": "Please provide the Audit Account ID (12-digit AWS account ID for security monitoring)"
            })
        
        # Parameter collection step
        commands.append({
            "description": "Collect required parameters from user",
            "action": "collect_parameters",
            "parameters": all_params_needed
        })
        
        # Build StackSet creation command
        if u_parameters:
            param_string = "--parameters " + " ".join([
                f"ParameterKey={name},ParameterValue=<{name}>"
                for name in u_parameters.keys()
            ])
            create_cmd = f"aws cloudformation create-stack-set --stack-set-name {stack_name} --template-body file://{section}/{template_name} {param_string} --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --permission-model SERVICE_MANAGED --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false --region {home_region}"
        else:
            create_cmd = f"aws cloudformation create-stack-set --stack-set-name {stack_name} --template-body file://{section}/{template_name} --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --permission-model SERVICE_MANAGED --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false --region {home_region}"
        
        commands.append({
            "description": f"Create StackSet {stack_name}",
            "command_template": create_cmd,
            "agent_note": "Replace <parameter_name> placeholders with actual values collected from user",
            "expected_output": "StackSetId returned"
        })
        
        # Build deployment targets command using new detection methods
        # Determine regions flag: all enabled regions or just home region
        if is_all_regions:
            regions_flag = "<ALL_ENABLED_REGIONS>"
            regions_note = "Get all enabled regions by running: aws ec2 describe-regions --query 'Regions[?OptInStatus!=`not-opted-in`].RegionName' --output text | tr '\\t' ' '. Pass the full space-separated list to --regions."
        else:
            regions_flag = home_region
            regions_note = None
        
        if self._is_logarchive_account_stackset(template_name):
            target_cmd = f"aws cloudformation create-stack-instances --stack-set-name {stack_name} --deployment-targets OrganizationalUnitIds=<ROOT_OU_ID>,Accounts=<LOGARCHIVE_ACCOUNT_ID>,AccountFilterType=INTERSECTION --regions {regions_flag} --operation-preferences MaxConcurrentPercentage=100"
        elif self._is_network_account_stackset(template_name):
            target_cmd = f"aws cloudformation create-stack-instances --stack-set-name {stack_name} --deployment-targets OrganizationalUnitIds=<ROOT_OU_ID>,Accounts=<NETWORK_ACCOUNT_ID>,AccountFilterType=INTERSECTION --regions {regions_flag} --operation-preferences MaxConcurrentPercentage=100"
        elif self._is_audit_account_stackset(template_name):
            target_cmd = f"aws cloudformation create-stack-instances --stack-set-name {stack_name} --deployment-targets OrganizationalUnitIds=<ROOT_OU_ID>,Accounts=<AUDIT_ACCOUNT_ID>,AccountFilterType=INTERSECTION --regions {regions_flag} --operation-preferences MaxConcurrentPercentage=100"
        elif self._is_organization_wide_stackset(template_name):
            target_cmd = f"aws cloudformation create-stack-instances --stack-set-name {stack_name} --deployment-targets OrganizationalUnitIds=<ROOT_OU_ID>,AccountFilterType=NONE --regions {regions_flag} --operation-preferences MaxConcurrentPercentage=100"
        else:
            # Default to organization-wide deployment if no specific pattern matches
            target_cmd = f"aws cloudformation create-stack-instances --stack-set-name {stack_name} --deployment-targets OrganizationalUnitIds=<ROOT_OU_ID>,AccountFilterType=NONE --regions {regions_flag} --operation-preferences MaxConcurrentPercentage=100"
        
        deploy_instance_step = {
            "description": f"Deploy StackSet instances",
            "command_template": target_cmd,
            "agent_note": "Replace <ROOT_OU_ID> and account ID placeholders with actual values collected from user",
            "expected_output": "OperationId returned"
        }
        
        if regions_note:
            deploy_instance_step["agent_note"] += f". MULTI-REGION: {regions_note}"
            deploy_instance_step["multi_region"] = True
        
        commands.append(deploy_instance_step)
        
        return {
            "description": f"Deploy {template_name} as StackSet across organization" + (" (all regions)" if is_all_regions else ""),
            "commands": commands,
            "success_criteria": "StackSet shows ACTIVE status and all instances show CURRENT"
        }
    
    def _generate_agent_guide_content(self, config: Dict[str, Any],
                                    processing_results: Dict[str, Any],
                                    deployment_steps: List[Dict[str, Any]],
                                    home_region: str) -> str:
        """Generate the markdown content for the LLM agent guide."""
        
        total_steps = len(deployment_steps)
        phases = list(set(step['phase'] for step in deployment_steps))
        
        # Get Control Tower status
        is_control_tower_enabled = TitaniumConfigParser.get_control_tower_enabled(config)

        guide_content = f"""# LLM Agent Deployment Guide
## Interactive Step-by-Step AWS Landing Zone Deployment

This guide is specifically designed for LLM/GenAI agents to execute AWS Landing Zone deployments through interactive, step-by-step processes with user confirmation and dynamic parameter resolution.

## Guide Overview

- **Total Steps**: {total_steps}
- **Deployment Phases**: {', '.join(phases)}
- **Target Region**: {home_region}
- **Control Tower Enabled**: {is_control_tower_enabled}
- **Interaction Model**: Step-by-step with user confirmation
- **Parameter Handling**: Dynamic resolution with user prompts

"""
        
        # Add decision matrix
        guide_content += self.generate_decision_matrix(is_control_tower_enabled)
        guide_content += "\n"
        
        # Add Control Tower documentation
        guide_content += self._generate_control_tower_documentation()
        guide_content += "\n"
        
        guide_content += """## How This Guide Works

This guide is structured for LLM agents to follow these patterns:

### 1. Parameter Resolution Pattern
For each template requiring parameters:
```
Agent: "I need to deploy [template]. This template requires parameter [X] which is [description]. 
        [Specific prompt for parameter]. Please provide the value or confirm the suggested value: [suggestion]"
User: [Provides value or confirms]
Agent: "Thank you. I'll use [resolved_value] for parameter [X]."
```

### 2. Deployment Confirmation Pattern
Before each deployment:
```
Agent: "Ready to deploy [template_name]. This will [description]. 
        The command I'll execute is: [command]
        Proceed with deployment? (yes/no)"
User: "yes"
Agent: [Executes command and reports results]
```

### 3. Verification Pattern
After each deployment:
```
Agent: [Executes verification commands]
Agent: "Deployment verification: [results]. Status: [SUCCESS/FAILED]"
```

## Deployment Steps

"""
        
        # Group steps by phase
        current_phase = None
        step_number = 1
        
        for step in deployment_steps:
            if step['phase'] != current_phase:
                current_phase = step['phase']
                guide_content += f"\n### Phase: {current_phase.title()}\n\n"
            
            guide_content += f"#### Step {step_number}: {step['title']}\n"
            guide_content += f"**Phase**: {step['phase']} | **ID**: {step['step_id']}\n\n"
            guide_content += f"**Description**: {step['description']}\n\n"
            
            if 'agent_instructions' in step:
                guide_content += "**Agent Instructions**:\n"
                for instruction in step['agent_instructions']:
                    guide_content += f"- {instruction}\n"
                guide_content += "\n"
            
            # Parameter prompts
            if 'parameter_prompts' in step:
                guide_content += "**Parameter Resolution Required**:\n"
                for param in step['parameter_prompts']:
                    guide_content += f"- **{param['parameter_name']}** ({param['parameter_type']})\n"
                    guide_content += f"  - Prompt: \"{param['prompt']}\"\n"
                    if param['suggested_value']:
                        guide_content += f"  - Suggested: `{param['suggested_value']}`\n"
                    guide_content += f"  - Validation: {param['validation']}\n\n"
            
            # Commands
            if 'commands' in step:
                guide_content += "**Commands to Execute**:\n"
                for i, cmd in enumerate(step['commands'], 1):
                    guide_content += f"{i}. {cmd['description']}\n"
                    
                    # Handle different command formats
                    if 'command' in cmd:
                        guide_content += f"   ```bash\n   {cmd['command']}\n   ```\n"
                    elif 'command_template' in cmd:
                        guide_content += f"   ```bash\n   {cmd['command_template']}\n   ```\n"
                        if 'agent_note' in cmd:
                            guide_content += f"   *Note*: {cmd['agent_note']}\n"
                    elif 'action' in cmd:
                        guide_content += f"   *Action*: {cmd['action']}\n"
                        if cmd['action'] == 'collect_parameters' and 'parameters' in cmd:
                            guide_content += f"   *Parameters to collect*: {len(cmd['parameters'])} parameters\n"
                            # Display detailed parameter information
                            for param in cmd['parameters']:
                                guide_content += f"      - **{param['name']}** ({param['type']})\n"
                                guide_content += f"        - Description: {param['description']}\n"
                                guide_content += f"        - Prompt: \"{param['prompt']}\"\n"
                    
                    if 'confirmation_prompt' in cmd:
                        guide_content += f"   *Confirmation*: {cmd['confirmation_prompt']}\n"
                    expected_output = cmd.get('expected_output', 'Command executes successfully')
                    guide_content += f"   *Expected*: {expected_output}\n\n"
            
            # Confirmation prompt
            if 'confirmation_prompt' in step:
                guide_content += f"**Confirmation Prompt**: {step['confirmation_prompt']}\n\n"
            
            # Success criteria
            guide_content += f"**Success Criteria**: {step['success_criteria']}\n\n"
            
            # Failure actions
            if 'failure_actions' in step:
                guide_content += "**If Step Fails**:\n"
                for action in step['failure_actions']:
                    guide_content += f"- {action}\n"
                guide_content += "\n"
            
            guide_content += "---\n\n"
            step_number += 1
        
        # Add troubleshooting section
        guide_content += """## Troubleshooting Guide for LLM Agents

### Common Parameter Issues
- **Account ID not found**: Ask user to provide the correct 12-digit account ID
- **Invalid bucket name**: Ensure bucket name follows S3 naming conventions (lowercase, no spaces)
- **Organization ID issues**: Verify user has Organizations permissions

### Deployment Failures
- **Permission errors**: Ask user to verify AWS CLI permissions and Organizations access
- **Template validation errors**: Check template syntax and parameter values
- **StackSet creation failures**: Verify Organizations integration is enabled

### Agent Response Patterns

#### For Parameter Collection:
```
"I need to collect the value for parameter [name]. [Description]. 
[Specific prompt]. Please provide the value or confirm the suggested value: [suggestion]"
```

#### For Deployment Confirmation:
```
"Ready to deploy [template]. This will [action]. 
Command: [command]
Proceed? (yes/no)"
```

#### For Status Reporting:
```
"Deployment Status: [SUCCESS/FAILED]
Details: [specific results]
Next: [next action]"
```

## JSON Guide Reference

A machine-readable version of this guide is available in `llm_agent_steps.json` for programmatic access.

---
*Generated by Titanium LLM Agent Guide Generator*
"""
        
        return guide_content
    
    def _generate_json_guide(self, deployment_steps: List[Dict[str, Any]],
                           config: Dict[str, Any], home_region: str) -> Dict[str, Any]:
        """Generate JSON format guide for programmatic use."""

        return {
            "guide_version": "1.0",
            "guide_type": "llm_agent_interactive",
            "total_steps": len(deployment_steps),
            "home_region": home_region,
            "interaction_patterns": {
                "parameter_resolution": "Ask user for each parameter with specific prompts",
                "deployment_confirmation": "Request explicit yes/no confirmation before each deployment",
                "status_reporting": "Report success/failure with specific details"
            },
            "steps": deployment_steps
        }
    
    def _extract_home_region(self, config: Dict[str, Any]) -> str:
        """Extract home region from Titanium config."""
        home_region = config.get('homeRegion')
        if not home_region:
            home_region = config.get('global', {}).get('homeRegion')
        if not home_region:
            home_region = config.get('network', {}).get('tgwArchitecture', {}).get('region')
        
        if isinstance(home_region, str) and home_region.startswith('&'):
            home_region = 'us-east-1'
        
        return home_region or 'us-east-1'
    
    def _extract_account_mappings(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract account mappings from Titanium config."""
        mappings = {
            'management_account': None,
            'network_account': None,
            'log_archive_account': None,
            'audit_account': None,
            'root_ou_id': None,
            'organizational_units': {},
            'account_emails': {}
        }
        
        bootstrap = config.get('bootstrap', {})
        org_mapping = bootstrap.get('organizationMapping', {})
        
        if org_mapping:
            mappings['root_ou_id'] = org_mapping.get('rootOrganizationId', '${ROOT_OU_ID}')
            mappings['organizational_units'] = org_mapping.get('organizationalUnitIds', {})
        
        accounts = config.get('accounts', {})
        for account_name, account_config in accounts.items():
            if isinstance(account_config, dict):
                account_id = account_config.get('id')
                email = account_config.get('email')
                
                if account_id:
                    if account_name.lower() in ['management', 'mgmt']:
                        mappings['management_account'] = account_id
                    elif account_name.lower() in ['network', 'networking']:
                        mappings['network_account'] = account_id
                    elif account_name.lower() in ['logarchive', 'log-archive', 'logging']:
                        mappings['log_archive_account'] = account_id
                    elif account_name.lower() in ['audit', 'security']:
                        mappings['audit_account'] = account_id
                
                if email:
                    mappings['account_emails'][account_name] = email
        
        return mappings
    
    def _get_phase_description(self, phase_name: str) -> str:
        """Get description for deployment phase."""
        descriptions = {
            'bootstrap': 'Enable CloudFormation StackSets Organizations Integration and foundational roles',
            'controltower': 'Deploy AWS Control Tower with prerequisites and landing zone setup',
            'organization': 'Create organizational units and deploy service control policies',
            'identity': 'Deploy organization-wide IAM controls (account password policy)',
            'security': 'Enable security services and compliance monitoring',
            'network': 'Deploy VPCs, Transit Gateway, and network security infrastructure'
        }
        return descriptions.get(phase_name, f'Deploy {phase_name} infrastructure')
    
    def _is_management_account_only(self, template_name: str) -> bool:
        """Determine if template should be deployed only in management account (Stack)."""
        return '-stack-mgmt-' in template_name.lower()

    def _is_audit_account_stackset(self, template_name: str) -> bool:
        """Determine if template is a StackSet deployed to audit account."""
        return '-stackset-audit-' in template_name.lower()

    def _is_network_account_stackset(self, template_name: str) -> bool:
        """Determine if template is a StackSet deployed to network account."""
        return '-stackset-network-' in template_name.lower()

    def _is_logarchive_account_stackset(self, template_name: str) -> bool:
        """Determine if template is a StackSet deployed to log archive account."""
        return '-stackset-logarchive-' in template_name.lower()

    def _is_organization_wide_stackset(self, template_name: str) -> bool:
        """Determine if template is a StackSet deployed organization-wide."""
        return '-stackset-org-' in template_name.lower()
    
    def _is_log_storage_template(self, template_name: str) -> bool:
        """Determine if template is for log storage and should deploy to LogArchive account."""
        # Use new naming convention pattern
        return self._is_logarchive_account_stackset(template_name)

    def generate_template_mapping(
        self,
        config: Optional[Dict[str, Any]] = None,
        templates_dir: Optional[str] = None,
        automation_registry_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate structured template mapping for the configuration summary tool.

        Reuses existing methods for template scanning, parameter extraction,
        deployment target detection, and ordering logic. Adds automation registry
        integration, template selection metadata, and Titanium.yaml path mapping.

        Args:
            config: Optional Titanium.yaml config dict for selection-aware mapping.
            templates_dir: Path to templates directory (defaults to mcp_tools/templates/).
            automation_registry_path: Path to automation_registry.yaml.

        Returns:
            Template_Mapping dict with version, sections, and deployment_order.
        """
        import re

        # Validate config if provided
        if config is not None and not isinstance(config, dict):
            return {"error": "config must be a dictionary"}

        # Resolve templates directory
        if templates_dir is None:
            templates_dir = str(Path(__file__).parent / "templates")

        # Resolve automation registry path
        if automation_registry_path is None:
            automation_registry_path = str(
                Path(__file__).parent.parent / "config" / "automation_registry.yaml"
            )

        # Load automation registry
        automation_registry: Dict[str, Any] = {}
        try:
            with open(automation_registry_path, "r") as f:
                registry_data = yaml.safe_load(f)
                automation_registry = registry_data.get("sections", {})
        except FileNotFoundError:
            return {"error": "automation_registry.yaml not found"}
        except Exception as e:
            return {"error": f"Failed to load automation_registry.yaml: {str(e)}"}

        # Load param_yaml_mapping
        param_mapping: Dict[str, Any] = {}
        mapping_path = Path(automation_registry_path).parent / "param_yaml_mapping.yaml"
        try:
            with open(mapping_path, "r") as f:
                mapping_data = yaml.safe_load(f)
                param_mapping = mapping_data.get("parameters", {})
        except FileNotFoundError:
            print(f"Warning: param_yaml_mapping.yaml not found at {mapping_path}")
        except Exception as e:
            print(f"Warning: Failed to load param_yaml_mapping.yaml: {str(e)}")

        # Define section ordering and metadata
        section_defs = [
            {
                "dir": "bootstrap",
                "section_id": "bootstrap",
                "section_name": "Bootstrap",
                "description": "CloudFormation StackSets service role and org integration",
            },
            {
                "dir": "controltower",
                "section_id": "control_tower",
                "section_name": "Control Tower",
                "description": "Control Tower landing zone setup and configuration",
            },
            {
                "dir": "organization",
                "section_id": "organization",
                "section_name": "Organization",
                "description": "Organizational units, service control policies, tagging policies, and backup policies",
            },
            {
                "dir": "identity",
                "section_id": "identity",
                "section_name": "Identity",
                "description": "IAM password policy and access management",
            },
            {
                "dir": "security",
                "section_id": "security",
                "section_name": "Security",
                "description": "Security Hub, GuardDuty, EBS encryption, Access Analyzer, and security monitoring",
            },
            {
                "dir": "network",
                "section_id": "network",
                "section_name": "Network",
                "description": "IPAM, VPC flow logs, Transit Gateway, DNS resolver, endpoint VPC, and workload VPCs",
            },
            {
                "dir": "finance",
                "section_id": "cost_management",
                "section_name": "Cost Management",
                "description": "Budgets, Compute Optimizer, and Cost Optimization Hub",
            },
        ]

        # Sort key helper for template filenames
        def _get_sort_key(filename: str):
            match = re.match(r"^(\d+)([a-z]?)", filename)
            if match:
                return (int(match.group(1)), match.group(2) or "")
            return (999, "")

        # Determine template selection based on config
        def _should_select_template(filename: str, section_dir: str) -> Tuple[bool, Optional[str]]:
            """Return (selected, skip_reason) for a template."""
            if config is None:
                return True, None

            # 04a / 04b mutual exclusion for network section
            if section_dir == "network":
                # IPAM delegation (01) + sharing (02) — skip when IPAM disabled,
                # matching the network processor's skip gate (issue #82). Preserve
                # the default-on quirk: an ipam block without an explicit enabled
                # flag counts as enabled; an absent block is disabled.
                if filename.startswith(("01-ipam", "02-ipam")):
                    ipam = config.get("network", {}).get("ipam", {}) or {}
                    ipam_enabled = ipam.get("enabled", True if ipam else False)
                    if not ipam_enabled:
                        return False, "IPAM disabled"
                    return True, None

                network_firewall = (
                    config.get("network", {})
                    .get("tgwArchitecture", {})
                    .get("vpcs", {})
                    .get("inspectionVpc", {})
                    .get("networkFirewall", False)
                )
                if filename.startswith("04a-"):
                    if network_firewall:
                        return False, "Network Firewall enabled — using inspection VPC template"
                    return True, None
                if filename.startswith("04b-"):
                    if not network_firewall:
                        return False, "Network Firewall disabled — using basic egress VPC template"
                    return True, None

                # DNS resolver
                if filename.startswith("05-dns"):
                    dns_enabled = (
                        config.get("network", {})
                        .get("tgwArchitecture", {})
                        .get("route53Resolver", {})
                        .get("enabled", True)
                    )
                    if not dns_enabled:
                        return False, "Route53 Resolver disabled"
                    return True, None

                # Endpoint VPC — opt-in. Default False to match both the network
                # processor's skip gate and the advisor, which only ever sets this
                # from the explicit enable_vpc_endpoints answer (default False), so
                # the two never disagree (issue #81).
                if filename.startswith("06-vpc") and "endpoint" in filename.lower():
                    endpoint_enabled = (
                        config.get("network", {})
                        .get("tgwArchitecture", {})
                        .get("vpcs", {})
                        .get("endpointVpc", {})
                        .get("enabled", False)
                    )
                    if not endpoint_enabled:
                        return False, "Endpoint VPC disabled"
                    return True, None

                # Workload VPCs (07) are never deployed: they belong to workload
                # accounts provisioned by Control Tower account vending, not to a
                # Titanium StackSet. The template stays in the repo but is not
                # actionable, matching the network processor's skip (issue #87).
                if filename.startswith("07-vpc") and "workload" in filename.lower():
                    return False, "Workload VPCs are provisioned by Control Tower account vending, not deployed here"

            return True, None

        # Build sections
        sections: List[Dict[str, Any]] = []
        global_deployment_order: List[Dict[str, Any]] = []
        order_counter = 0

        for section_def in section_defs:
            section_dir = section_def["dir"]
            section_id = section_def["section_id"]
            section_path = os.path.join(templates_dir, section_dir)

            # Get automation registry data for this section
            registry_key = section_id
            registry_entry = automation_registry.get(registry_key, {})
            automation_status = registry_entry.get("status", "manual")
            automated_percentage = registry_entry.get("automated_percentage", 0)

            templates_list: List[Dict[str, Any]] = []

            if os.path.isdir(section_path):
                # Scan and sort template files
                yaml_files = [
                    f for f in os.listdir(section_path) if f.endswith(".yaml")
                ]
                yaml_files.sort(key=_get_sort_key)

                for filename in yaml_files:
                    order_counter += 1
                    filepath = os.path.join(section_path, filename)

                    # Determine deployment method and target
                    if self._is_management_account_only(filename):
                        deployment_method = "Stack"
                        deployment_target = "Management"
                    else:
                        deployment_method = "StackSet"
                        if self._is_audit_account_stackset(filename):
                            deployment_target = "Audit"
                        elif self._is_network_account_stackset(filename):
                            deployment_target = "Network"
                        elif self._is_logarchive_account_stackset(filename):
                            deployment_target = "LogArchive"
                        elif self._is_organization_wide_stackset(filename):
                            deployment_target = "All accounts"
                        else:
                            deployment_target = "All accounts"

                    # Determine selection
                    selected, skip_reason = _should_select_template(
                        filename, section_dir
                    )

                    # Parse template and extract parameters
                    parameters_list: List[Dict[str, Any]] = []
                    try:
                        with open(filepath, "r") as f:
                            template_content = f.read()
                        template_data = self._parse_cloudformation_template(
                            template_content
                        )
                        raw_params = template_data.get("Parameters", {})

                        for param_name, param_config in raw_params.items():
                            if param_name.startswith("t"):
                                prefix = "t"
                            elif param_name.startswith("u"):
                                prefix = "u"
                            else:
                                continue

                            description = param_config.get(
                                "Description", f"Parameter {param_name}"
                            )
                            # Clean up placeholder descriptions
                            if isinstance(description, str) and "PLACEHOLDER" in description:
                                description = f"Parameter {param_name}"

                            param_entry: Dict[str, Any] = {
                                "parameter_name": param_name,
                                "parameter_prefix": prefix,
                                "description": description,
                                "titanium_yaml_path": None,
                                "label": None,
                            }

                            # Annotate from param_yaml_mapping
                            if param_name in param_mapping:
                                mapping_entry = param_mapping[param_name]
                                param_entry["titanium_yaml_path"] = mapping_entry.get(
                                    "yaml_path"
                                )
                                param_entry["label"] = mapping_entry.get("label")

                            parameters_list.append(param_entry)

                    except Exception as e:
                        print(
                            f"Warning: Failed to parse template {filename}: {str(e)}"
                        )

                    template_entry = {
                        "filename": filename,
                        "deployment_method": deployment_method,
                        "deployment_target": deployment_target,
                        "deployment_order": order_counter,
                        "selected": selected,
                        "skip_reason": skip_reason,
                        "parameters": parameters_list,
                    }
                    templates_list.append(template_entry)

                    # Add to global deployment order
                    global_deployment_order.append(
                        {
                            "order": order_counter,
                            "filename": f"{section_dir}/{filename}",
                            "deployment_method": deployment_method,
                            "deployment_target": deployment_target,
                            "selected": selected,
                            "skip_reason": skip_reason,
                        }
                    )

            section_entry = {
                "section_id": section_id,
                "section_name": section_def["section_name"],
                "automation_status": automation_status,
                "automated_percentage": automated_percentage,
                "description": section_def["description"],
                "templates": templates_list,
            }
            sections.append(section_entry)

        return {
            "version": "1.0",
            "sections": sections,
            "deployment_order": global_deployment_order,
        }
