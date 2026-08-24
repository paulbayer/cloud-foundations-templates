# UK Public Sector Requirements for AWS Landing Zones

This document outlines the key requirements, regulatory considerations, and best practices specific to UK public sector organizations when designing AWS landing zones.

## Security Classifications

UK government data is classified according to the [Government Security Classifications Policy](https://www.gov.uk/government/publications/government-security-classifications):

| Classification | Description | AWS Landing Zone Implications |
|---------------|-------------|------------------------------|
| **OFFICIAL** | The majority of public sector information. Includes routine business operations and services. | Standard AWS services can be used with appropriate controls. |
| **OFFICIAL-SENSITIVE** | A subset of OFFICIAL that requires special handling. | Additional controls like CMKs, stricter access controls, and enhanced monitoring. |
| **SECRET** | Very sensitive information that requires protection against serious/organized threats. | Requires enhanced security measures, potentially AWS for Government. |
| **TOP SECRET** | Exceptionally sensitive information requiring the highest levels of protection. | May require on-premises or specialized cloud environments with extraordinary controls. |

Most UK public sector workloads operate at OFFICIAL or OFFICIAL-SENSITIVE levels.

## Core Regulatory Frameworks

UK public sector landing zones must consider the following regulatory frameworks:

### 1. National Cyber Security Centre (NCSC) Cloud Security Principles

The [14 Cloud Security Principles](https://www.ncsc.gov.uk/collection/cloud-security/implementing-the-cloud-security-principles) form the foundation for secure cloud use:

1. Data in transit protection
2. Asset protection and resilience
3. Separation between users
4. Governance framework
5. Operational security
6. Personnel security
7. Secure development
8. Supply chain security
9. Secure user management
10. Identity and authentication
11. External interface protection
12. Secure service administration
13. Audit information for users
14. Secure use of the service

### 2. Cyber Essentials and Cyber Essentials Plus

A government-backed certification scheme focusing on five key controls:

1. Firewalls
2. Secure configuration
3. User access control
4. Malware protection
5. Patch management

### 3. UK GDPR and Data Protection Act 2018

Key requirements include:

- Data minimization
- Purpose limitation
- Storage limitation
- Data subject rights
- Data Protection Impact Assessments (DPIAs)
- Appropriate technical and organizational measures

### 4. Technology Code of Practice

The [Technology Code of Practice](https://www.gov.uk/guidance/the-technology-code-of-practice) provides standards for designing, building, and buying technology. Key principles include:

1. Define user needs
2. Make things accessible
3. Make things secure
4. Make use of open standards
5. Use cloud first
6. Make things interoperable
7. Make things open
8. Share, reuse, and collaborate
9. Integrate and adapt technology
10. Make better use of data
11. Define governance
12. Meet the Service Standard

### 5. Network and Information Systems (NIS) Regulations

Applies to Operators of Essential Services (OES) and Digital Service Providers (DSPs), requiring:

- Appropriate and proportionate security measures
- Measures to prevent and minimize impact of incidents
- Incident reporting

## Network Connectivity Requirements

### Public Services Network (PSN)

For organizations requiring connectivity to the Public Services Network:

- AWS Direct Connect with appropriate PSN connectivity partner
- Implementation of PSN IP Code of Connection (CoCo) requirements
- Appropriate network segmentation and security controls

### Health and Social Care Network (HSCN)

For healthcare organizations:

- AWS HSCN-approved partner connectivity
- Compliance with NHS Digital Data Security and Protection Toolkit
- Appropriate technical and organizational measures

## UK-Specific AWS Service Considerations

### Regional Deployment

UK public sector organizations generally require:

- Primary deployment in the London (eu-west-2) region
- Consideration of eu-west-1 (Ireland) for disaster recovery
- Awareness of sovereignty considerations for data storage and processing

### Service Restrictions

Some services may require additional scrutiny:

- Services that process sensitive data
- Services not available in UK regions
- Services in preview or beta status

## Procurement Frameworks

Landing zones should facilitate procurement through approved frameworks:

- Crown Commercial Service (CCS)
  - G-Cloud
  - Cloud Compute
  - Technology Services 3
- Digital Outcomes and Specialists

## Financial Considerations

### Budget Cycle Alignment

- Annual budget cycles aligned to fiscal year (April to March)
- Need for clear cost attribution, reporting, and forecasting
- Consideration of capital vs. operational expenditure

### Shared Responsibility Model

Clear delineation of:

- Which security controls are AWS's responsibility
- Which security controls are the organization's responsibility
- How this maps to government security frameworks

## Common Landing Zone Requirements

Based on these frameworks, UK public sector landing zones typically require:

1. **Strong Identity Management**
   - Integration with existing identity providers
   - Multi-factor authentication
   - Least privilege access
   - Regular access reviews

2. **Comprehensive Logging and Monitoring**
   - Centralized log collection
   - Security incident detection
   - Compliance reporting
   - Audit trails for all user actions

3. **Network Security**
   - Segmentation by security domain
   - Protection of data in transit
   - Controlled ingress/egress points
   - Web application firewalls for public-facing services

4. **Data Protection**
   - Encryption at rest and in transit
   - Key management
   - Data classification
   - Data loss prevention

5. **Operational Resilience**
   - Cross-region/multi-AZ architectures for critical services
   - Backup and recovery capabilities
   - Disaster recovery planning
   - Business continuity testing

## Organizational Structure Considerations

Common patterns based on organization type:

### Central Government Departments

- Typically require higher levels of control
- Often have complex existing IT estates requiring integration
- May need cross-department collaboration capabilities
- Higher likelihood of ministerial oversight and scrutiny

### Local Government

- Often have budget constraints requiring cost optimization
- Typically manage diverse but smaller-scale services
- May have shared services with other councils
- Often require citizen-facing digital services

### NHS and Healthcare

- Handle sensitive patient data requiring strong controls
- Often need to integrate with national healthcare systems
- May have specialized clinical applications
- Require high availability for critical care systems

### Education (Higher and Further)

- Balance between administrative and research needs
- Often have federated decision-making structures
- May need to support BYOD and diverse user bases
- Research may require high performance computing

## References

1. [NCSC Cloud Security Guidance](https://www.ncsc.gov.uk/collection/cloud-security)
2. [UK Government Security Classifications](https://www.gov.uk/government/publications/government-security-classifications)
3. [Technology Code of Practice](https://www.gov.uk/guidance/the-technology-code-of-practice)
4. [ICO Guide to GDPR](https://ico.org.uk/for-organisations/guide-to-data-protection/guide-to-the-general-data-protection-regulation-gdpr/)
5. [NHS Digital Data Security and Protection Toolkit](https://www.dsptoolkit.nhs.uk/)
6. [AWS UK Public Sector Resources](https://aws.amazon.com/government-education/uk-public-sector/)
