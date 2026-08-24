# Step 3: Deploy to AWS

⬅️ [Back to Step 2: Design Your Landing Zone](DESIGN_GUIDE.md) | [Back to README](README.md)

This guide covers generating CloudFormation templates from your `Titanium.yaml` and deploying them to your AWS environment.

## Prerequisites for Deployment

Before deploying your landing zone, ensure you have the following:

- **AWS Organization** — An existing AWS Organization, or the ability to create one from a management account
- **Management account with administrative access** — You need admin-level permissions in the management (payer) account to create accounts, OUs, SCPs, and enable services
- **AWS Control Tower eligibility** — Your management account must meet the [AWS Control Tower prerequisites](https://docs.aws.amazon.com/controltower/latest/userguide/setting-up.html) (no existing Config recorder in the home region, no existing CloudTrail organization trail unless intended)
- **AWS CLI configured** — The [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed and configured with credentials for your management account
- **Python 3.12+** — Required to run the Titanium Generator MCP server for template generation

## Template Generation Support Status

Not all sections of Titanium.yaml have full CloudFormation template support yet. For the canonical per-section support status and coverage, see [About Titanium → Generator Support Status](ABOUT.md#generator-support-status). Sections that still require manual configuration (Identity & Access, Logging, and several security services) are covered in [Manual Steps for Unsupported Sections](#manual-steps-for-unsupported-sections) below.

## How Titanium.yaml Maps to CloudFormation

Your Titanium.yaml contains nine sections. Each section captures a set of landing zone decisions, and the Titanium Generator reads these sections to produce CloudFormation templates.

| # | Titanium.yaml Section | Key | Produces Templates? | What It Configures |
|---|----------------------|-----|--------------------|--------------------|
| 1 | Global Configuration | `homeRegion`, `enabledRegions`, `managementAccountAccessRole` | No (consumed by other sections) | Home region, enabled regions, management account role |
| 2 | Control Tower | `controlTower` | Yes (1 template) | Landing zone version, logging retention, organization trail, region deny |
| 3 | Organization | `organization` | Yes (4 templates) | OUs, SCPs, tagging policies, backup policies |
| 4 | Identity & Access | `iamPasswordPolicy`, `accessAnalyzer`, `iamIdentityCenter` | Not yet | IAM password policy, access analyzer, Identity Center/SSO |
| 5 | Logging | `logging`, `vpcFlowLogs` | Partial (via Network) | CloudTrail trails, Session Manager, CloudWatch log retention, VPC Flow Logs |
| 6 | Security | `centralSecurityServices` | Yes (10 templates) | GuardDuty, SecurityHub, Access Analyzer, EBS default encryption |
| 7 | Accounts | `accounts` | No (consumed by other sections) | Mandatory accounts (Management, LogArchive, Audit), infrastructure and workload accounts |
| 8 | Network | `network` | Yes (8 templates) | IPAM, Transit Gateway, Network Firewall, VPC Endpoints, Route 53 Resolver, workload VPCs |
| 9 | Cloud Financial Management | `cloudFinancialManagement` | Yes (3 templates) | Budgets, Compute Optimizer, Cost Optimization Hub |

The Titanium Generator reads your Titanium.yaml, matches each section to its corresponding CloudFormation templates, and injects your configuration values as template parameters.

## Step-by-Step Deployment Sequence

### Step 1: Review and Validate Your Titanium.yaml

Before generating templates, review your configuration:

1. Open your `Titanium.yaml` and verify all email addresses are updated (search for `@example.com`)
2. Confirm your home region and enabled regions are correct
3. Use the Titanium Generator's validation tool to check for errors:

   > "Can you validate my Titanium.yaml configuration?"

   The assistant will run `parse_titanium_config` and report any issues.

### Step 2: Generate CloudFormation Templates

Use the Titanium Generator to produce CloudFormation templates from your configuration:

> "Generate CloudFormation templates from my Titanium.yaml"

The assistant will run `process_all_templates`, which:
- Reads your Titanium.yaml
- Processes each supported section
- Outputs CloudFormation templates to a specified directory
- Reports which sections were processed and which were skipped

Review the generated templates before deployment. Each template is a standard CloudFormation YAML file that can be inspected, version-controlled, and customized if needed.

### Step 3: Set Up AWS Control Tower

If you haven't already set up AWS Control Tower:

1. Sign in to the [AWS Management Console](https://console.aws.amazon.com/) with your management account
2. Navigate to **AWS Control Tower** and launch the setup wizard
3. Select your home region and configure the landing zone settings
4. Configure foundational OUs — Control Tower v4 creates a **Security** OU by default. You can optionally create a **Sandbox** OU during setup
5. Configure shared accounts — In CT v4, the **Log Archive** and **Audit** accounts are created as part of the Security OU. You can choose existing accounts or let Control Tower create new ones
6. Review and confirm the setup — Wait for Control Tower setup to complete (typically 30–60 minutes)

> **Note (Control Tower v4):** Unlike earlier versions, CT v4 allows you to opt out of creating an organization-level CloudTrail trail and AWS Config aggregator during setup. If your Titanium configuration manages these separately (via the `logging` or `centralSecurityServices` sections), you may choose to skip them during CT setup to avoid conflicts.

If Control Tower is already set up, verify that your existing configuration aligns with the settings in your Titanium.yaml (landing zone version, logging retention, region deny settings).

### Step 4: Deploy CloudFormation Stacks

When you generate templates (Step 2), the Titanium Generator also produces an `LLM_AGENT_DEPLOYMENT_GUIDE.md` alongside your CloudFormation templates. This guide is specifically designed for AI assistants to execute deployments interactively — step by step, with parameter resolution and user confirmation at each stage.

To start the deployment, point your AI assistant at the generated guide:

> "Use the LLM_AGENT_DEPLOYMENT_GUIDE.md in my output directory to deploy my landing zone templates"

The agent will:
1. Validate your AWS environment and collect account IDs
2. Deploy templates in the correct order (Bootstrap → Organization → Network → Security → Finance)
3. Resolve parameters dynamically — prompting you for account IDs, bucket names, and OU IDs as needed
4. Ask for confirmation before each deployment
5. Verify each stack/StackSet completes successfully before moving to the next

The deployment follows five phases:

| Phase | Templates | What It Deploys | Diagram |
|-------|-----------|----------------|---------|
| Bootstrap | 2 templates | Config recorder role, StackSets Organizations integration | — |
| Organization | 4 templates | OUs, SCPs, backup policies, tagging policies | [Organization diagram](docs/architecture-diagrams/02-organization.png) |
| Network | 8 templates | IPAM, Transit Gateway, Network Firewall, VPC Flow Logs, Route 53 Resolver, VPC Endpoints, workload VPCs | [Network diagram](docs/architecture-diagrams/03-network.png) |
| Security | 10 templates | GuardDuty, SecurityHub, Access Analyzer, and EBS default encryption across accounts | [Security diagram](docs/architecture-diagrams/04-security.png) |
| Finance | 3 templates | AWS Budgets with alert notifications, Compute Optimizer enablement, Cost Optimization Hub enablement | [Finance diagram](docs/architecture-diagrams/06-finance.png) |

Templates are deployed as CloudFormation stacks (management account) or StackSets (multi-account) based on their naming convention:
- `stack-mgmt` → CloudFormation stack in the management account
- `stackset` → StackSet targeting specific accounts or OUs

A machine-readable `llm_agent_steps.json` is also generated for programmatic access to the deployment steps.

### Step 5: Verify Deployment

After deployment, verify the following outcomes:

1. **AWS Organizations** — Check that all OUs exist and SCPs are attached correctly
2. **Accounts** — Verify that infrastructure accounts (SharedServices, Network, Monitoring) are created and in the correct OUs
3. **Network** — Confirm Transit Gateway is operational, VPCs are provisioned, and IPAM pools are allocated
4. **Security** — Verify GuardDuty is enabled across all accounts and SecurityHub is aggregating findings
5. **Logging** — Confirm VPC Flow Logs are being delivered to the centralized S3 bucket

You can ask your assistant to run verification checks:

> "Verify my landing zone deployment matches the Titanium.yaml configuration"

## Expected Outcomes

For a visual summary of the complete landing zone, see the [Architecture Overview diagram](docs/architecture-diagrams/01-overview.png). The full diagram set is available in the [Architecture Diagrams](docs/architecture-diagrams/README.md) directory.

Once all supported templates are deployed, your landing zone will include:

- **Account structure** — Management, LogArchive, Audit, SharedServices, Network, and Monitoring accounts organized into Security, Infrastructure, Workloads, Sandbox, and Exceptions OUs
- **Governance** — SCPs enforcing region restrictions, preventing organization departure, blocking public S3 buckets, and protecting CloudTrail
- **Networking** — Centralized Transit Gateway with inspection/egress VPCs, IPAM-managed IP allocation, VPC Flow Logs, Route 53 Resolver for hybrid DNS, and centralized VPC Endpoints
- **Security monitoring** — GuardDuty threat detection across all accounts, SecurityHub aggregating compliance findings with configurable standards (AWS FSBP, CIS, NIST, PCI DSS)
- **Tagging and backup** — Organization-wide tagging policies and backup policies applied to workload accounts

## Time and Cost Estimates

### Deployment Time

| Phase | Estimated Time | Notes |
|-------|---------------|-------|
| Control Tower setup | 30–60 minutes | One-time setup, includes account creation |
| Bootstrap stacks | 5–10 minutes | Quick stack deployments |
| Organization stacks | 10–20 minutes | OU creation and SCP attachment |
| Network stacks | 30–60 minutes | VPC provisioning, TGW setup, IPAM allocation |
| Security stacks | 15–30 minutes | Service enablement across accounts |
| **Total initial deployment** | **~2–4 hours** | Assumes sequential deployment with verification |

Full propagation of SCPs, GuardDuty findings, and SecurityHub compliance checks may take 24–48 hours after initial deployment.

### Cost Considerations

Landing zone infrastructure costs vary by configuration. Typical monthly costs for an SMB landing zone:

| Component | Estimated Monthly Cost | Notes |
|-----------|----------------------|-------|
| AWS Control Tower | No additional charge | Uses underlying AWS services |
| AWS Organizations | No additional charge | Free for all accounts |
| GuardDuty | $3–10 per account | Varies by event volume |
| SecurityHub | $1–5 per account | Varies by findings and checks |
| Transit Gateway | $36+ per attachment | Plus data processing charges |
| Network Firewall | $0.395/hr (~$285/mo) | Per firewall endpoint |
| VPC Flow Logs | Varies | Based on log volume and storage |
| CloudWatch Logs | Varies | Based on ingestion and retention |

These are approximate figures. Actual costs depend on your specific configuration, number of accounts, and traffic volume. Use the [AWS Pricing Calculator](https://calculator.aws/) for detailed estimates.

## Manual Steps for Unsupported Sections

For Titanium.yaml sections that don't yet have generator support, you'll need to configure these services using your AI assistant with AWS documentation, or manually through the AWS Console/CLI.

### Identity & Access (Section 4)

Your Titanium.yaml defines IAM password policy and Identity Center settings. To implement these:

- **IAM Password Policy** — Configure via the IAM console under Account Settings, or use the AWS CLI `aws iam update-account-password-policy`
- **IAM Identity Center** — Configure via the IAM Identity Center console, including SSO setup, permission sets, and external identity provider integration

> **Note:** IAM Access Analyzer is now templated as part of the Security phase (delegated administration + organization analyzer), so it no longer requires manual setup.

### Cloud Financial Management (Section 9)

Budgets, Compute Optimizer, and Cost Optimization Hub templates are generated and deployed automatically as part of the Finance phase. No manual steps required for the supported features.

### Security Services Not Yet Templated

The following security services are configured in your Titanium.yaml but lack generator templates:

- **CloudTrail** — Organization trail and data event trails (configured under `logging.cloudtrail`)
- **S3 Public Access Block** — Account-level enforcement (configured under `centralSecurityServices.s3PublicAccessBlock`)
- **AWS Config Rules** — Conformance packs and rule sets (configured under `centralSecurityServices.awsConfig`)
- **Macie** — Sensitive data discovery (configured under `centralSecurityServices.macie`)
- **Detective** — Advanced threat investigation (configured under `centralSecurityServices.detective`)
- **Audit Manager** — Compliance automation (configured under `centralSecurityServices.auditManager`)

For each, refer to the corresponding AWS documentation or ask your AI assistant for help configuring the service using the settings from your Titanium.yaml as a reference.
