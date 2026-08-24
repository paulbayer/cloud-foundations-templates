# Organizational Units Template - README

This template creates AWS Organizational Units (OUs) and enrolls them into the Control Tower landing zone in the same stack. Creating an OU with AWS Organizations alone leaves it ungoverned, so creation and enrollment are never separated.

## Overview

**Template**: `01-organizations-stack-mgmt-ous.yaml`  
**Purpose**: Create organizational units and register them with Control Tower  
**Deployment**: Management account only (regular CloudFormation stack, NOT StackSet)  
**Requires**: A deployed Control Tower landing zone (`controltower/01-...`)  
**Integration**: Works with `02-...-scps.yaml` via SSM Parameter Store

## Key Features

- ✅ **Automatic Root Discovery**: Custom Lambda resource discovers the Organization Root ID
- ✅ **Generated OUs**: One OU per entry in `organization.organizationalUnits` — the count is not fixed by the template
- ✅ **Control Tower Enrollment**: The discovery Lambda adopts-or-enables each OU's Control Tower baseline (issue #91), so it is governed without non-idempotent `AWS::ControlTower::EnabledBaseline` resources
- ✅ **SSM Parameter Export**: The discovery Lambda writes one OU-ID SSM parameter per OU for cross-template reference
- ✅ **CloudFormation Exports**: Stack exports for cross-stack references
- ✅ **Hub OU Discovery**: Looks up the Control Tower-created hub OU and publishes its ID on the same path convention
- ✅ **Flat Structure**: Simple flat OU hierarchy under Organization Root

## Supported Organizational Units

OUs are generated from `organization.organizationalUnits`, so any set can be
configured. The reference architecture uses:

| OU Name | Purpose | Created by |
|---------|---------|-----------|
| **Security** (hub) | Log Archive and Audit accounts | Control Tower manifest — **not this template** |
| **Infrastructure** | Shared services and networking | This template |
| **Workloads** | Application and workload accounts | This template |
| **Sandbox** | Experimentation and development | This template |
| **Exceptions** | Accounts requiring policy exceptions | This template |

**The hub OU is excluded from generation.** Landing Zone 4.0 requires the accounts used
for service integration to share one OU directly under the root, and that OU is declared
in the Control Tower manifest. Creating it here as well would collide on the OU name, so
this template discovers it by name (`uHubOuName`) instead and publishes its ID to SSM
alongside the OUs it does own.

Under Landing Zone 4.0 there is no `organizationStructure` block, so Sandbox is not
special — it is created and enrolled by this template like any other OU.

## Parameters

OUs are no longer toggled by parameter. The previous `tCreateSecurityOU` /
`tSecurityOUName` pairs are gone: they capped the template at five OUs, and because no
processor ever set them they all defaulted to `"false"`, which excluded every OU while
`DependsOn` still referenced them and failed the stack at validation. OU resources are
generated instead.

### User-Provided Parameters (u prefix)
```yaml
uSSMParameterPrefix:
  Type: String
  Default: "/titanium/organization/ou-ids"
  Description: "SSM Parameter Store path prefix for OU ID exports (User-provided)"

uHubOuName:
  Type: String
  Default: "Security"
  Description: "Name of the Control Tower-created hub OU to discover and publish"
```

`uHubOuName` must match the hub OU name in the Control Tower manifest. The generator sets
its default from `controltower.organizationStructure`.

## Template Processing by Titanium Generator

### Input (Titanium.yaml)
```yaml
organization:
  enable: true
  organizationalUnits:
    - name: Security
    - name: Infrastructure  
    - name: Workloads
    - name: Sandbox
    - name: Exceptions
```

### Output (Generated Template)

The generator does **not** emit native resources per OU. It populates the discovery
Lambda's `OrganizationalUnits` input (one `{Name, LogicalId}` entry per OU) and one
output per OU; the `generated-organizational-units` region is left as an explanatory
comment. The OUs themselves, their SSM ID parameters, and their Control Tower baseline
enrollment are all handled at deploy time by the discovery Lambda — see below.

```yaml
      # In OrganizationRootDiscovery.Properties (generated-ou-list region):
      OrganizationalUnits:
        - Name: 'Workloads'
          LogicalId: 'Workloads'

  # In the Outputs section (generated-ou-outputs region):
  WorkloadsOuId:
    Description: 'Workloads OU ID'
    Value: !GetAtt OrganizationRootDiscovery.WorkloadsOuId
    Export:
      Name: !Sub '${AWS::StackName}-WorkloadsOU-ID'
```

