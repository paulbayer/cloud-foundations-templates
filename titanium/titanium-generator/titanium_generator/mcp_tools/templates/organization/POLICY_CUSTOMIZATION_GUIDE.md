# AWS Organizations Policy Customization Guide

This guide explains how to customize AWS Organizations Backup Policies and Tagging Policies for your landing zone deployment.

## Overview

AWS Organizations policies allow you to enforce governance requirements across your entire organization. This guide covers:

- Backup Policies: Enforce backup requirements using AWS Backup
- Tagging Policies: Enforce tag compliance across resources

## Policy Structure

### Backup Policies

Backup policies use AWS Backup's policy syntax with inheritance operators:

```json
{
  "plans": {
    "PlanName": {
      "regions": {
        "@@assign": ["us-east-1", "us-west-2"]
      },
      "rules": {
        "RuleName": {
          "schedule_expression": {
            "@@assign": "cron(0 5 ? * * *)"
          },
          "lifecycle": {
            "delete_after_days": {
              "@@assign": "30"
            }
          }
        }
      }
    }
  }
}
```

### Tagging Policies

Tagging policies enforce tag requirements with inheritance operators:

```json
{
  "tags": {
    "Environment": {
      "tag_key": {
        "@@assign": "Environment"
      },
      "tag_value": {
        "@@assign": ["Production", "Development"]
      },
      "enforced_for": {
        "@@assign": ["ec2:instance", "s3:bucket"]
      }
    }
  }
}
```

## Inheritance Operators

Both policy types support inheritance operators that control how child policies can modify parent policies:

### `@@assign`
Sets a value that applies to the account. Child policies cannot override.

```json
"tag_key": {
  "@@assign": "Environment"
}
```

### `@@append`
Allows child policies to add additional values to the list.

```json
"tag_value": {
  "@@assign": ["Production", "Development"],
  "@@operators_allowed_for_child_policies": ["@@append"]
}
```

### `@@remove`
Allows child policies to remove values from the list.

```json
"enforced_for": {
  "@@assign": ["ec2:*", "s3:*"],
  "@@operators_allowed_for_child_policies": ["@@remove"]
}
```

### `@@none`
Prevents child policies from making any modifications.

```json
"tag_key": {
  "@@assign": "CostCenter",
  "@@operators_allowed_for_child_policies": ["@@none"]
}
```

## Backup Policy Examples

### Daily Backup with 30-Day Retention

```json
{
  "plans": {
    "DailyBackupPlan": {
      "regions": {
        "@@assign": ["us-east-1", "us-west-2"]
      },
      "rules": {
        "DailyBackupRule": {
          "schedule_expression": {
            "@@assign": "cron(0 5 ? * * *)"
          },
          "start_backup_window_minutes": {
            "@@assign": "60"
          },
          "complete_backup_window_minutes": {
            "@@assign": "120"
          },
          "lifecycle": {
            "delete_after_days": {
              "@@assign": "30"
            }
          },
          "target_backup_vault_name": {
            "@@assign": "Default"
          }
        }
      },
      "selections": {
        "tags": {
          "DailyBackupSelection": {
            "iam_role_arn": {
              "@@assign": "arn:aws:iam::$account:role/service-role/AWSBackupDefaultServiceRole"
            },
            "tag_key": {
              "@@assign": "BackupSchedule"
            },
            "tag_value": {
              "@@assign": ["Daily"]
            }
          }
        }
      }
    }
  }
}
```

**Usage**: Resources tagged with `BackupSchedule: Daily` will be backed up daily at 5 AM UTC with 30-day retention.

### Weekly Backup with 90-Day Retention

```json
{
  "plans": {
    "WeeklyBackupPlan": {
      "regions": {
        "@@assign": ["us-east-1", "us-west-2"]
      },
      "rules": {
        "WeeklyBackupRule": {
          "schedule_expression": {
            "@@assign": "cron(0 5 ? * SUN *)"
          },
          "start_backup_window_minutes": {
            "@@assign": "60"
          },
          "complete_backup_window_minutes": {
            "@@assign": "120"
          },
          "lifecycle": {
            "delete_after_days": {
              "@@assign": "90"
            }
          },
          "target_backup_vault_name": {
            "@@assign": "Default"
          }
        }
      },
      "selections": {
        "tags": {
          "WeeklyBackupSelection": {
            "iam_role_arn": {
              "@@assign": "arn:aws:iam::$account:role/service-role/AWSBackupDefaultServiceRole"
            },
            "tag_key": {
              "@@assign": "BackupSchedule"
            },
            "tag_value": {
              "@@assign": ["Weekly"]
            }
          }
        }
      }
    }
  }
}
```

