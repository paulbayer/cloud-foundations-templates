# Account Structures for UK Public Sector Landing Zones

This document outlines reference patterns for AWS account structures tailored to UK public sector organizations. These patterns provide a foundation for designing landing zones that meet security, operational, and governance requirements.

## Core Principles for UK Public Sector Account Structures

All account structures for UK public sector organizations should follow these principles:

1. **Security Classification Segregation**: Separate accounts based on data security classification when handling multiple classifications
2. **Functional Separation**: Group accounts by common function and trust boundaries
3. **Administrative Separation**: Maintain separate administrative boundaries where needed
4. **Deployment Isolation**: Separate production from non-production environments
5. **Cost Transparency**: Enable clear cost attribution and budget management
6. **Regulatory Alignment**: Support compliance with UK regulatory frameworks
7. **Operational Efficiency**: Balance security concerns with operational overhead

## Reference Account Structures

### Pattern 1: Basic Foundation (Small Organization)

Suitable for: Smaller local authorities, smaller agencies, educational institutions

**Minimum Structure:**

```
Organization Root
├── Management Account
├── Security & Logging Account
├── Shared Services Account
├── Non-Production Account
└── Production Account
```

**Key Characteristics:**
- Limited number of accounts to manage
- Suitable for organizations with simple requirements
- All production workloads share a common account
- Single non-production environment for dev/test

### Pattern 2: Standard Foundation (Medium Organization)

Suitable for: Medium-sized local authorities, agencies, NHS trusts, universities

**Structure:**

```
Organization Root
├── Management Account
├── Security Services Account
├── Shared Services Account
├── Log Archive Account
├── Development Account
├── Test Account
├── Pre-Production Account
├── Production - Internal Systems Account
└── Production - Public-Facing Services Account
```

**Key Characteristics:**
- Separation of internal and external-facing production workloads
- Distinct environments for development lifecycle stages
- Dedicated log archive separate from security services
- Suitable for organizations with moderate complexity

### Pattern 3: Comprehensive Foundation (Large Organization)

Suitable for: Central government departments, large agencies, NHS digital, large universities

**Structure:**

```
Organization Root
├── Management Account
├── Security Services Account
├── Security Audit Account
├── Log Archive Account
├── Shared Services Account
│   ├── Networking OU
│   │   ├── Transit Account
│   │   └── DNS Account
│   └── Common Services OU
│       ├── Shared Tools Account
│       └── Identity Services Account
├── Sandbox OU
│   └── Innovation Account
├── Workloads OU
│   ├── Development OU
│   │   ├── Dev Team 1 Account
│   │   └── Dev Team 2 Account
│   ├── Test OU
│   │   ├── Test Team 1 Account
│   │   └── Test Team 2 Account
│   ├── Pre-Production OU
│   │   └── Pre-Prod Account
│   └── Production OU
│       ├── Internal Services Account
│       ├── Citizen Services Account
│       └── Partner Services Account
└── Suspended OU
    └── Quarantine Account
```

**Key Characteristics:**
- Multiple organizational units (OUs) for better policy management
- Team-based development and testing accounts
- Further separation of production workloads by audience
- Dedicated accounts for networking components
- Suspended OU for security incident management

### Pattern 4: Multi-Classification Structure

Suitable for: Organizations handling data at OFFICIAL and OFFICIAL-SENSITIVE classifications

**Structure:**

```
Organization Root
├── Management Account
├── Security Services Account
├── Log Archive - OFFICIAL Account
├── Log Archive - OFFICIAL-SENSITIVE Account
├── Shared Services OU
│   ├── Networking - OFFICIAL Account
│   ├── Networking - OFFICIAL-SENSITIVE Account
│   └── Common Tools Account
├── OFFICIAL OU
│   ├── Development Account
│   ├── Test Account
│   └── Production Account
└── OFFICIAL-SENSITIVE OU
    ├── Development Account
    ├── Test Account
    └── Production Account
```

**Key Characteristics:**
- Clear separation between different security classifications
- Separate logging infrastructure for each classification
- Discrete networking accounts for each classification

## Customization Factors for UK Public Sector

### By Organization Type

#### Central Government Departments