At deploy time, for each entry the discovery Lambda:
- **adopts-or-creates** the OU (adopt an existing OU by name under the root, else
  create it) and writes its ID to `${uSSMParameterPrefix}/<slug>-ou-id` (issue #78);
- **adopts-or-enables** the Control Tower baseline: if the OU is already enrolled it is
  left as-is, otherwise the Lambda fires `EnableBaseline` without waiting for it to
  finish (issue #91). Native `AWS::ControlTower::EnabledBaseline` resources are **not**
  used because they always CREATE and fail with `AlreadyExists` on an already-enrolled
  OU, rolling back the whole stack. The `IdentityCenterEnabledBaselineArn` parameter is
  attached only when the Lambda discovers that Control Tower manages Identity Center.

`Security` is absent from the output because it is the hub OU, created by Control Tower.

OU names are slugged for the SSM path rather than lowercased, since AWS Organizations
permits spaces and punctuation that SSM parameter names reject.

## Deployment Workflow

### 1. Template Processing
```bash
# Process template with titanium-generator
python -m titanium_generator process \
  --titanium-config Titanium.yaml \
  --template-dir templates/organization \
  --output-dir modified-templates/organization
```

### 2. Stack Deployment
```bash
# Deploy to management account only
aws cloudformation create-stack \
  --stack-name LandingZone-OrganizationalUnits \
  --template-body file://modified-templates/organization/organizational-units.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-west-2 \
  --profile management-account
```

### 3. Verify Control Tower Enrollment

Enrollment is fired by the discovery Lambda during step 2, asynchronously (issue #91).
**Do not run `enable-baseline` or use the "Enroll OU" console button** — the Lambda
enrolls (or adopts) the OUs, and running `enable-baseline` on an already-enrolled OU
fails. Because enrollment is async and Control Tower serializes baseline operations, an
OU may still be `IN_PROGRESS`, or not yet started, when the stack completes; re-running
this template is idempotent and re-attempts any missing OU.

```bash
# Every OU should report SUCCEEDED
aws controltower list-enabled-baselines \
  --query 'enabledBaselines[].{Target:targetIdentifier,Status:statusSummary.status}' \
  --output table
```

Verify before deploying SCPs: a policy attached to an OU that Control Tower has not
baselined is not enforced by the landing zone. If an OU is missing or failed, read the
stack events rather than enrolling by hand — the stack is the source of truth.

### 4. Deploy Service Control Policies
```bash
# Now deploy SCPs using the created OUs
aws cloudformation create-stack-set \
  --stack-set-name LandingZone-ServiceControlPolicies \
  --template-body file://modified-templates/organization/service-control-policies.yaml \
  --permission-model SERVICE_MANAGED
```

## SSM Parameter Store Integration

### Exported Parameters
For each created OU, the template stores its ID in SSM Parameter Store:

```
/titanium/organization/ou-ids/security-ou-id = "ou-root-1234567890"
/titanium/organization/ou-ids/infrastructure-ou-id = "ou-root-0987654321"
/titanium/organization/ou-ids/workloads-ou-id = "ou-root-1122334455"
/titanium/organization/ou-ids/sandbox-ou-id = "ou-root-5566778899"
/titanium/organization/ou-ids/exceptions-ou-id = "ou-root-9988776655"
```

### Usage in Other Templates
The `service-control-policies.yaml` template can reference these parameters:

```yaml
Parameters:
  SSMParameterPrefix:
    Type: String
    Default: "/titanium/organization/ou-ids"

Resources:
  PolicyAttachmentFunction:
    Type: AWS::Lambda::Function
    Properties:
      Code:
        ZipFile: |
          import boto3
          ssm = boto3.client('ssm')
          
          # Get OU ID from SSM
          security_ou_id = ssm.get_parameter(
              Name='/titanium/organization/ou-ids/security-ou-id'
          )['Parameter']['Value']
```

## CloudFormation Exports

### Stack Exports
```yaml
Outputs:
  SecurityOUId:
    Description: 'Security OU ID'
    Value: !Ref SecurityOU
    Export:
      Name: !Sub '${AWS::StackName}-SecurityOU-ID'

  OrganizationRootId:
    Description: 'Organization Root ID'
    Value: !GetAtt OrganizationRootDiscovery.RootId
    Export:
      Name: !Sub '${AWS::StackName}-OrganizationRootId'
```

### Cross-Stack References
```yaml
# In other templates
SecurityOUId: !ImportValue 'LandingZone-OrganizationalUnits-SecurityOU-ID'
```

## Lambda Functions

There is one Lambda-backed custom resource. OU IDs are published by native
`AWS::SSM::Parameter` resources rather than by a Lambda, which restores drift detection
and attributes a failure to the specific OU that caused it.

### Organization Discovery
- **Purpose**: Discover the Organization Root ID, locate the Control Tower hub OU,
  resolve the Identity Center enabled-baseline ARN, adopt-or-create each configured OU,
  and adopt-or-enable each OU's Control Tower baseline (issue #91)
- **Runtime**: Python 3.13
- **Permissions**: `organizations:ListRoots`, `organizations:DescribeOrganization`,
  `organizations:ListOrganizationalUnitsForParent`, `organizations:CreateOrganizationalUnit`,
  `controltower:ListEnabledBaselines`, `controltower:ListBaselines`,
  `controltower:EnableBaseline`, `ssm:PutParameter`, `ssm:DeleteParameter`,
  `ssm:GetParameter`
- **Output**: `RootId`, `OrganizationId`, `HubOuId`,
  `IdentityCenterEnabledBaselineArn`, `<LogicalId>OuId` per OU; root, hub, and per-OU IDs
  written to SSM

The Identity Center ARN is resolved here rather than passed in as a parameter because it
embeds the management account ID. It resolves to an empty string when Control Tower is
not managing Identity Center, in which case the Lambda omits the
`IdentityCenterEnabledBaselineArn` parameter when it calls `EnableBaseline`.

## Validation Commands

### Verify OU Creation
```bash
# List all OUs under root
aws organizations list-organizational-units-for-parent \
  --parent-id $(aws organizations list-roots --query 'Roots[0].Id' --output text)

# Check specific OU
aws organizations describe-organizational-unit \
  --organizational-unit-id $(aws ssm get-parameter --name "/titanium/organization/ou-ids/security-ou-id" --query 'Parameter.Value' --output text)
```

### Verify SSM Parameters
```bash
# List all OU ID parameters
aws ssm get-parameters-by-path \
  --path "/titanium/organization/ou-ids" \
  --recursive

# Get specific OU ID
aws ssm get-parameter \
  --name "/titanium/organization/ou-ids/security-ou-id" \
  --query 'Parameter.Value' \
  --output text
```

### Verify Control Tower Enrollment
```bash
# Check for Control Tower guardrails (indicates enrollment)
aws controltower list-enabled-controls \
  --target-identifier $(aws ssm get-parameter --name "/titanium/organization/ou-ids/security-ou-id" --query 'Parameter.Value' --output text)
```

## Integration with Service Control Policies Template

The `service-control-policies.yaml` template has been updated to work with SSM parameters:

### Enhanced Parameters
```yaml
# SSM Parameter Store path for OU IDs (User-provided)
uSSMParameterPrefix:
  Type: String
  Default: "/titanium/organization/ou-ids"
  Description: "SSM Parameter Store path prefix where OU IDs are stored (User-provided)"

# Updated target parameters support OU names that get resolved to IDs (User-provided)
uPreventLeaveOrganizationTargets:
  Type: CommaDelimitedList
  Default: ""
  Description: "Deployment targets (comma-separated OU IDs or names) (User-provided)"
```

### Lambda Resolution
The policy attachment Lambda function can resolve OU names to IDs using SSM:

```python
# Resolve OU name to ID
if target.startswith('ou-'):
    # Already an OU ID
    target_id = target
else:
    # Look up OU ID from SSM
    param_name = f"{ssm_prefix}/{target.lower()}-ou-id"
    target_id = ssm.get_parameter(Name=param_name)['Parameter']['Value']
```

## Error Handling

### Common Issues

1. **Organization Not Enabled**
   ```
   Error: AWS Organizations is not enabled
   ```
   **Solution**: Enable AWS Organizations in the management account

2. **Root Discovery Fails**
   ```
   Error: No organization roots found
   ```
   **Solution**: Verify Organizations is properly configured

3. **SSM Parameter Creation Fails**
   ```
   Error: Access denied to SSM Parameter Store
   ```
   **Solution**: Verify Lambda IAM permissions for SSM

4. **Control Tower Enrollment Issues**
   ```
   Manual Step: OU not showing "Enrolled" status
   ```
   **Solution**: Check Control Tower console for enrollment errors

### Troubleshooting Commands

```bash
# Check Organizations status
aws organizations describe-organization

# Verify Lambda function logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/Titanium"

# Check stack events for errors
aws cloudformation describe-stack-events \
  --stack-name LandingZone-OrganizationalUnits
```

## Security Considerations

- **Least Privilege**: Lambda functions use minimal required permissions
- **Parameter Store**: SSM parameters are tagged and organized for easy management
- **Control Tower Ready**: OUs are tagged for easy identification in Control Tower
- **Cleanup**: SSM parameters are automatically cleaned up on stack deletion

## Best Practices

1. **Deploy First**: Always deploy this template before SCPs
2. **Manual Enrollment**: Complete Control Tower enrollment before SCP deployment
3. **Validation**: Verify OU creation and enrollment before proceeding
4. **Parameter Naming**: Use consistent SSM parameter naming conventions
5. **Tagging**: Maintain consistent resource tagging for management

## Version Compatibility

- **AWS CloudFormation**: All regions
- **AWS Organizations**: Required
- **AWS Control Tower**: Optional but recommended
- **Python Runtime**: 3.9+ for Lambda functions
- **Titanium Generator**: v1.0+

## Support

For issues with this template:
1. Check deployment guide validation steps
2. Verify CloudFormation stack events
3. Review Lambda function logs
4. Validate Organizations and Control Tower status

---

**Next Steps**: After successful deployment and Control Tower enrollment, proceed with `service-control-policies.yaml` deployment for complete organization governance.
