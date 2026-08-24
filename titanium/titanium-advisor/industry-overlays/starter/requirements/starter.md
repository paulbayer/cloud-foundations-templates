# Starter Industry Requirements

## Overview

The **Starter** industry overlay is designed for organizations that want to get started with AWS Landing Zones using basic, proven patterns. This configuration focuses on fundamental security and networking capabilities that can be immediately deployed using the current titanium-generator CloudFormation templates.

## Target Audience

- Organizations new to AWS Landing Zones
- Small to medium-sized organizations (< 500 people)
- Teams that want a working foundation to build upon
- Organizations that prioritize quick deployment over advanced features
- Development teams that need basic multi-account structure

## Supported Features

### ✅ Organization Structure
- **Organizational Units**: Security, Infrastructure, Workloads, Sandbox
- **Service Control Policies**: 
  - Prevent accounts from leaving organization
  - Prevent public S3 buckets
  - Basic region restrictions
- **Tagging Policies**: Enforce required tags for cost allocation and governance
- **Backup Policies**: Optional automated backup for workload accounts

### ✅ Account Management
- **Mandatory Accounts**: Management, LogArchive, Audit (required by AWS Control Tower)
- **Infrastructure Accounts**: Network, SharedServices (optional but recommended)
- **Account Email Management**: Automated email address generation based on domain

### ✅ Network Architecture
- **Transit Gateway**: Centralized networking with segregated routing
- **IPAM**: IP Address Manager for automated CIDR allocation
- **Inspection VPC**: Dedicated VPC for centralized network security and traffic inspection
- **AWS Network Firewall**: Stateful network firewall for traffic filtering and inspection
  - Firewall logging to centralized S3 bucket
  - Integration with IPAM for automatic IP addressing
  - Multi-AZ deployment for high availability
- **VPC Management**: 
  - Default VPC deletion across accounts
  - Automated workload VPC creation
  - Multi-AZ deployment (2-3 availability zones)
- **VPC Flow Logs**: 
  - Centralized S3 bucket in Log Archive account
  - Network traffic logging for security analysis
  - 90-day retention by default

### ✅ Basic Security
- **AWS Control Tower**: Foundational security guardrails
- **Service Control Policies**: Essential governance controls
- **VPC Flow Logs**: Network traffic monitoring
- **Cross-account logging**: Centralized log storage in LogArchive account

### ✅ Cost Management
- **Basic Budgets**: Monthly cost budgets with email alerts
- **Cost Allocation Tags**: Basic tagging for cost tracking

## Limitations and Exclusions

### ❌ Advanced Security Services
- **GuardDuty**: Threat detection (planned for future release)
- **Security Hub**: Compliance monitoring (planned for future release)
- **Macie**: Data classification and protection (planned for future release)
- **Detective**: Security investigation (planned for future release)
- **AWS Config**: Advanced compliance rules (planned for future release)

### ❌ Advanced Logging and Monitoring
- **CloudTrail Data Events**: Advanced API logging (planned for future release)
- **CloudWatch Metrics and Alarms**: Custom monitoring (planned for future release)
- **Session Manager**: EC2 session logging (planned for future release)
- **AWS Config**: Configuration compliance monitoring (planned for future release)

### ❌ Identity and Access Management
- **Identity Center**: SSO configuration (planned for future release)
- **Advanced IAM**: Custom roles and policies beyond basic patterns
- **External Identity Providers**: SAML/SCIM integration (planned for future release)

### ❌ Advanced Network Features
- **VPC Endpoints**: Private connectivity to AWS services (planned for future release)
- **Hybrid Connectivity**: Direct Connect, VPN, Route53 Resolver (planned for future release)
- **CloudWAN**: Global network management (planned for future release)

### ❌ Advanced Cost Management
- **Cost and Usage Reports**: Detailed cost analysis (planned for future release)
- **Advanced Cost Optimization**: Instance Scheduler, Workspaces optimization (planned for future release)
- **Reserved Instance Management**: RI planning and optimization (planned for future release)

## Technical Requirements

### Prerequisites
- AWS Organization created and accessible
- Management account with appropriate permissions
- Email domain for account creation
- Basic understanding of AWS networking concepts

### Deployment Architecture
- **Management Account**: Control Tower, budgets, root-level policies
- **LogArchive Account**: VPC Flow Logs, S3 buckets with lifecycle policies
- **Network Account**: Transit Gateway, IPAM, centralized networking
- **Audit Account**: Security monitoring and compliance (basic setup)

### Regional Scope
- **Single Region**: Designed for single-region deployment
- **Home Region**: All resources deployed in selected home region
- **Multi-Region**: Not supported in starter configuration

## Migration Path

### From Starter to Advanced
Organizations can upgrade from starter to more advanced industry overlays as needs grow:

1. **Enterprise Overlay**: Adds advanced security services, complex logging, Identity Center
2. **US Government Overlay**: Adds compliance controls, advanced monitoring
3. **UK Public Sector Overlay**: Adds sector-specific compliance and security controls

### Expansion Capabilities
As titanium-generator capabilities expand, the starter configuration can be enhanced with:
- Advanced security services through additional CloudFormation stacks
- Enhanced monitoring through CloudWatch integration
- Identity Center configuration for centralized access management
- Network inspection capabilities through additional VPC configurations

## Success Criteria

After deployment, organizations will have:
- ✅ Multi-account structure following AWS best practices
- ✅ Basic security controls preventing common misconfigurations
- ✅ Centralized networking with Transit Gateway and IPAM
- ✅ Network security with Inspection VPC and AWS Network Firewall
- ✅ Centralized logging with VPC Flow Logs and Network Firewall logs
- ✅ Audit trail for compliance and security investigations
- ✅ Cost visibility through basic budgeting and tagging
- ✅ Foundation for scaling to more advanced configurations

## Limitations Acknowledgment

**Important**: By choosing the starter configuration, you acknowledge:
1. This is a **basic** landing zone suitable for getting started
2. Advanced security features are **not included** and must be added separately
3. Complex networking scenarios are **not supported**
4. This configuration is designed for **learning and development** environments
5. Production workloads may require additional security and monitoring capabilities

## Support and Documentation

- **Generator Compatibility**: Designed specifically for current titanium-generator capabilities
- **CloudFormation Templates**: Uses validated templates from the templates/ directory
- **Deployment Order**: Templates must be deployed in sequence (organization → network)
- **Troubleshooting**: Limited to generator-supported features only

## Next Steps

1. Complete the starter industry interview
2. Review generated `titanium.yaml` configuration
3. Use titanium-generator to create CloudFormation templates
4. Deploy templates in the recommended order
5. Validate deployment using AWS Console
6. Plan for future enhancements as generator capabilities expand