- Consider ministerial reporting lines when defining OUs
- May need alignment with departmental structure
- Higher likelihood of cross-government services

#### Local Government

- Consider regional shared service arrangements
- Often need clear separation between public-facing and back-office systems
- Cost constraints may push toward consolidation

#### NHS/Healthcare

- Consider clinical vs. administrative system separation
- May need specialized accounts for research or patient data
- Consider HSCN connectivity requirements in network accounts

#### Educational Institutions

- Consider separation between administrative and research computing
- May need accommodation for student projects
- Often require more flexible sandbox/innovation environments

### By Scale

| Organization Size | AWS Accounts | Organizational Units | Considerations |
|------------------|--------------|----------------------|---------------|
| Small (<100 staff) | 3-5 | 1-2 | Minimize operational overhead |
| Medium (100-1000 staff) | 5-10 | 2-4 | Balance security separation with manageability |
| Large (1000+ staff) | 10+ | 4+ | Comprehensive separation, potential for delegated administration |

## Account Governance for UK Public Sector

### Security Considerations

- **Service Control Policies (SCPs)**: Implement SCPs that enforce UK public sector security standards
- **OFFICIAL vs OFFICIAL-SENSITIVE**: Apply consistent controls according to classification
- **Boundary Protection**: Implement appropriate guardrails for public-facing accounts
- **Identity Management**: Enforce consistent identity policies across accounts

### Cost Management

- **Budget Structure**: Align accounts with budgetary responsibility units
- **FinOps Controls**: Implement account-level cost governance
- **Procurement Alignment**: Structure accounts to align with procurement framework requirements
- **Fiscal Year**: Configure budgets to align with UK government fiscal year (April-March)

### Operational Considerations

- **Support Model**: Define operational support model for each account
- **Incident Management**: Define security incident process across accounts
- **Change Control**: Implement appropriate change management processes based on account purpose

## Example: Account Structure for a Medium-Sized Local Authority

```
Organization Root
├── Management Account
├── Security & Logging Account
├── Shared Services Account (network, identity, etc.)
├── Development & Testing Account
├── Production - Back Office Account
├── Production - Public Services Account
└── Production - Social Care Account (higher sensitivity data)
```

**Rationale:**
- Single security account for simplified management
- Combined dev/test to reduce costs
- Separate account for social care systems due to sensitive data
- Public-facing services separated from internal systems

## Example: Account Structure for a Central Government Department

```
Organization Root
├── Management Account
├── Security Services Account
├── Log Archive Account
├── Audit Account
├── Shared Services OU
│   ├── Networking Account
│   └── Common Services Account
├── Development OU
│   ├── Dev Team A Account
│   ├── Dev Team B Account
│   └── Dev Team C Account
├── Test Account
├── Pre-Production Account
├── Production OU
│   ├── Citizen Services Account
│   ├── Business Services Account
│   ├── Internal Systems Account
│   └── Inter-Department Services Account
└── Partner Access Account
```

**Rationale:**
- Comprehensive security and logging separation
- Multiple development accounts based on team structure
- Production segregation by service constituency
- Dedicated partner access account for cross-government services

## Deployment Considerations

### AWS Control Tower

AWS Control Tower provides a simplified way to set up and govern a multi-account AWS environment, following prescriptive best practices. For UK public sector:

- Enable Security Hub with UK-relevant standards
- Configure guardrails aligned to NCSC Cloud Security Principles
- Implement detective controls for UK-specific regulatory requirements

### AWS Organizations Features to Consider

- **Trusted Access**: Enable trusted access for security services
- **Delegated Administration**: Consider delegated admin for Security Hub, GuardDuty, etc.
- **Tag Policies**: Implement tag policies for cost allocation aligned with department/service codes
- **Backup Policies**: Ensure consistent UK-appropriate retention policies

## References

1. [NCSC Cloud Security Guidance](https://www.ncsc.gov.uk/collection/cloud-security)
2. [AWS Control Tower Best Practices](https://docs.aws.amazon.com/controltower/latest/userguide/best-practices.html)
3. [AWS Organizations User Guide](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_introduction.html)
4. [AWS UK Public Sector Blog](https://aws.amazon.com/blogs/publicsector/)
