# Control Tower Templates

This directory contains CloudFormation templates for deploying AWS Control Tower in the management account.

## Naming Convention

All templates follow the standardized naming pattern:
`<order>-<service>-<deployment-type>-<target>-<action>.yaml`

Where:
- `order`: Two-digit number (01-99) for proper sorting
- `service`: Service name (lowercase, hyphenated)
- `deployment-type`: `stack` (CloudFormation Stack) or `stackset` (CloudFormation StackSet)
- `target`: `mgmt` (management account)
- `action`: Action performed (descriptive verb or noun)

## Templates

### 01-controltower-stack-mgmt-setup.yaml
- **Purpose**: Deploys AWS Control Tower with prerequisites including Organizations, IAM roles, and landing zone configuration
- **Deployment Type**: CloudFormation Stack
- **Deployment Target**: Management account only
- **Dependencies**: 
  - AWS Organizations must be available (created by this template)
  - Bootstrap templates should be deployed first (Config role, StackSets integration)
- **Key Resources**:
  - AWS Organizations with ALL features enabled
  - Logging and Security accounts
  - Control Tower IAM roles (Admin, CloudTrail, Config Aggregator, StackSet)
  - Control Tower Landing Zone with centralized logging and security configuration

## Deployment Order

1. **Deploy Control Tower Setup** (`01-controltower-stack-mgmt-setup.yaml`)
   - Deploy directly to management account
   - Creates Organizations, accounts, IAM roles, and Control Tower landing zone
   - This is typically the first major infrastructure deployment after bootstrap

## Deployment Methods

### Direct Deployment to Management Account

The template is deployed as a CloudFormation Stack directly to the management account:

```bash
aws cloudformation create-stack \
  --stack-name ControlTower-Setup-prod \
  --template-body file://01-controltower-stack-mgmt-setup.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=uLoggingAccountEmail,ParameterValue=logging@example.com \
    ParameterKey=uLoggingAccountName,ParameterValue=LogArchive \
    ParameterKey=uSecurityAccountEmail,ParameterValue=security@example.com \
    ParameterKey=uSecurityAccountName,ParameterValue=Audit \
    ParameterKey=tVersion,ParameterValue=4.0 \
    ParameterKey=tGovernedRegions,ParameterValue=us-east-1 \
    ParameterKey=tSecurityOuName,ParameterValue=Security \
    ParameterKey=tSandboxOuName,ParameterValue=Sandbox \
    ParameterKey=tLoggingBucketRetentionPeriod,ParameterValue=365 \
    ParameterKey=tAccessLoggingBucketRetentionPeriod,ParameterValue=365

# Wait for completion (this can take 30-60 minutes)
aws cloudformation wait stack-create-complete \
  --stack-name ControlTower-Setup-prod
```

## Configuration Integration

This template integrates with the Titanium Control Tower configuration section:

```yaml
controlTower:
  enabled: true
  version: "4.0"
  governedRegions:
    - us-east-1
  loggingAccount:
    email: "logging@example.com"
    name: "LogArchive"
  securityAccount:
    email: "security@example.com"
    name: "Audit"
  organizationalUnits:
    security:
      name: "Security"
    sandbox:
      name: "Sandbox"
  centralizedLogging:
    enabled: true
    loggingBucketRetentionDays: 365
    accessLoggingBucketRetentionDays: 365
  accessManagement:
    enabled: true
```

## Template Parameters

### Required Parameters:
- `uLoggingAccountEmail`: Email address for the centralized logging account (must be unique)
- `uLoggingAccountName`: Name for the logging account (default: "LogArchive")
- `uSecurityAccountEmail`: Email address for the security/audit account (must be unique)
- `uSecurityAccountName`: Name for the security account (default: "Audit")

### Optional Parameters:
- `tVersion`: Control Tower landing zone version (default: "4.0")
- `tGovernedRegions`: Comma-delimited list of AWS regions to govern (default: "us-east-1")
- `tSecurityOuName`: Name for the Security organizational unit (default: "Security")
- `tSandboxOuName`: Name for the Sandbox organizational unit (default: "Sandbox")
- `tLoggingBucketRetentionPeriod`: Retention period in days for centralized logging bucket (required)
- `tAccessLoggingBucketRetentionPeriod`: Retention period in days for access logging bucket (required)