**Usage**: Resources tagged with `BackupSchedule: Weekly` will be backed up every Sunday at 5 AM UTC with 90-day retention.

### Monthly Backup with 365-Day Retention

```json
{
  "plans": {
    "MonthlyBackupPlan": {
      "regions": {
        "@@assign": ["us-east-1", "us-west-2"]
      },
      "rules": {
        "MonthlyBackupRule": {
          "schedule_expression": {
            "@@assign": "cron(0 5 1 * ? *)"
          },
          "start_backup_window_minutes": {
            "@@assign": "60"
          },
          "complete_backup_window_minutes": {
            "@@assign": "180"
          },
          "lifecycle": {
            "delete_after_days": {
              "@@assign": "365"
            }
          },
          "target_backup_vault_name": {
            "@@assign": "Default"
          }
        }
      },
      "selections": {
        "tags": {
          "MonthlyBackupSelection": {
            "iam_role_arn": {
              "@@assign": "arn:aws:iam::$account:role/service-role/AWSBackupDefaultServiceRole"
            },
            "tag_key": {
              "@@assign": "BackupSchedule"
            },
            "tag_value": {
              "@@assign": ["Monthly"]
            }
          }
        }
      }
    }
  }
}
```

**Usage**: Resources tagged with `BackupSchedule: Monthly` will be backed up on the 1st of each month at 5 AM UTC with 365-day retention.

## Tagging Policy Examples

### Required Tags (Environment, CostCenter, Project)

```json
{
  "tags": {
    "Environment": {
      "tag_key": {
        "@@assign": "Environment",
        "@@operators_allowed_for_child_policies": ["@@none"]
      },
      "tag_value": {
        "@@assign": ["Production", "Development", "Staging", "Test"],
        "@@operators_allowed_for_child_policies": ["@@append"]
      },
      "enforced_for": {
        "@@assign": [
          "ec2:instance",
          "ec2:volume",
          "s3:bucket",
          "rds:db",
          "lambda:function",
          "dynamodb:table"
        ]
      }
    },
    "CostCenter": {
      "tag_key": {
        "@@assign": "CostCenter",
        "@@operators_allowed_for_child_policies": ["@@none"]
      },
      "enforced_for": {
        "@@assign": ["*"]
      }
    },
    "Project": {
      "tag_key": {
        "@@assign": "Project",
        "@@operators_allowed_for_child_policies": ["@@none"]
      },
      "enforced_for": {
        "@@assign": ["*"]
      }
    }
  }
}
```

**Usage**: All resources must have Environment, CostCenter, and Project tags. Environment values are restricted to the specified list.

### Optional Tags with Validation

```json
{
  "tags": {
    "Owner": {
      "tag_key": {
        "@@assign": "Owner"
      },
      "enforced_for": {
        "@@assign": ["ec2:*", "s3:*"]
      }
    },
    "Application": {
      "tag_key": {
        "@@assign": "Application"
      },
      "enforced_for": {
        "@@assign": ["ec2:instance", "lambda:function"]
      }
    }
  }
}
```

**Usage**: Owner tag is recommended for EC2 and S3 resources. Application tag is recommended for compute resources.

### Data Classification Tags

```json
{
  "tags": {
    "DataClassification": {
      "tag_key": {
        "@@assign": "DataClassification",
        "@@operators_allowed_for_child_policies": ["@@none"]
      },
      "tag_value": {
        "@@assign": ["Public", "Internal", "Confidential", "Restricted"],
        "@@operators_allowed_for_child_policies": ["@@none"]
      },
      "enforced_for": {
        "@@assign": [
          "s3:bucket",
          "rds:db",
          "dynamodb:table",
          "secretsmanager:secret"
        ]
      }
    }
  }
}
```

**Usage**: Data storage resources must have a DataClassification tag with one of the specified values.

## Customization Workflow

### 1. Create Policy JSON Files

Store your policy JSON files in a dedicated directory:

