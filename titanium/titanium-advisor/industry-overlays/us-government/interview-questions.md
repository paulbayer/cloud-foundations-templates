# US Government Landing Zone Interview Questions

This document extends the core interview framework with questions specifically tailored for US government agencies. These questions should be incorporated into the general interview flow at appropriate points.

## Organization Context - US Government Extensions

### Organization Type

```
What type of US government organization are you working with?
1. Federal civilian agency
2. Department of Defense (DoD) agency
3. Intelligence community
4. State government agency
5. Local government agency
6. Tribal government organization
7. Other government entity (please specify)
```

### Security Classification

```
What is the highest level of security classification for data that will be processed in your AWS environment?
1. Unclassified / Public
2. Sensitive But Unclassified (SBU)
3. For Official Use Only (FOUO)
4. Controlled Unclassified Information (CUI)
5. Classified (Secret/Top Secret)
```

### Scale and Scope

```
How many citizen-facing digital services do you anticipate hosting on AWS?
1. None - all internal systems only
2. 1-5 services
3. 6-20 services
4. More than 20 services
```

```
What is your organization's annual IT budget range?
1. Under $1 million
2. $1-10 million
3. $10-50 million
4. $50-100 million
5. $100 million - $1 billion
6. Over $1 billion
```

## Regulatory Requirements - US Government Extensions

### Core Frameworks

```
Which of the following regulatory frameworks apply to your organization? (Select all that apply)
1. Federal Information Security Modernization Act (FISMA)
2. Federal Risk and Authorization Management Program (FedRAMP)
3. NIST Special Publication 800-53
4. NIST Cybersecurity Framework
5. CMMC (Cybersecurity Maturity Model Certification)
6. Section 508 compliance requirements
7. Privacy Act of 1974
8. HIPAA (for health-related data)
9. Criminal Justice Information Services (CJIS) security policy
10. IRS Publication 1075 (for tax information)
```

### Specific Standards

```
What FedRAMP impact level are you targeting for your AWS environment?
1. FedRAMP Low
2. FedRAMP Moderate
3. FedRAMP High
4. Not applicable / Don't know
```

```
Do you require alignment with any of the following? (Select all that apply)
1. DOD Cloud Computing SRG (Security Requirements Guide)
2. DOD SRG Impact Levels (IL2, IL4, IL5, IL6)
3. Intelligence Community Directive (ICD) 503
4. NIST SP 800-171 (CUI requirements)
```

### Data Protection

```
Will you be handling any of the following types of data? (Select all that apply)
1. Personally Identifiable Information (PII)
2. Protected Health Information (PHI)
3. Tax information
4. Law enforcement sensitive information
5. Controlled Unclassified Information (CUI)
6. Export Controlled information (ITAR/EAR)
7. Payment Card Information (PCI)
```

```
Have you completed a System Security Plan (SSP) for the workloads you plan to migrate to AWS?
1. Yes, completed for all workloads
2. Completed for some workloads
3. Not yet, but planning to
4. Not applicable to our workloads
```

## Network Connectivity - US Government Extensions

### Government Networks

```
Do you require connectivity to any of the following networks? (Select all that apply)
1. Department of Defense Information Network (DODIN)
2. Justice Unified Telecommunications Network (JUSTN)
3. Trusted Internet Connection (TIC)
4. MTIPS (Managed Trusted Internet Protocol Services)
5. SIPRNet
6. Other government secure network (please specify)
7. No government network connectivity required
```

### Existing Networks

```
What type of connectivity do you currently have between your on-premises environment and cloud providers?
1. None currently established
2. Internet-based VPN
3. AWS Direct Connect
4. DISA Cloud Access Point (CAP)
5. Agency Trusted Internet Connection (TIC)
6. SD-WAN or MPLS
```

## Security Controls - US Government Extensions

### Security Operations

```
How do you plan to manage security operations for your AWS environment?
1. Internal security team
2. External managed security service provider (MSSP)
3. Defense agency (e.g., DISA, CISA)
4. Hybrid approach
5. Exploring options/undecided
```

```
What level of security monitoring capability does your organization currently have?
1. Basic/minimal (e.g., default CloudTrail only)
2. Moderate (e.g., security alerts for critical events)
3. Advanced (e.g., 24/7 SOC, SIEM implementation)
4. None currently
```

