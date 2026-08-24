# UK Public Sector Landing Zone Interview Questions

This document extends the [core interview framework](../../core/interview-framework.md) with questions specifically tailored for UK public sector organizations. These questions should be incorporated into the general interview flow at appropriate points.

## Organization Context - UK Public Sector Extensions

### Organization Type

```
What type of UK public sector organization are you working with?
1. Central government department or agency
2. Local government/council
3. NHS/healthcare organization
4. Educational institution (university, college)
5. Police or emergency services
6. Arm's length body/non-departmental public body
7. Other public sector organization (please specify)
```

### Security Classification

```
What is the highest level of security classification for data that will be processed in your AWS environment?
1. OFFICIAL
2. OFFICIAL-SENSITIVE
3. SECRET
4. TOP SECRET
```

### Scale and Scope

```
How many public-facing digital services do you anticipate hosting on AWS?
1. None - all internal systems only
2. 1-5 services
3. 6-20 services
4. More than 20 services
```

```
What is your organization's annual IT budget range?
1. Under £1 million
2. £1-5 million
3. £5-20 million
4. £20-100 million
5. Over £100 million
```

## Regulatory Requirements - UK Public Sector Extensions

### Core Frameworks

```
Which of the following regulatory frameworks apply to your organization? (Select all that apply)
1. NCSC Cloud Security Principles
2. Cyber Essentials / Cyber Essentials Plus
3. UK GDPR and Data Protection Act 2018
4. Digital Service Standard
5. Technology Code of Practice
6. Network and Information Systems (NIS) Regulations
7. PSN Code of Connection
8. HSCN Connectivity Requirements
9. NHS Digital Data Security and Protection Toolkit
```

### Specific Standards

```
Do you have specific compliance requirements related to any of the following? (Select all that apply)
1. PCI DSS (for payment processing)
2. ISO 27001
3. National Institute for Clinical Excellence (NICE) guidelines
4. Open Banking standards
5. UK Statistics Authority Code of Practice
6. Accessibility requirements (WCAG 2.1 AA)
```

### Data Protection

```
Have you completed a Data Protection Impact Assessment (DPIA) for the workloads you plan to migrate to AWS?
1. Yes, completed for all workloads
2. Completed for some workloads
3. Not yet, but planning to
4. Not applicable to our workloads
5. Not sure what a DPIA is
```

```
Will you be handling any of the following types of personal data? (Select all that apply)
1. Basic personal identifiers (names, addresses)
2. Financial information
3. Health records
4. Criminal records
5. Biometric data
6. Children's data
7. Large-scale data processing of citizens
```

## Network Connectivity - UK Public Sector Extensions

### Government Networks

```
Do you require connectivity to any of the following networks? (Select all that apply)
1. Public Services Network (PSN)
2. Health and Social Care Network (HSCN)
3. Police National Network (PNN)
4. Janet Network (for education)
5. RLI (Remote Logon Infrastructure)
6. Other government secure network (please specify)
7. No government network connectivity required
```

### Existing Networks

```
What type of connectivity do you currently have between your on-premises environment and cloud providers?
1. None currently established
2. Internet-based VPN
3. Direct Connect / dedicated leased line
4. Transit Gateway connections
5. MPLS or SD-WAN
```

## Security Controls - UK Public Sector Extensions

### Security Operations

```
How do you plan to manage security operations for your AWS environment?
1. Internal security team
2. External managed security service provider (MSSP)
3. Hybrid approach with internal and external resources
4. Exploring options/undecided
```

```
What level of security monitoring capability does your organization currently have?
1. Basic/minimal (e.g., default AWS CloudTrail only)
2. Moderate (e.g., security alerts for critical events)
3. Advanced (e.g., 24/7 SOC, SIEM implementation)
4. None currently
```

### Security Accreditation

```
Will your AWS workloads require formal security accreditation?
1. Yes, for all workloads
2. Yes, for specific high-risk workloads only
3. No formal accreditation required
4. Undecided/unsure
```

```
If accreditation is required, which approach will you follow?
1. NCSC Assured Service (Cyber Assessment Framework)
2. ISO 27001 certification
3. Internal accreditation process
4. Other (please specify)
```