## IAM Roles Created

The template creates the following IAM roles required by Control Tower:

1. **AWSControlTowerAdmin**: Service role for Control Tower operations
   - Managed policy: AWSControlTowerServiceRolePolicy
   - Additional permissions: EC2 DescribeAvailabilityZones

2. **AWSControlTowerCloudTrailRole**: Role for CloudTrail log delivery
   - Permissions: CreateLogStream, PutLogEvents to Control Tower log groups

3. **AWSControlTowerConfigAggregatorRoleForOrganizations**: Role for Config aggregation
   - Managed policy: AWSConfigRoleForOrganizations

4. **AWSControlTowerStackSetRole**: Role for StackSet operations
   - Permissions: AssumeRole to AWSControlTowerExecution role in member accounts

## Resources Created

- **AWS Organizations**: Organization with ALL features enabled
- **Logging Account**: Dedicated account for centralized logging
- **Security Account**: Dedicated account for security and audit functions
- **Control Tower Landing Zone**: Configured with:
  - Governed regions
  - Organizational structure (Security and Sandbox OUs)
  - Centralized logging with configurable retention
  - Security roles and access management

## Outputs

- `oLogAccountId`: Account ID of the created logging account (exported as "LogAccountId")
- `oSecurityAccountId`: Account ID of the created security account (exported as "SecurityAccountId")

## Security Considerations

- **Email Addresses**: Must be unique and not associated with any existing AWS accounts
- **IAM Roles**: Follow AWS Control Tower best practices with service-specific roles
- **Centralized Logging**: All CloudTrail logs centralized in dedicated logging account
- **Access Management**: Identity Center (AWS SSO) enabled for centralized access
- **Tagging**: Resources tagged for governance and cost allocation

## Deployment Time

Control Tower deployment typically takes 30-60 minutes. The stack will:
1. Create AWS Organizations
2. Create logging and security accounts
3. Set up IAM roles
4. Deploy Control Tower landing zone
5. Configure guardrails and baseline controls

## Troubleshooting

### Common Issues:

1. **Email Already in Use**: Ensure email addresses are unique and not used by existing AWS accounts
2. **Organization is a prerequisite**: This template does **not** create the AWS Organization — Control Tower requires a pre-existing organization (management account, all features enabled). Supply its Root ID via the `uOrganizationRootId` parameter (`aws organizations list-roots --query 'Roots[0].Id' --output text`); the hub OU is created under that root.
3. **Insufficient Permissions**: Deploying user needs full admin permissions in management account
4. **Region Availability**: Ensure Control Tower is available in your chosen regions
5. **Account Limits**: Check AWS account limits before creating new accounts

### Verification:

```bash
# Verify Organizations
aws organizations describe-organization

# Verify Control Tower landing zone
aws controltower list-landing-zones

# Verify created accounts
aws organizations list-accounts

# Check IAM roles
aws iam get-role --role-name AWSControlTowerAdmin
aws iam get-role --role-name AWSControlTowerCloudTrailRole
aws iam get-role --role-name AWSControlTowerConfigAggregatorRoleForOrganizations
aws iam get-role --role-name AWSControlTowerStackSetRole
```

## Next Steps

After deploying Control Tower:

1. **Access Identity Center**: Configure AWS IAM Identity Center (SSO) for user access
2. **Create Additional OUs**: Define organizational unit structure beyond Security and Sandbox
3. **Deploy Guardrails**: Enable additional Control Tower guardrails as needed
4. **Account Factory**: Set up Account Factory for automated account provisioning
5. **Network Infrastructure**: Deploy network templates using StackSets
6. **Security Baseline**: Deploy security templates to audit account
7. **Service Control Policies**: Apply SCPs to organizational units

## References

- [AWS Control Tower User Guide](https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html)
- [Control Tower Landing Zone](https://docs.aws.amazon.com/controltower/latest/userguide/landing-zone.html)
- [Control Tower IAM Roles](https://docs.aws.amazon.com/controltower/latest/userguide/roles-how.html)
- [AWS Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_introduction.html)
- [Control Tower Best Practices](https://docs.aws.amazon.com/controltower/latest/userguide/best-practices.html)
