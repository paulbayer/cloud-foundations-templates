# Security Templates Naming Convention for LLM Agent Guide

## Purpose

This document defines the naming convention used for security templates to enable the LLM Agent Guide (`llm_agent_guide.py`) to correctly identify deployment types (Stack vs StackSet) and deployment targets (Management vs Audit accounts).

## Naming Pattern

```
<order>-<service>-<deployment-type>-<target>-<action>.yaml
```

### Components

1. **order**: Two-digit number (01-08) for proper sorting
2. **service**: Service name (securityhub, guardduty)
3. **deployment-type**: `stack` or `stackset`
4. **target**: `mgmt` (management account) or `audit` (security/audit account)
5. **action**: Action performed (delegate, configure, detector, role, policy, eventbridge)

## Deployment Type Indicators

### Stack (Management Account Only)

**Pattern**: `-stack-mgmt-`

**Meaning**: CloudFormation Stack deployed ONLY to the Management Account

**Examples**:
- `01-securityhub-stack-mgmt-delegate.yaml`
- `05-guardduty-stack-mgmt-configure.yaml`
- `06-securityhub-cspm-stack-mgmt-policy.yaml`

**LLM Agent Behavior**: 
- Generates `aws cloudformation create-stack` commands
- Targets Management Account only
- No StackSet operations

### StackSet (Audit Account)

**Pattern**: `-stackset-audit-`

**Meaning**: CloudFormation StackSet deployed to the Audit/Security Account

**Examples**:
- `02-securityhub-cspm-stackset-audit-configure.yaml`
- `03-guardduty-stackset-audit-detector.yaml`
- `04-guardduty-stackset-audit-role.yaml`
- `07-securityhub-v2-stackset-audit-configure.yaml`
- `08-securityhub-stackset-audit-eventbridge.yaml`

**LLM Agent Behavior**:
- Generates `aws cloudformation create-stack-set` commands
- Generates `aws cloudformation create-stack-instances` commands
- Uses `--deployment-targets` with Audit Account ID
- Uses `--permission-model SERVICE_MANAGED`

### StackSet (Organization-Wide)

**Pattern**: `-stackset-org-`

**Meaning**: CloudFormation StackSet deployed organization-wide (all accounts)

**Examples**: (None in current security templates, but pattern is defined)

**LLM Agent Behavior**:
- Generates `aws cloudformation create-stack-set` commands
- Uses `--deployment-targets OrganizationalUnitIds=<ROOT_OU_ID>,AccountFilterType=NONE`
- Deploys to all accounts in the organization

### StackSet (Network Account)

**Pattern**: `-stackset-network-`

**Meaning**: CloudFormation StackSet deployed to the Network Account

**Examples**: (Used in network templates)
- `02-ipam-stackset-network-sharing.yaml`
- `04a-tgw-stackset-egress-vpc.yaml`
- `04b-tgw-stackset-inspection-vpc-firewall.yaml`
- `05-dns-stackset-network-resolver.yaml`
- `06-vpc-stackset-endpoint-vpc.yaml`

**LLM Agent Behavior**:
- Generates `aws cloudformation create-stack-set` commands
- Generates `aws cloudformation create-stack-instances` commands
- Uses `--deployment-targets` with Network Account ID
- Uses `--permission-model SERVICE_MANAGED`

### StackSet (Log Archive Account)

**Pattern**: `-stackset-logarchive-`

**Meaning**: CloudFormation StackSet deployed to the Log Archive Account

**Examples**: (Used in network templates)
- `03-vpc-stackset-logarchive-flowlogs-bucket.yaml`

**LLM Agent Behavior**:
- Generates `aws cloudformation create-stack-set` commands
- Generates `aws cloudformation create-stack-instances` commands
- Uses `--deployment-targets` with Log Archive Account ID
- Uses `--permission-model SERVICE_MANAGED`

## LLM Agent Guide Implementation

### Detection Method: `_is_management_account_only()`

```python
def _is_management_account_only(self, template_name: str) -> bool:
    """Determine if template should be deployed only in management account (Stack)."""
    
    # Check for explicit 'stack-mgmt' pattern (new naming convention)
    if '-stack-mgmt-' in template_name.lower():
        return True
    
    return False
```

### Detection Method: `_is_audit_account_stackset()`

```python
def _is_audit_account_stackset(self, template_name: str) -> bool:
    """Determine if template is a StackSet deployed to audit account."""
    
    # Check for explicit 'stackset-audit' pattern
    if '-stackset-audit-' in template_name.lower():
        return True
    
    return False
```

### Detection Method: `_is_network_account_stackset()`

```python
def _is_network_account_stackset(self, template_name: str) -> bool:
    """Determine if template is a StackSet deployed to network account."""
    
    # Check for explicit 'stackset-network' pattern
    if '-stackset-network-' in template_name.lower():
        return True
    
    return False
```

### Detection Method: `_is_logarchive_account_stackset()`

