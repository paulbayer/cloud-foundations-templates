# Organization Templates - Validated Template Folder

This folder contains validated CloudFormation templates for AWS Organizations management, designed to work with the Titanium Template Modifier's organization processor.

## Naming Convention

All templates in this directory follow the standardized naming convention:

**Pattern**: `<order>-<service>-<deployment-type>-<target>-<action>.yaml`

- `order`: Two-digit number (01-99) for proper sorting
- `service`: Service name (lowercase, hyphenated)
- `deployment-type`: `stack` or `stackset`
- `target`: `mgmt` (management), `audit`, `network`, `logarchive`, or `org` (organization-wide)
- `action`: Action performed (descriptive verb or noun)

### Templates in This Directory

1. **01-organizations-stack-mgmt-ous.yaml** - Creates organizational units (OUs) in the Management account
2. **02-organizations-stack-mgmt-scps.yaml** - Deploys Service Control Policies (SCPs) in the Management account
3. **03-organizations-stack-mgmt-backup-policies.yaml** - Deploys AWS Backup Policies in the Management account
4. **04-organizations-stack-mgmt-tagging-policies.yaml** - Deploys Tagging Policies in the Management account

**Deployment Order**: Templates are numbered to ensure proper dependency sequence:
1. Deploy OUs first (01) - Creates the organizational structure
2. Deploy SCPs (02) - Attaches security policies to OUs
3. Deploy Backup Policies (03) - Attaches backup policies to OUs
4. Deploy Tagging Policies (04) - Attaches tagging policies to OUs

All policy templates depend on OUs being created first, as policies are attached to specific organizational units.

## Template Overview

### `01-organizations-stack-mgmt-ous.yaml`

CloudFormation Stack template for creating AWS Organizations organizational units. Deploys to the Management account only.

### `02-organizations-stack-mgmt-scps.yaml`

A focused CloudFormation Stack template for Service Control Policies (SCPs) with selective deployment capabilities. Deploys to the Management account only. This template supports:

#### Service Control Policies (SCPs)
- **PreventLeaveOrganization**: Prevents member accounts from leaving the organization
- **RegionRestriction**: Restricts access to specified AWS regions only
- **CloudTrailProtection**: Prevents disabling or modifying CloudTrail configuration
- **DenyPublicResources**: Denies creation of publicly accessible resources
- **DenyUserCreationNoSSO**: Prevents user creation outside of SSO
- **DenyVpcWithoutIPAM**: Prevents VPC creation without IPAM pool

### `03-organizations-stack-mgmt-backup-policies.yaml`

CloudFormation Stack template for AWS Organizations Backup Policies with selective deployment capabilities. Deploys to the Management account only. This template supports:

#### Backup Policies
Backup policies enforce backup requirements across your organization using AWS Backup. Each policy can define:

- **Backup Plans**: Scheduled backup rules with retention periods
- **Backup Schedules**: Cron expressions for backup timing (daily, weekly, monthly)
- **Lifecycle Rules**: Automatic deletion after retention period
- **Target Selection**: Resources to backup based on tags
- **Backup Vaults**: Destination vaults for backup storage
- **Cross-Region Copy**: Optional backup replication to other regions

**Common Backup Policy Examples:**
- **DailyBackup**: Daily backups with 30-day retention
- **WeeklyBackup**: Weekly backups with 90-day retention  
- **MonthlyBackup**: Monthly backups with 365-day retention

**Policy Attachment**: Backup policies can be attached to:
- Organization root (applies to all accounts)
- Specific organizational units
- Individual accounts

**Resource Selection**: Resources are selected for backup using tags. You must tag your AWS resources with the `BackupSchedule` tag to enable automatic backups:

```yaml
# Tag your resources with one of these values:
BackupSchedule: Daily    # Resources with this tag get daily backups (30-day retention)
BackupSchedule: Weekly   # Resources with this tag get weekly backups (90-day retention)
BackupSchedule: Monthly  # Resources with this tag get monthly backups (365-day retention)
```

**Example: Tagging an EC2 Instance for Daily Backups**
```bash
aws ec2 create-tags \
  --resources i-1234567890abcdef0 \
  --tags Key=BackupSchedule,Value=Daily
```

