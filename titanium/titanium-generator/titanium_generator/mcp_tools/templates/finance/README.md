# AWS Finance Module

This directory contains CloudFormation templates for AWS finance and cost management capabilities.

## Templates

### 1. Budgets (01-finance-stack-mgmt-budgets.yaml)

Deploys AWS Budgets with configurable thresholds and SNS alert notifications.
- Monthly cost budget with configurable amount
- SNS topic for budget alert notifications
- Email subscription for alerts at configurable threshold

### 2. Compute Optimizer (02-finance-stack-mgmt-compute-optimizer.yaml)

Enables AWS Compute Optimizer across the organization using a Lambda-backed Custom Resource.
- Organization-wide enablement (free tier)
- Analyzes EC2, Auto Scaling groups, EBS volumes, Lambda functions, and ECS on Fargate
- Provides rightsizing recommendations at no cost

### 3. Cost Optimization Hub (03-finance-stack-mgmt-cost-optimization-hub.yaml)

Enables AWS Cost Optimization Hub across the organization using a Lambda-backed Custom Resource.
- Organization-wide enablement (free tier)
- Aggregates recommendations from Compute Optimizer, Savings Plans, Reserved Instances, rightsizing, and idle resource detection
- Single view with estimated savings