```python
def _is_logarchive_account_stackset(self, template_name: str) -> bool:
    """Determine if template is a StackSet deployed to log archive account."""
    
    # Check for explicit 'stackset-logarchive' pattern
    if '-stackset-logarchive-' in template_name.lower():
        return True
    
    return False
```

### Detection Method: `_is_organization_wide_stackset()`

```python
def _is_organization_wide_stackset(self, template_name: str) -> bool:
    """Determine if template is a StackSet deployed organization-wide."""
    
    # Check for explicit 'stackset-org' pattern
    if '-stackset-org-' in template_name.lower():
        return True
    
    return False
```

## Template Metadata

All templates include metadata to explicitly declare deployment characteristics:

```yaml
Metadata:
  DeploymentTarget: "Management" | "Audit" | "Organization"
  DeploymentType: "Stack" | "StackSet"
  DeploymentOrder: <number>
  Prerequisites:
    - "List of prerequisites"
```

This metadata serves as:
1. **Documentation** for human readers
2. **Validation** for the LLM agent (can cross-check naming vs metadata)
3. **Fallback** if naming pattern detection fails

## Command Generation Examples

### Stack (Management Account)

**Template**: `01-securityhub-stack-mgmt-delegate.yaml`

**Generated Commands**:
```bash
# Create stack
aws cloudformation create-stack \
  --stack-name Titanium-01-securityhub-stack-mgmt-delegate \
  --template-body file://security/01-securityhub-stack-mgmt-delegate.yaml \
  --parameters ParameterKey=uSecurityAccountId,ParameterValue=<AUDIT_ACCOUNT_ID> \
               ParameterKey=uOrganizationId,ParameterValue=<ORG_ID> \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region us-east-1

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name Titanium-01-securityhub-stack-mgmt-delegate \
  --region us-east-1
```

### StackSet (Audit Account)

**Template**: `02-securityhub-cspm-stackset-audit-configure.yaml`

**Generated Commands**:
```bash
# Create StackSet
aws cloudformation create-stack-set \
  --stack-set-name Titanium-02-securityhub-cspm-stackset-audit-configure \
  --template-body file://security/02-securityhub-cspm-stackset-audit-configure.yaml \
  --parameters ParameterKey=uRootOuId,ParameterValue=<ROOT_OU_ID> \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false \
  --region us-east-1

# Deploy to Audit Account
aws cloudformation create-stack-instances \
  --stack-set-name Titanium-02-securityhub-cspm-stackset-audit-configure \
  --deployment-targets OrganizationalUnitIds=<ROOT_OU_ID>,Accounts=<AUDIT_ACCOUNT_ID>,AccountFilterType=INTERSECTION \
  --regions us-east-1 \
  --operation-preferences MaxConcurrentPercentage=100
```

## Benefits of This Convention

1. **Immediate Clarity**: Developers can instantly see deployment type from filename
2. **LLM Agent Compatible**: Pattern-based detection works reliably
3. **Proper Sorting**: Two-digit numbering ensures correct deployment order
4. **Self-Documenting**: Filename tells the complete story
5. **Validation**: Metadata provides cross-check mechanism

## Migration from Old Naming

| Old Name | New Name | Change |
|----------|----------|--------|
| `1-securityhub-cspm-mgmt-enable-delegate.yaml` | `01-securityhub-stack-mgmt-delegate.yaml` | Added deployment-type indicator |
| `2-security-hub-cspm-org-configuration.yaml` | `02-securityhub-cspm-stackset-audit-configure.yaml` | Added deployment-type and target |
| `3-guardduty-detector-audit.yaml` | `03-guardduty-stackset-audit-detector.yaml` | Added deployment-type |
| `4-guardduty-configuration-role-audit.yaml` | `04-guardduty-stackset-audit-role.yaml` | Added deployment-type |
| `5-guardduty-configuration-lambda-mgmt.yaml` | `05-guardduty-stack-mgmt-configure.yaml` | Added deployment-type |
| `5a-securityhub-org-policy-enable.yaml` | `06-securityhub-cspm-stack-mgmt-policy.yaml` | Added deployment-type |
| `6-securityhub-integration-eventbridge.yaml` | `07-securityhub-stackset-audit-eventbridge.yaml` | Added deployment-type |

## Validation Checklist

When creating new templates, verify:

- [ ] Filename follows `<order>-<service>-<deployment-type>-<target>-<action>.yaml` pattern
- [ ] Deployment type indicator is present:
  - `stack-mgmt` for Management account Stacks
  - `stackset-audit` for Audit account StackSets
  - `stackset-network` for Network account StackSets
  - `stackset-logarchive` for Log Archive account StackSets
  - `stackset-org` for organization-wide StackSets
- [ ] Two-digit order number is used
- [ ] Metadata section includes `DeploymentTarget`, `DeploymentType`, `DeploymentOrder`
- [ ] Template name matches metadata declarations
- [ ] LLM agent guide can correctly identify deployment type

## References

- LLM Agent Guide: `titanium-generator/titanium_generator/mcp_tools/llm_agent_guide.py`
- Template Directory: `landing-zone/generated-templates/security/`
- Documentation: `README.md`, `DEPLOYMENT-ORDER.md`
