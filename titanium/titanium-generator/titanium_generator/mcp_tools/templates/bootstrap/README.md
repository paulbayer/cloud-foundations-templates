# Bootstrap Templates

This directory contains CloudFormation templates for bootstrapping AWS infrastructure deployment capabilities in the management account.

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

### 01-config-stack-mgmt-role.yaml
- **Purpose**: Creates AWS Config recorder IAM role in the management account
- **Deployment Type**: CloudFormation Stack
- **Deployment Target**: Management account only
- **Dependencies**: None
- **Key Resources**: ConfigRecorderRole with AWS_ConfigRole and ReadOnlyAccess policies

### 02-stacksets-stack-mgmt-enable.yaml
- **Purpose**: Enables AWS Organizations integration for CloudFormation StackSets
- **Deployment Type**: CloudFormation Stack
- **Deployment Target**: Management account only
- **Dependencies**: AWS Organizations must be enabled
- **Key Resources**: Lambda functions to activate Organizations access for StackSets
- **Note**: Replaces manual StackSet administration/execution role creation with service-managed permissions

## Deployment Order

1. **Deploy Config Role** (`01-config-stack-mgmt-role.yaml`)
   - Deploy directly to management account
   - Creates IAM role for AWS Config service
   - Required for Config-based compliance monitoring

2. **Enable StackSets Organizations Integration** (`02-stacksets-stack-mgmt-enable.yaml`)
   - Deploy directly to management account
   - Enables service-managed StackSet permissions
   - Required before deploying any StackSets with Organizations integration

## Deployment Methods

### Direct Deployment to Management Account

Both templates are deployed as CloudFormation Stacks directly to the management account:

```bash
# Step 1: Deploy Config Role
aws cloudformation create-stack \
  --stack-name ConfigRecorderRole-prod \
  --template-body file://01-config-stack-mgmt-role.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters ParameterKey=uConfigRecorderRoleName,ParameterValue=Management-ConfigRecorderRole

# Step 2: Enable StackSets Organizations Integration
aws cloudformation create-stack \
  --stack-name StackSetsOrganizationsIntegration-prod \
  --template-body file://02-stacksets-stack-mgmt-enable.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters ParameterKey=uEnableStackSetsOrganizationsIntegration,ParameterValue=true \
              ParameterKey=uEnableAutoDeployment,ParameterValue=true \
              ParameterKey=uEnvironment,ParameterValue=production
```

### Service-Managed StackSets

After enabling Organizations integration with `02-stacksets-stack-mgmt-enable.yaml`, you can deploy StackSets using service-managed permissions:

```bash
aws cloudformation create-stack-set \
  --stack-set-name MyStackSet \
  --template-body file://my-template.yaml \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false \
  --capabilities CAPABILITY_NAMED_IAM

aws cloudformation create-stack-instances \
  --stack-set-name MyStackSet \
  --deployment-targets OrganizationalUnitIds=ou-xxxx-xxxxxxxx \
  --regions us-west-2
```

## Configuration Integration

These templates integrate with the Titanium bootstrap configuration section:

```yaml
bootstrap:
  enabled: true
  configRole:
    enabled: true
    roleName: "Management-ConfigRecorderRole"
  stackSetsOrganizationsIntegration:
    enabled: true
    autoDeployment: true
    retainStacksOnAccountRemoval: false
    environment: "production"
```

## Template Parameters

### 01-config-stack-mgmt-role.yaml Parameters:
- `uConfigRecorderRoleName`: Name of Config recorder role (default: "Management-ConfigRecorderRole")

### 02-stacksets-stack-mgmt-enable.yaml Parameters:
- `uEnableStackSetsOrganizationsIntegration`: Enable/disable integration (default: "true")
- `uEnableAutoDeployment`: Auto-deploy to new accounts in target OUs (default: "true")
- `uRetainStacksOnAccountRemoval`: Retain stacks when accounts removed from OUs (default: "false")
- `uEnvironment`: Environment name for tagging (default: "production")

## Security Considerations

- **Config Role Permissions**: Uses AWS managed policies (AWS_ConfigRole and ReadOnlyAccess)
- **Service-Managed Permissions**: StackSets Organizations integration uses AWS-managed service roles
- **Lambda Execution**: Lambda functions have minimal permissions for Organizations API calls
- **Tagging**: All resources tagged for governance and cost allocation

## Troubleshooting

### Common Issues:

1. **Config Role Already Exists**: Delete existing role or use different name via parameter
2. **Organizations Not Enabled**: Enable AWS Organizations before deploying StackSets integration
3. **Permissions**: Ensure deploying user has IAM and Lambda permissions
4. **Integration Validation**: Check Lambda logs if integration validation fails

### Verification:

```bash
# Verify Config role
aws iam get-role --role-name Management-ConfigRecorderRole

# Verify StackSets Organizations integration
aws organizations list-aws-service-access-for-organization \
  --query 'EnabledServicePrincipals[?ServicePrincipal==`stacksets.cloudformation.amazonaws.com`]'

# Check CloudFormation StackSets Organizations access
aws cloudformation describe-organizations-access
```

## Next Steps

After deploying these bootstrap templates:

1. **Deploy Control Tower**: Set up AWS Control Tower for account governance
2. **Create Organizational Units**: Define OU structure for account organization
3. **Deploy Network Infrastructure**: Use StackSets for network templates
4. **Configure Security**: Deploy security baseline templates via StackSets
5. **Set Up Monitoring**: Configure CloudTrail and Config for compliance monitoring

## References

- [AWS Config IAM Roles](https://docs.aws.amazon.com/config/latest/developerguide/iamrole-permissions.html)
- [StackSets with AWS Organizations](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-orgs-enable-trusted-access.html)
- [Service-Managed StackSet Permissions](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-concepts.html#stacksets-concepts-service-managed-permissions)