**Example: Tagging an RDS Database for Weekly Backups**
```bash
aws rds add-tags-to-resource \
  --resource-name arn:aws:rds:us-east-1:123456789012:db:mydb \
  --tags Key=BackupSchedule,Value=Weekly
```

**Supported Resources**: AWS Backup supports EC2 instances, EBS volumes, RDS databases, DynamoDB tables, EFS file systems, and more. See [AWS Backup supported resources](https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html#supported-resources) for the complete list.

### `04-organizations-stack-mgmt-tagging-policies.yaml`

CloudFormation Stack template for AWS Organizations Tagging Policies with selective deployment capabilities. Deploys to the Management account only. This template supports:

#### Tagging Policies
Tagging policies enforce tag compliance across your organization. Each policy can define:

- **Required Tags**: Tags that must be present on resources
- **Tag Values**: Allowed values for specific tag keys
- **Case Sensitivity**: Enforce consistent tag key/value casing
- **Resource Types**: Which AWS resources require tags
- **Inheritance**: Child policies can extend parent policies

**Common Tagging Policy Examples:**
- **RequiredTags**: Enforce Environment, CostCenter, Project tags
- **DataClassification**: Enforce data classification tags on sensitive resources
- **CostAllocation**: Enforce cost allocation tags for billing

**Policy Enforcement**: Tagging policies can enforce tags on:
- All resource types (`*`)
- Specific services (e.g., `ec2:instance`, `s3:bucket`, `rds:db`)
- Multiple resource types per tag

**Tag Operators**: Policies support inheritance operators:
- `@@assign`: Set tag requirements (cannot be overridden)
- `@@append`: Add additional allowed values in child policies
- `@@none`: Prevent child policies from modifying

## Parameter Structure

The template follows the Titanium specification parameter naming convention with `t`/`u` prefixes:

### Titanium-Set Parameters (t prefix)
```yaml
tDeploy[ItemName]:
  Type: String
  Default: "false"  # Modified by Titanium processor based on presence in config
  AllowedValues: ["true", "false"]
  Description: "Enable deployment of [ItemName] (Titanium-set)"

t[ItemName]Description:
  Type: String
  Default: "Description from Titanium.yaml"  # Modified by Titanium processor
  Description: "Description for [ItemName] (Titanium-set)"
```

### User-Provided Parameters (u prefix)
```yaml
u[ItemName]Targets:
  Type: CommaDelimitedList
  Default: "Root,Security"  # Modified from deploymentTargets in Titanium.yaml
  Description: "Deployment targets for [ItemName] (User-provided)"

uOrganizationId:
  Type: String
  Description: "AWS Organization ID (User-provided)"

uSSMParameterPrefix:
  Type: String
  Default: "/titanium"
  Description: "SSM parameter prefix for storing OU IDs (User-provided)"
```

### Conditional Logic
```yaml
Conditions:
  Create[ItemName]: !Equals [!Ref tDeploy[ItemName], "true"]
```

## Usage with Titanium Processor

This template is designed to work with the Titanium Template Modifier's organization processor. The processor will:

1. **Extract Configuration**: Parse the `organization` section from Titanium.yaml
2. **Generate Parameters**: Create parameters for each configured policy/resource
3. **Modify Defaults**: Update parameter default values based on Titanium.yaml content
4. **Preserve Structure**: Maintain existing conditions and resource definitions

### Example Titanium.yaml Organization Section

```yaml
organization:
  enable: true
  serviceControlPolicies:
    - name: PreventLeaveOrganization
      description: "Prevents member accounts from leaving the organization"
      policy: "service-control-policies/prevent-leave-org.json"
      type: customerManaged
      deploymentTargets:
        organizationalUnits: [Root]
    - name: RegionRestriction
      description: "Restricts access to specified AWS regions"
      policy: "service-control-policies/region-restriction.json"
      type: customerManaged
      deploymentTargets:
        organizationalUnits: [Root]
  backupPolicies:
    - name: DailyBackup
      description: "Daily backups with 30-day retention"
      policy: "backup-policies/daily-backup-30day.json"
      deploymentTargets:
        organizationalUnits: [Workloads]
    - name: WeeklyBackup
      description: "Weekly backups with 90-day retention"
      policy: "backup-policies/weekly-backup-90day.json"
      deploymentTargets:
        organizationalUnits: [Infrastructure]
  taggingPolicies:
    - name: RequiredTags
      description: "Enforces Environment, CostCenter, Project tags"
      policy: "tagging-policies/required-tags.json"
      deploymentTargets:
        organizationalUnits: [Root]
    - name: DataClassification
      description: "Enforces data classification tags"
      policy: "tagging-policies/data-classification.json"
      deploymentTargets:
        organizationalUnits: [Workloads, Infrastructure]
  organizationalUnits:
    - name: Infrastructure
      parent: Root
    - name: Security
      parent: Root
    - name: Workloads
      parent: Root
    - name: Sandbox
      parent: Root
```

### Processing Result

After processing, the template parameters would be updated:

```yaml
# Before Processing
tDeployPreventLeaveOrganization:
  Default: "false"

# After Processing
tDeployPreventLeaveOrganization:
  Default: "true"  # Updated because policy is present in Titanium.yaml

tPreventLeaveOrganizationDescription:
  Default: "Prevents member accounts from leaving the organization"  # From Titanium.yaml

uPreventLeaveOrganizationTargets:
  Default: "Root"  # From deploymentTargets in Titanium.yaml
```

## Template Features

### Automatic Policy Attachment

The template includes Lambda functions that automatically attach policies to specified organizational units and accounts:

- **PolicyAttachmentFunction**: Handles attachment/detachment of all policy types
- **EnableDeclarativePoliciesFunction**: Enables declarative policy types when needed

### Comprehensive Error Handling

- Handles duplicate policy attachments gracefully
- Provides detailed logging for troubleshooting
- Supports cleanup on stack deletion

### Flexible OU Hierarchy

- Supports nested organizational units
- Configurable parent-child relationships
- Conditional creation based on requirements

### Export Values

All resources export their IDs for cross-stack references:

```yaml
Outputs:
  InfrastructureOUId:
    Value: !Ref InfrastructureOU
    Export:
      Name: !Sub "${AWS::StackName}-InfrastructureOU-ID"
```

## Validation

The template has been validated against:

- ✅ CloudFormation template syntax
- ✅ AWS Organizations resource requirements
- ✅ IAM permissions for Lambda functions
- ✅ Parameter naming conventions
- ✅ Condition logic
- ✅ Resource dependencies

## Deployment Prerequisites

1. **AWS Organizations Setup**: Organization must be created and accessible
2. **Policy Types Enabled**: Required policy types must be enabled in the organization
3. **IAM Permissions**: Deployment role must have Organizations and Lambda permissions
4. **Organization Root ID**: Must provide the organization root ID as parameter

## Security Considerations

- Lambda functions use least-privilege IAM roles
- Policy attachments are logged for audit trails
- Supports role-based exclusions in SCPs
- Declarative policies include SSO role exceptions

## Customization

The template can be customized by:

1. **Adding New Policies**: Add new SCP/Tagging/Backup policy resources
2. **Modifying Parameters**: Adjust parameter names and defaults
3. **Extending OUs**: Add additional organizational units
4. **Custom Lambda Logic**: Modify attachment functions for specific requirements

## Integration with Other Templates

This template is designed to integrate with other Titanium templates:

- Exports OU IDs for account placement
- Provides policy IDs for cross-references
- Supports modular deployment patterns

## Troubleshooting

### Common Issues

1. **Policy Type Not Enabled**: Ensure policy types are enabled in the organization
2. **Insufficient Permissions**: Verify Lambda execution role has required permissions
3. **Circular Dependencies**: Check OU parent-child relationships
4. **Parameter Conflicts**: Ensure parameter names don't conflict with reserved words

### Debugging

- Check CloudWatch logs for Lambda function execution details
- Use AWS CLI to verify policy attachments: `aws organizations list-policies-for-target`
- Validate organization structure: `aws organizations list-organizational-units-for-parent`

## Version History

- **v1.0**: Initial comprehensive template with all organization features
- Supports: SCPs, Tagging Policies, Backup Policies, OUs, Declarative Policies
- Compatible with: Titanium Template Modifier v1.0+
