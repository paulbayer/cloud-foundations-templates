# Network Templates

This directory contains CloudFormation templates for network infrastructure deployment in AWS Landing Zone.

## Naming Convention

All templates follow the standardized naming pattern:
```
<order>-<service>-<deployment-type>-<target>-<action>.yaml
```

Where:
- **order**: Two-digit number (01-99) for proper sorting
- **service**: Service name (lowercase, hyphenated)
- **deployment-type**: `stack` or `stackset`
- **target**: `mgmt` (management), `network`, `logarchive`, `audit`, or `org` (organization-wide)
- **action**: Action performed (descriptive verb or noun)

## Templates

### 01-ipam-stack-mgmt-delegation.yaml
- **Type**: CloudFormation Stack
- **Target**: Management Account
- **Purpose**: Delegates IPAM administration to the Network account
- **Dependencies**: None (must be deployed first)

### 02-ipam-stackset-network-sharing.yaml
- **Type**: CloudFormation StackSet
- **Target**: Network Account
- **Purpose**: Creates IPAM pools and shares them with the organization
- **Dependencies**: 01-ipam-stack-mgmt-delegation.yaml

### 03-vpc-stackset-logarchive-flowlogs-bucket.yaml
- **Type**: CloudFormation StackSet
- **Target**: Log Archive Account
- **Purpose**: Creates S3 bucket for VPC Flow Logs storage
- **Dependencies**: None

### 04-tgw-stackset-network-firewall.yaml [DEPRECATED]
- **Type**: CloudFormation StackSet
- **Target**: Network Account
- **Purpose**: Deploys Transit Gateway with AWS Network Firewall
- **Dependencies**: 02-ipam-stackset-network-sharing.yaml
- **Status**: **DEPRECATED** - Use 04a or 04b instead

**This template has been replaced by:**
- **04a-tgw-stackset-egress-vpc.yaml** - For centralized egress without firewall inspection
- **04b-tgw-stackset-inspection-vpc-firewall.yaml** - For centralized egress with Network Firewall inspection

### 04a-tgw-stackset-egress-vpc.yaml
- **Type**: CloudFormation StackSet
- **Target**: Network Account
- **Purpose**: Deploys Transit Gateway with Egress VPC for centralized internet egress (without firewall)
- **Dependencies**: 02-ipam-stackset-network-sharing.yaml
- **Use Case**: Centralized egress without deep packet inspection
- **Architecture**: Spoke VPCs → TGW → Egress VPC (TGW Subnets) → NAT Gateways → Internet

### 04b-tgw-stackset-inspection-vpc-firewall.yaml
- **Type**: CloudFormation StackSet
- **Target**: Network Account
- **Purpose**: Deploys Transit Gateway with Inspection VPC and AWS Network Firewall for centralized egress with inspection
- **Dependencies**: 02-ipam-stackset-network-sharing.yaml
- **Use Case**: Centralized egress with deep packet inspection
- **Architecture**: Spoke VPCs → TGW → Inspection VPC (TGW Subnets) → Firewall Endpoints → NAT Gateways → Internet

### 05-dns-stackset-network-resolver.yaml
- **Type**: CloudFormation StackSet
- **Target**: Network Account
- **Purpose**: Configures Route 53 Resolver for hybrid DNS
- **Dependencies**: 04a-tgw-stackset-egress-vpc.yaml OR 04b-tgw-stackset-inspection-vpc-firewall.yaml

### 06-vpc-stackset-endpoint-vpc.yaml
- **Type**: CloudFormation StackSet
- **Target**: Network Account
- **Purpose**: Deploys centralized VPC Endpoints for AWS services
- **Dependencies**: 02-ipam-stackset-network-sharing.yaml, 04a or 04b

### 07-vpc-stackset-workload-vpc.yaml
- **Type**: CloudFormation StackSet
- **Target**: Workload Accounts
- **Purpose**: Deploys workload VPCs with conditional IPAM or explicit CIDR allocation
- **Dependencies**: 02-ipam-stackset-network-sharing.yaml, 04a or 04b