```
policy-files/
├── backup-policies/
│   ├── daily-backup-30day.json
│   ├── weekly-backup-90day.json
│   └── monthly-backup-365day.json
└── tagging-policies/
    ├── required-tags.json
    ├── optional-tags.json
    └── data-classification.json
```

### 2. Reference Policies in Titanium.yaml

```yaml
organization:
  enable: true
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
```

### 3. Generate Modified Templates

Run the Titanium generator to create modified CloudFormation templates:

```bash
# Process all templates
python -m titanium_generator.mcp_tools.process_all_templates \
  --titanium-path Titanium.yaml \
  --output-dir modified-templates/
```

### 4. Deploy Templates

Deploy the generated templates using CloudFormation:

```bash
# Deploy backup policies
aws cloudformation create-stack \
  --stack-name LandingZone-BackupPolicies \
  --template-body file://modified-templates/03-organizations-stack-mgmt-backup-policies.yaml \
  --capabilities CAPABILITY_NAMED_IAM

# Deploy tagging policies
aws cloudformation create-stack \
  --stack-name LandingZone-TaggingPolicies \
  --template-body file://modified-templates/04-organizations-stack-mgmt-tagging-policies.yaml \
  --capabilities CAPABILITY_NAMED_IAM
```

## Best Practices

### Backup Policies

1. **Start with Daily Backups**: Begin with daily backups for critical resources
2. **Use Tag-Based Selection**: Tag resources with `BackupSchedule` tag for automatic backup
3. **Test Restore Procedures**: Regularly test backup restoration
4. **Monitor Backup Jobs**: Set up CloudWatch alarms for failed backups
5. **Cross-Region Replication**: Consider copying backups to another region for disaster recovery

### Tagging Policies

1. **Start at Root**: Apply basic tagging policies at the organization root
2. **Use Inheritance**: Allow child OUs to extend tag values with `@@append`
3. **Enforce Critical Tags**: Use `@@none` operator for tags that cannot be modified
4. **Resource-Specific Tags**: Apply different tag requirements to different resource types
5. **Monitor Compliance**: Use AWS Config to monitor tag compliance

## Common Customizations

### Adjust Backup Schedule

Change the cron expression in the backup policy:

```json
"schedule_expression": {
  "@@assign": "cron(0 2 ? * * *)"  // 2 AM UTC daily
}
```

### Modify Retention Period

Change the lifecycle delete_after_days:

```json
"lifecycle": {
  "delete_after_days": {
    "@@assign": "60"  // 60 days retention
  }
}
```

### Add New Tag Requirements

Add a new tag to the tagging policy:

```json
"Department": {
  "tag_key": {
    "@@assign": "Department"
  },
  "enforced_for": {
    "@@assign": ["*"]
  }
}
```

### Restrict Tag Values

Limit allowed values for a tag:

```json
"Environment": {
  "tag_key": {
    "@@assign": "Environment"
  },
  "tag_value": {
    "@@assign": ["prod", "dev", "staging"]
  }
}
```

## Troubleshooting

### Policy Not Attaching

**Issue**: Policy created but not attached to OUs

**Solution**: 
1. Verify OU IDs are correct in `u[PolicyName]Targets` parameter
2. Check CloudWatch logs for Lambda function errors
3. Ensure policy type is enabled in organization

### Backup Jobs Not Running

**Issue**: Backup policy deployed but backups not executing

**Solution**:
1. Verify resources have correct `BackupSchedule` tag
2. Check IAM role `AWSBackupDefaultServiceRole` exists
3. Verify backup vault exists in target accounts
4. Check AWS Backup console for job status

### Tag Compliance Failures

**Issue**: Resources failing tag compliance checks

**Solution**:
1. Verify tag keys match exactly (case-sensitive)
2. Check tag values are in allowed list
3. Ensure resource types are included in `enforced_for`
4. Use AWS Config to identify non-compliant resources

## Additional Resources

- [AWS Backup Policy Syntax](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_backup_syntax.html)
- [AWS Tagging Policy Syntax](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies-syntax.html)
- [AWS Organizations Policy Inheritance](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_inheritance.html)
- [AWS Backup Documentation](https://docs.aws.amazon.com/aws-backup/)
- [AWS Resource Tagging Best Practices](https://docs.aws.amazon.com/whitepapers/latest/tagging-best-practices/tagging-best-practices.html)
