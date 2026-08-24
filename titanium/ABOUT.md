# About Titanium

## Where Does Titanium Fit?

AWS Control Tower gives you a baseline — accounts, basic logging, and guardrails. Titanium builds on that foundation with organization design, networking, security hardening, identity, monitoring, and cost management. What remains is the customer-specific work: workload architecture, hybrid connectivity, and operational processes.

![Where Does Titanium Fit?](docs/architecture-diagrams/05b-titanium-value-proposition-simple.png)

## What Gets Deployed

The diagram below shows the AWS environment that Titanium deploys — a multi-account organization with organizational units, centralized security and logging accounts, networking (VPCs, Transit Gateway), identity and access controls, and governance guardrails.

![Landing Zone Overview](docs/architecture-diagrams/01-overview.png)

For the full set of architecture diagrams (organization, network, security), see the [Architecture Diagrams](docs/architecture-diagrams/README.md) directory.

### Templates per Module

Titanium generates CloudFormation templates organized by module. Each module maps to a deployment phase. Template filenames follow a naming convention that determines how each is deployed (`*-stack-mgmt-*` → CloudFormation stack in the management account; `*-stackset-*` → StackSet targeting specific accounts or OUs).

#### Bootstrap (2 templates)
- Config recorder IAM role
- StackSets Organizations integration trust

#### Organization (4 templates)
- Organizational unit (OU) structure
- Service control policies (SCPs)
- Tagging policies
- Backup policies

#### Network (8 templates)
- IPAM delegation (management account)
- IPAM pool sharing across the organization
- VPC Flow Logs bucket (Log Archive account)
- Transit Gateway with egress VPC
- Transit Gateway inspection VPC with Network Firewall
- Route 53 Resolver (hybrid DNS)
- Centralized endpoint VPC (VPC Endpoints)
- Workload VPCs

#### Security (10 templates)
- GuardDuty — delegated administration, detector configuration, and cross-account service role
- SecurityHub — delegated administration, CSPM standards configuration, CSPM policy, and EventBridge findings forwarding
- IAM Access Analyzer — delegated administration and organization analyzer configuration
- EBS default encryption enforced organization-wide

#### Finance (3 templates)
- AWS Budgets with SNS alert notifications
- Compute Optimizer organization-wide enablement
- Cost Optimization Hub organization-wide enablement

## Generator Support Status

| Section                    | Status              | Coverage                                                                                                          |
| ----------------------------| ---------------------| -------------------------------------------------------------------------------------------------------------------|
| Bootstrap                  | Fully supported     | 100% — Config recorder role, StackSets Organizations integration                                                  |
| Organization               | Fully supported     | 100% — OUs, SCPs, tagging policies, backup policies                                                               |
| Network                    | Fully supported     | ~85% — IPAM, Transit Gateway, Network Firewall, VPC Flow Logs, Route 53 Resolver, VPC Endpoints, workload VPCs    |
| Control Tower              | Partially supported | ~60% — Basic setup template; Identity Center and Network Factory not yet templated                                |
| Security                   | Partially supported | ~50% — GuardDuty, SecurityHub, Access Analyzer, and EBS encryption templated                                      |
| Identity & Access, Logging | In progress         | Manual configuration required (see [Deployment Guide](DEPLOYMENT_GUIDE.md#manual-steps-for-unsupported-sections)) |
| Finance                    | Fully supported     | 100% — Budgets, Compute Optimizer, and Cost Optimization Hub                                                      |

## Deployment Phases

Deployment proceeds in five phases, each building on the previous:

| Phase | Templates | What Gets Deployed | Estimated Time |
|-------|-----------|-------------------|----------------|
| 1. Bootstrap | 2 templates | Config recorder role, StackSets Organizations trust | 5–10 min |
| 2. Organization | 4 templates | OUs, SCPs, tagging policies, backup policies | 10–20 min |
| 3. Network | 8 templates | IPAM, Transit Gateway, Network Firewall, VPC Flow Logs, Route 53 Resolver, VPC Endpoints, workload VPCs | 30–60 min |
| 4. Security | 10 templates | GuardDuty, SecurityHub, Access Analyzer, and EBS encryption across accounts | 15–30 min |
| 5. Finance | 3 templates | Budgets with alert notifications, Compute Optimizer enablement, Cost Optimization Hub enablement | 5–10 min |