## Operational Model - UK Public Sector Extensions

### Procurement

```
How do you procure AWS services?
1. Direct from AWS
2. Through G-Cloud framework
3. Through a partner/reseller
4. Through Cloud Compute framework
5. Other framework (please specify)
```

```
What is your procurement/budgeting cycle?
1. Annual
2. Multi-year
3. Project-based
4. Consumption-based
```

### Team Structure

```
How is your cloud team structured?
1. Dedicated cloud team separate from traditional IT
2. Embedded within existing IT structure
3. Federated model with central governance
4. Outsourced/partner-delivered
5. Not yet established
```

```
What is your development approach for citizen/public-facing services?
1. In-house development team
2. Outsourced development
3. Mixed model with in-house and contracted resources
4. GDS-aligned multidisciplinary teams
```

## Technical Requirements - UK Public Sector Extensions

### Hybrid Requirements

```
Do you have systems that must remain on-premises for regulatory or technical reasons?
1. No, planning full cloud migration
2. Yes, planning hybrid for the foreseeable future
3. Yes, but temporary until technical barriers are resolved
4. Uncertain, currently assessing
```

```
Do you have sovereignty requirements that limit which AWS regions you can use?
1. Must use UK regions only
2. Can use UK and EU regions
3. Can use any AWS regions with appropriate controls
4. No specific sovereignty requirements
```

### Cross-Government Services

```
Do you need to integrate with any of these common government platforms? (Select all that apply)
1. GOV.UK Notify
2. GOV.UK Pay
3. GOV.UK Verify / One Login
4. GOV.UK Platform as a Service (PaaS)
5. Government Gateway
6. Other government platforms (please specify)
```

## Constraints and Considerations - UK Public Sector Extensions

### Political Considerations

```
Are there any political or public perception concerns about cloud adoption?
1. No significant concerns
2. Some concerns about data sovereignty
3. Concerns about vendor lock-in
4. Concerns about security of cloud services
5. Other concerns (please specify)
```

### Legacy Challenges

```
What legacy systems will need integration with your AWS environment?
1. Mainframe systems
2. Traditional data centers
3. Existing cloud environments
4. Custom-developed applications
5. Commercial off-the-shelf (COTS) applications
```

### Digital Skills

```
How would you rate your organization's AWS/cloud skills?
1. Extensive - fully capable of designing and implementing cloud solutions
2. Moderate - can manage basic cloud services but need help with advanced features
3. Limited - early in cloud adoption journey
4. Minimal - heavily reliant on partners
```

```
Do you have a digital skills development program in place?
1. Yes, comprehensive program
2. Limited training available
3. Planning to establish one
4. No program currently
```

## Follow-up Questions Based on Organization Type

### For Central Government

```
Are you planning to act as a central shared service provider for other departments or agencies?
1. Yes, providing shared services to multiple organizations
2. Limited sharing with closely related organizations only
3. No, environment will be for our use only
```

```
What level of ministerial or cabinet oversight is expected for your cloud program?
1. High - regular ministerial reporting
2. Moderate - summary updates to ministers
3. Low - operational decisions delegated to department
```

### For Local Government

```
Are you exploring shared services with other local authorities?
1. Yes, active shared service arrangements
2. Exploring possibilities
3. No current plans for sharing
```

```
What is the primary driver for your cloud adoption?
1. Cost reduction
2. Improved service delivery
3. Legacy system replacement
4. Digital transformation initiative
5. Data center exit
```

### For Healthcare Organizations

```
Will you need to process patient identifiable data in AWS?
1. Yes, significant amount of patient data
2. Limited patient data
3. No patient data, clinical systems remain on-premises
```

```
Do you need to integrate with core NHS systems like Spine, GP Connect, or NHS e-Referral Service?
1. Yes, deep integration required
2. Limited integration points
3. No integration with national systems
```

### For Educational Institutions

```
What is the balance between administrative and research computing needs?
1. Primarily administrative
2. Primarily research
3. Balanced mix of both
```

```
Do you need to support JANET network connectivity in your landing zone?
1. Yes, essential requirement
2. Helpful but not essential
3. Not required
