# Landing Zone Design Interview Framework

This document outlines the structured approach for conducting landing zone design interviews using Kiro. This framework is designed to be industry-agnostic and forms the foundation upon which industry-specific interviews are built.

## Interview Stages

Every landing zone design interview should progress through these key stages:

### 1. Organization Context (10-15 minutes)

- **Purpose**: Understand the organization's structure, scale, and basic requirements
- **Key Questions**:
  - What is the size of your organization (employees, IT users)?
  - What is your current cloud maturity level?
  - How many AWS accounts do you currently manage or anticipate managing?
  - What is your expected monthly AWS spend?
  - What regions do you need to operate in?

### 2. Business Drivers (5-10 minutes)

- **Purpose**: Identify primary motivations for establishing a landing zone
- **Key Questions**:
  - What are your primary reasons for establishing a structured landing zone?
  - What timeframe are you working with for implementation?
  - What specific business outcomes are you hoping to achieve?
  - Are there any current pain points in your cloud operations?

### 3. Security and Compliance Requirements (15-20 minutes)

- **Purpose**: Understand regulatory landscape and security posture
- **Key Questions**:
  - What regulatory frameworks must you comply with?
  - What types of data will you be processing?
  - What are your data sovereignty requirements?
  - Do you have existing security tools or standards you must incorporate?
  - What is your organization's risk tolerance level?

### 4. Operational Model (10-15 minutes)

- **Purpose**: Understand how the organization will operate AWS at scale
- **Key Questions**:
  - How is your IT organization structured?
  - What is your approach to cloud governance?
  - How do you manage deployment pipelines?
  - What level of autonomy should application teams have?
  - What are your monitoring and incident response requirements?

### 5. Technical Requirements (15-20 minutes)

- **Purpose**: Gather specific technical requirements for the landing zone
- **Key Questions**:
  - What are your network connectivity requirements?
  - What identity provider do you use or plan to use?
  - What level of account isolation do you require?
  - Do you have preferred architectural patterns?
  - What are your logging, monitoring, and observability requirements?

### 6. Constraints and Considerations (5-10 minutes)

- **Purpose**: Identify limitations and special considerations
- **Key Questions**:
  - Are there budget constraints for the landing zone implementation?
  - Are there any organizational policies that might impact design choices?
  - Are there legacy systems or existing architectures that need integration?
  - Are there political or organizational change management considerations?

## Question Types

The interview should utilize a mix of question types:

### 1. Multiple Choice Questions

Use for questions where there are clear distinct options:

```
What type of identity provider do you plan to use?
1. AWS IAM Identity Center (successor to AWS SSO)
2. Azure Active Directory / Entra ID
3. On-premises Active Directory with AD Connector
4. Okta or other third-party IdP
5. We haven't decided yet
```

### 2. Rating Scale Questions

Use for understanding priorities and importance:

```
On a scale of 1 to 5, how important is having a centralized logging solution?
1. Not important at all
2. Slightly important
3. Moderately important
4. Very important
5. Critically important
```

### 3. Open-ended Questions

Use for gathering detailed information where options aren't predictable:

```
What specific compliance frameworks or regulations must your cloud environment adhere to?
```

### 4. Conditional Questions

Use follow-up questions based on previous answers:

```
[If user selected "Very important" for centralized logging]
What specific log sources are most critical for your compliance requirements?
```

## Response Format

After completing all required stages of the interview, synthesize the responses into a structured design proposal using the appropriate document template. The format should include:

1. **Executive Summary**: Brief overview of the organization and key requirements
2. **Business Drivers**: Summary of the primary business goals
3. **Design Decisions**: Key architectural decisions with rationale
4. **Architecture Diagrams**: Visual representations of the proposed landing zone
5. **Implementation Roadmap**: Phased approach for deploying the landing zone
6. **Appendices**: Detailed specifications for components of the landing zone

## Tailoring the Interview

This framework serves as a base. Industry-specific interview flows will:

- Add industry-specific questions at appropriate stages
- Skip irrelevant questions based on industry context
- Include specialized sections for industry-specific requirements
- Adjust terminology to match industry conventions
- Incorporate relevant compliance frameworks and regulatory requirements

## Interview Flow Control

During the interview:

- Begin with broad questions and narrow down based on responses
- Skip sections that are determined to be irrelevant based on previous responses
- Allow the user to go back and change answers if needed
- Provide recommendations when the user is uncertain about an answer
- Summarize inputs at key points to ensure understanding
