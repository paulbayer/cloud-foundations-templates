# AWS Organizations Policy Examples

This directory contains example policy JSON files for AWS Organizations Backup Policies and Tagging Policies. These examples can be used as templates for creating your own policies in Titanium.yaml configurations.

## Directory Structure

```
policy-examples/
├── backup-policies/
│   ├── daily-backup-30day.json
│   ├── weekly-backup-90day.json
│   └── monthly-backup-365day.json
└── tagging-policies/
    ├── required-tags.json
    ├── optional-tags.json
    └── data-classification.json
```

## Backup Policies

Backup policies define automated backup schedules and retention rules for resources across your organization.

### daily-backup-30day.json
- **Schedule**: Daily at 5:00 AM UTC
- **Retention**: 30 days
- **Target Resources**: Resources tagged with `BackupSchedule: Daily`
- **Use Case**: Frequent backups for critical resources with short-term retention needs

### weekly-backup-90day.json
- **Schedule**: Weekly on Sundays at 5:00 AM UTC
- **Retention**: 90 days
- **Target Resources**: Resources tagged with `BackupSchedule: Weekly`
- **Use Case**: Regular backups for important resources with medium-term retention

### monthly-backup-365day.json
- **Schedule**: Monthly on the 1st at 5:00 AM UTC
- **Retention**: 365 days (1 year)
- **Target Resources**: Resources tagged with `BackupSchedule: Monthly`
- **Use Case**: Long-term archival backups for compliance and audit requirements

### Backup Policy Syntax

AWS Backup policies use the `@@assign` operator to set values. Key components:

- **regions**: AWS regions where backups are created
- **schedule_expression**: Cron expression for backup timing
- **lifecycle.delete_after_days**: Retention period in days
- **selections.tags**: Tag-based resource selection criteria

## Tagging Policies

Tagging policies enforce tag compliance across your organization, ensuring consistent resource tagging.

### required-tags.json
Enforces three mandatory tags on all resources:
- **Environment**: Production, Development, Staging, or Test
- **CostCenter**: Required for cost allocation
- **Project**: Required for project tracking

### optional-tags.json
Defines optional but recommended tags:
- **Owner**: Resource owner identification
- **Application**: Application name for grouping
- **ManagedBy**: Infrastructure management tool (Terraform, CloudFormation, Manual)

### data-classification.json
Enforces data governance and compliance tags:
- **DataClassification**: Public, Internal, Confidential, or Restricted
- **DataRetention**: Retention period (30days, 90days, 1year, etc.)
- **ComplianceScope**: Applicable compliance frameworks (PCI-DSS, HIPAA, SOC2, GDPR)

### Tagging Policy Syntax

AWS Tagging policies use several operators:

- **@@assign**: Sets allowed values for a tag
- **@@none**: Prevents child policies from overriding
- **@@append**: Allows child policies to add values
- **enforced_for**: Specifies which resource types require the tag

## Using These Examples in Titanium.yaml

### Example 1: Single Backup Policy

```yaml
organization:
  backupPolicies:
    - name: DailyBackups
      description: Daily backups with 30-day retention
      policy: policy-examples/backup-policies/daily-backup-30day.json
      deploymentTargets:
        organizationalUnits:
          - Production
```

### Example 2: Multiple Backup Policies

```yaml
organization:
  backupPolicies:
    - name: DailyBackups
      description: Daily backups for production workloads
      policy: policy-examples/backup-policies/daily-backup-30day.json
      deploymentTargets:
        organizationalUnits:
          - Production
    
    - name: WeeklyBackups
      description: Weekly backups for development
      policy: policy-examples/backup-policies/weekly-backup-90day.json
      deploymentTargets:
        organizationalUnits:
          - Development
```

### Example 3: Tagging Policies

```yaml
organization:
  taggingPolicies:
    - name: RequiredTags
      description: Enforce mandatory tags across all accounts
      policy: policy-examples/tagging-policies/required-tags.json
      deploymentTargets:
        organizationalUnits:
          - Root
    
    - name: DataClassification
      description: Enforce data classification tags
      policy: policy-examples/tagging-policies/data-classification.json
      deploymentTargets:
        organizationalUnits:
          - Production
          - Staging
```

## Customizing Policies

### Modifying Backup Schedules

Cron expressions use AWS format: `cron(Minutes Hours Day-of-month Month Day-of-week Year)`

Examples:
- Daily at 2 AM: `cron(0 2 ? * * *)`
- Every 6 hours: `cron(0 */6 * * ? *)`
- First Monday of month: `cron(0 5 ? * MON#1 *)`

### Modifying Tag Values

To add or change allowed tag values, update the `@@assign` array:

```json
"tag_value": {
  "@@assign": ["Value1", "Value2", "Value3"]
}
```

### Modifying Enforced Resources

To change which resource types require tags, update the `enforced_for` array:

```json
"enforced_for": {
  "@@assign": [
    "ec2:instance",
    "s3:bucket",
    "rds:db"
  ]
}
```

Use `"*"` to enforce on all resource types.

## Policy Inheritance

AWS Organizations policies support inheritance through operators:

- **@@none**: Child policies cannot override this value
- **@@append**: Child policies can add to the list
- **@@remove**: Child policies can remove from the list
- **@@replace**: Child policies can completely replace the value

## Best Practices

1. **Start Simple**: Begin with basic policies and add complexity as needed
2. **Test in Non-Production**: Deploy policies to test OUs before production
3. **Use Descriptive Names**: Make policy names clear and self-documenting
4. **Document Exceptions**: If you need to exclude certain resources, document why
5. **Review Regularly**: Audit policy compliance and adjust as needed
6. **Backup Before Changes**: Always test policy changes in a safe environment

## Deployment Order

When deploying organization policies:

1. Deploy OU structure first (01-organizations-stack-mgmt-ous.yaml)
2. Deploy SCPs if needed (02-organizations-stack-mgmt-scps.yaml)
3. Deploy Backup Policies (03-organizations-stack-mgmt-backup-policies.yaml)
4. Deploy Tagging Policies (04-organizations-stack-mgmt-tagging-policies.yaml)

## Troubleshooting

### Policy Not Enforcing

- Verify the policy is attached to the correct OU
- Check that the policy type is enabled in your organization
- Ensure resources have the correct tags for backup policies
- Review CloudWatch logs for Lambda function errors

### Invalid Policy Content

- Validate JSON syntax using a JSON validator
- Ensure all required fields are present
- Check that resource types in `enforced_for` are valid
- Verify cron expressions are in correct AWS format

## Additional Resources

- [AWS Backup Policy Syntax](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_backup_syntax.html)
- [AWS Tagging Policy Syntax](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies-syntax.html)
- [AWS Organizations Best Practices](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_best-practices.html)

## Support

For issues or questions about these policy examples, refer to the main Titanium documentation or consult the AWS Organizations documentation.
