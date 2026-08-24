# Starter Industry Overlay

## Overview

The **Starter** industry overlay provides a basic AWS Landing Zone configuration designed specifically for organizations getting started with multi-account AWS environments. This overlay includes only features that are currently supported by the titanium-generator for immediate CloudFormation deployment.

## Key Features

### ✅ What's Included
- **Basic Organization Structure**: Security, Infrastructure, Workloads, and Sandbox OUs
- **Essential Security Policies**: Prevent account leaving, public S3 buckets, and region restrictions  
- **Transit Gateway Networking**: Centralized networking with IPAM and segregated routing
- **VPC Flow Logs**: Network traffic monitoring to S3
- **Basic Cost Management**: Monthly budgets with email alerts
- **Account Structure**: Management, LogArchive, Audit, Network, and SharedServices accounts

### ❌ What's Not Included
- Advanced security services (GuardDuty, Security Hub, Macie)
- CloudWatch metrics and alarms
- Identity Center (SSO) configuration
- Network inspection capabilities
- Advanced logging beyond VPC Flow Logs
- Cost optimization tools

## Quick Start

### 1. Run the Interview
The interview process will gather basic information about your organization and requirements:

```bash
# Example interview responses for starter industry
Organization Name: Acme Corp
Home Region: us-east-1
Email Domain: acme-corp.com
Organization Size: Small (< 50 people)
AWS Experience: Beginner
```

### 2. Generated Configuration
The interview will produce a `titanium.yaml` file with:
- 4 Organizational Units
- 2 Service Control Policies  
- Basic tagging policies
- Transit Gateway networking
- VPC Flow Logs configuration
- 5 AWS accounts (3 mandatory + 2 infrastructure)

### 3. CloudFormation Generation
Use titanium-generator to create CloudFormation templates:

```bash
python titanium-generator/main.py --input titanium.yaml --output ./cloudformation-templates/
```

### 4. Deployment
Deploy templates in the correct order:
1. Organization template (SCPs, OUs, tagging policies)
2. Network templates (IPAM, VPC Flow Logs bucket, Transit Gateway)

## File Structure

```
titanium-advisor/industry-overlays/starter/
├── README.md                          # This file
├── questions.json                      # Structured interview questions with validation
├── pattern.json                        # Template variables and configuration
├── requirements/
│   └── starter.md                      # Detailed requirements and limitations
└── output-examples/
    └── starter-example.yaml            # Example generated titanium.yaml
```

## Target Audience

### Perfect For:
- Organizations new to AWS Landing Zones
- Small to medium teams (< 500 people)
- Development and testing environments
- Teams wanting quick deployment over advanced features
- Organizations that need a foundation to build upon

### Not Suitable For:
- Large enterprises requiring advanced security
- Organizations needing complex compliance frameworks
- Production workloads requiring advanced monitoring
- Teams needing hybrid connectivity (Direct Connect, VPN)

## Interview Process

The starter interview uses a **structured question format** (`questions.json`) with tracked progress and validation:

### Interview Workflow
1. Start interview session with MCP tool: `start_interview('starter')`
2. AI guides you through 11 sections using `get_section_quick_mode()`
3. For each section, AI explains options and presents defaults
4. Confirm selections before recording with `bulk_record_answers()`
5. Generate validated configuration with `generate_deterministic_titanium_config()`

### Interview Sections
1. **Basic Information** - Organization name, region, size, experience
2. **Account Structure** - Infrastructure accounts and OUs
3. **Security and Governance** - SCPs and allowed regions
4. **Tagging Requirements** - Tag enforcement policies
5. **Backup Policies** - Automated backup configuration
6. **Network Architecture** - VPC settings and availability zones
7. **Network Security** - Inspection VPC and firewall
8. **Logging and Monitoring** - Flow logs and retention
9. **Cost Management** - Budgets and alerts
10. **Email Addresses** - Account email configuration
11. **Deployment Confirmation** - Final review

**Total Time**: ~15 minutes with AI guidance (vs manual 45-60 minutes for enterprise overlay)

### Benefits of Structured Interview
- ✅ **Progress tracking**: See what's complete and what's remaining
- ✅ **Validation**: Questions have type checking and required field enforcement
- ✅ **Defaults**: Smart defaults for starter use cases
- ✅ **Conditional logic**: Questions adapt based on your answers
- ✅ **AI guidance**: LLM explains each option and why it matters

## Generated Resources

### AWS Accounts Created:
- **Management**: Your existing account becomes the management account
- **LogArchive**: Centralized logging (VPC Flow Logs, audit trails)
- **Audit**: Security monitoring and compliance
- **Network**: Transit Gateway, IPAM, centralized networking  
- **SharedServices**: Shared resources like DNS, Active Directory

### Networking Architecture:
- **Transit Gateway**: Central hub for all VPC connectivity
- **IPAM**: Automated IP address management across accounts
- **Workload VPCs**: Automatically created in Workloads OU accounts
- **VPC Flow Logs**: Network traffic monitoring for security

### Security Controls:
- **SCPs**: Prevent account leaving, public S3 buckets
- **Tagging Policies**: Enforce cost allocation and governance tags
- **Control Tower**: Basic security guardrails and compliance

## Limitations and Migration Path

### Current Limitations:
- Single region deployment only
- No advanced security services
- Basic networking (no inspection or endpoints)
- Limited cost management features
- No Identity Center integration

### Migration Options:
As your needs grow, you can:

1. **Expand Manually**: Add CloudFormation stacks for advanced features
2. **Upgrade to Enterprise**: Migrate to enterprise industry overlay
3. **Wait for Updates**: Features will be added as generator capabilities expand

## Support and Troubleshooting

### Compatible With:
- ✅ Current titanium-generator organization processor
- ✅ Current titanium-generator network processor  
- ✅ CloudFormation templates in templates/ directory

### Common Issues:
- **Template Not Found**: Ensure you're using supported features only
- **Deployment Failures**: Deploy templates in the correct order (org → network)
- **Missing Features**: Check limitations - many features are not yet supported

### Getting Help:
- Review the requirements/starter.md file for detailed limitations
- Check output-examples/starter-example.yaml for expected configuration
- Ensure titanium-generator is up to date

## Example Output

See `output-examples/starter-example.yaml` for a complete example of what this industry overlay generates. The example shows:

- Complete organization structure with 4 OUs
- Service Control Policies for basic security
- Transit Gateway networking configuration
- VPC Flow Logs setup
- Basic cost management with budgets
- All required account definitions

## Next Steps

### Using the MCP Server (Recommended)
1. **Start Interview**: Use the Titanium Advisor MCP server tool `start_interview('starter')`
2. **Complete Sections**: Work through each section with AI guidance
3. **Review Configuration**: Examine the generated `Titanium.yaml` file
4. **Generate Templates**: Use titanium-generator to create CloudFormation
5. **Deploy Infrastructure**: Follow deployment order documentation
6. **Plan Expansion**: Consider future requirements and migration path

### Manual Configuration (Alternative)
If not using the MCP server, you can:
1. Reference `questions.json` for required configuration values
2. Manually create a `Titanium.yaml` following the schema
3. Use `output-examples/starter-example.yaml` as a template

The starter configuration provides a solid foundation that can grow with your organization's needs while ensuring you have a working AWS Landing Zone from day one.