## Deployment Order

Templates must be deployed in numerical order to satisfy dependencies:

1. **01-ipam-stack-mgmt-delegation.yaml** - Delegate IPAM to Network account
2. **02-ipam-stackset-network-sharing.yaml** - Create and share IPAM pools
3. **03-vpc-stackset-logarchive-flowlogs-bucket.yaml** - Create Flow Logs bucket
4. **Choose ONE of the following:**
   - **04a-tgw-stackset-egress-vpc.yaml** - Deploy Transit Gateway with Egress VPC (without firewall)
   - **04b-tgw-stackset-inspection-vpc-firewall.yaml** - Deploy Transit Gateway with Inspection VPC and Network Firewall
5. **05-dns-stackset-network-resolver.yaml** - Configure DNS resolver (optional)
6. **06-vpc-stackset-endpoint-vpc.yaml** - Deploy centralized VPC Endpoints (optional)
7. **07-vpc-stackset-workload-vpc.yaml** - Deploy workload VPCs (as needed)

### Template Selection Guide

**Use Template 04a (TGW + Egress VPC)** when:
- You need centralized internet egress for spoke VPCs
- Deep packet inspection is NOT required
- You want simpler architecture with lower cost
- Traffic flows: Spoke VPCs → TGW → Egress VPC → NAT Gateways → Internet

**Use Template 04b (TGW + Inspection VPC + Network Firewall)** when:
- You need centralized internet egress for spoke VPCs
- Deep packet inspection IS required for security/compliance
- You need advanced threat detection and prevention
- Traffic flows: Spoke VPCs → TGW → Inspection VPC → Firewall Endpoints → NAT Gateways → Internet

**Note**: Template 04 (04-tgw-stackset-network-firewall.yaml) is deprecated and should not be used for new deployments.

## Target Account Logic

The naming convention indicates which account each template deploys to:

- **-stack-mgmt-**: CloudFormation Stack in Management Account
- **-stackset-network-**: CloudFormation StackSet in Network Account
- **-stackset-logarchive-**: CloudFormation StackSet in Log Archive Account

This enables the LLM Agent Guide to automatically generate correct deployment commands.

## Notes

- IPAM delegation must happen in the Management account before IPAM resources can be created in the Network account
- VPC Flow Logs bucket is deployed to the Log Archive account for centralized logging
- Transit Gateway and DNS resolver are deployed to the Network account for centralized network management
- **Template 04 Deprecation**: The original 04-tgw-stackset-network-firewall.yaml has been replaced by two specialized templates (04a and 04b) for clearer architecture separation

## Migration from Template 04

If you are currently using the deprecated Template 04 (04-tgw-stackset-network-firewall.yaml), you should migrate to one of the new templates:

### Migration Steps

1. **Determine which template to use:**
   - If Network Firewall is NOT enabled: Migrate to **04a-tgw-stackset-egress-vpc.yaml**
   - If Network Firewall IS enabled: Migrate to **04b-tgw-stackset-inspection-vpc-firewall.yaml**

2. **Plan the migration:**
   - This is a breaking change that requires redeployment
   - Existing Template 04 stacks cannot be updated in-place to the new templates
   - Plan for network downtime during migration

3. **Deploy the new template:**
   - Deploy the appropriate new template (04a or 04b) with the same parameters
   - Verify connectivity and routing
   - Delete the old Template 04 stack

4. **Update dependent resources:**
   - Update any resources that reference the old stack outputs
   - Verify all cross-stack references are working

### Why the Change?

Template 04 attempted to handle multiple architectures in a single template, creating complex conditional logic that was difficult to maintain and understand. The new templates provide:

- **Clear separation of concerns**: Egress vs Inspection architectures
- **Simpler templates**: No complex conditional logic
- **Explicit architecture choice**: Clear understanding of what's being deployed
- **Better alignment with AWS Well-Architected Framework**