### Security Accreditation

```
Will your AWS workloads require formal security authorization/accreditation?
1. Yes, all workloads must be FedRAMP authorized
2. Yes, using agency-specific authorization process
3. Yes, using DOD RMF (Risk Management Framework)
4. No formal authorization required
5. Undecided/unsure
```

```
Who will serve as the Authorizing Official (AO) for your system?
1. Agency CIO
2. Agency CISO
3. Program/Mission Owner
4. Joint Authorization Board (JAB)
5. Not determined yet
```

## Operational Model - US Government Extensions

### Procurement

```
How do you procure AWS services?
1. Direct from AWS
2. Through AWS Partner
3. Through reseller
4. Through NASA SEWP
5. Through GSA Schedule
6. Through other procurement vehicle (please specify)
```

```
What is your procurement/budgeting cycle?
1. Annual
2. Multi-year
3. Project-based
4. Based on fiscal year (Oct-Sept)
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
Do you have a formal cloud center of excellence (CCoE) or cloud program management office?
1. Yes, established and operational
2. Currently forming one
3. Planning to establish one
4. No plans for formal CCoE
```

## Technical Requirements - US Government Extensions

### Sovereign Cloud Requirements

```
Do you have requirements to use AWS GovCloud?
1. Yes, required for all workloads
2. Yes, for specific regulated workloads only
3. No specific requirement for GovCloud
4. Undecided/evaluating
```

```
Do you have data residency requirements that limit which AWS regions you can use?
1. Must use US regions only
2. Must use GovCloud regions only
3. Must use Secret or Top Secret regions
4. Can use any AWS regions with appropriate controls
```

### Government-Specific Services

```
Do you need to integrate with any of these common government platforms? (Select all that apply)
1. Login.gov
2. SAM.gov
3. Pay.gov
4. USA.gov
5. Government-specific identity provider
6. Other government platforms (please specify)
```

## Constraints and Considerations - US Government Extensions

### Political Considerations

```
Are there any political or public perception concerns about cloud adoption?
1. No significant concerns
2. Concerns about data sovereignty
3. Concerns about vendor lock-in
4. Concerns about security of cloud services
5. Budget/cost justification to oversight bodies
```

### Legacy Challenges

```
What legacy systems will need integration with your AWS environment?
1. Mainframe systems
2. Traditional data centers
3. Existing cloud environments
4. Legacy COTS applications
5. Custom-developed applications
```

### Cloud Skills

```
How would you rate your organization's AWS/cloud skills?
1. Extensive - fully capable of designing and implementing cloud solutions
2. Moderate - can manage basic cloud services but need help with advanced features
3. Limited - early in cloud adoption journey
4. Minimal - heavily reliant on partners
```

```
Have your technical staff completed AWS certifications?
1. Yes, multiple staff with various certifications
2. Limited certifications in specific areas
3. No certifications yet, but training in progress
4. No certified staff or training program
```

## Follow-up Questions Based on Organization Type

### For Federal Civilian Agencies

```
Are you planning to share services with other agencies?
1. Yes, providing shared services to multiple agencies
2. Limited sharing with closely related agencies only
3. No, environment will be for our use only
```

```
What is your Federal Enterprise Architecture (FEA) alignment?
1. Strongly aligned, mature implementation
2. Partially aligned, work in progress
3. Planning to align
4. Not applicable for our agency
```

### For Department of Defense (DoD)

```
Are you subject to combatant command requirements?
1. Yes, specific combatant command alignment
2. Joint command requirements
3. No specific combatant command requirements
```

```
Do you require deployment to tactical edge locations?
1. Yes, significant edge deployment requirements
2. Limited edge deployment needs
3. No edge deployment requirements
4. Evaluating future edge requirements
```

### For State/Local Government

```
Are you exploring shared services with other state/local entities?
1. Yes, active shared service arrangements
2. Exploring possibilities
3. No current plans for sharing
```

```
What is the primary driver for your cloud adoption?
1. Cost reduction
2. Improved constituent service delivery
3. Legacy system replacement
4. Disaster recovery/continuity of operations
5. Data center exit
