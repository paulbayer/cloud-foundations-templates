# Titanium — AWS Landing Zone Framework

An AWS Landing Zone is a pre-configured, secure, multi-account AWS environment based on best practices. It gives you a consistent foundation — account structure, security guardrails, networking, and governance — so your teams can start building workloads without reinventing the wheel.

Titanium is an AI-assisted framework for designing and deploying AWS Landing Zones. Instead of manually configuring dozens of AWS services, you answer a guided interview, Titanium produces a single `Titanium.yaml` configuration file, generates CloudFormation templates, and deploys your multi-account AWS environment.

```
Interview  ──▶  Titanium.yaml  ──▶  CloudFormation Templates  ──▶  AWS Deployment
```

You don't need to be an AWS Landing Zone expert. The Advisor asks the right questions, captures your decisions in a single YAML file, and the Generator turns that into production-ready CloudFormation.

> **Disclaimer:** Titanium is a sample/reference implementation to help you build your
> own AWS Landing Zone. Like everything in this repository, it is provided as-is under
> MIT-0 and is **not** an officially supported AWS service or solution. Review and test
> all generated templates in a non-production environment before deploying.

🔍 [Want to know more?](ABOUT.md) — See where Titanium fits in the AWS landscape and what it deploys.

## Get Started

Follow these three steps to go from zero to a deployed landing zone:

| Step | Guide | What You'll Do | Time |
|------|-------|---------------|------|
| 1 | [Prerequisites & Setup](GETTING_STARTED.md) | Install Python, configure MCP servers, verify everything works | ~15 min |
| 2 | [Design Your Landing Zone](DESIGN_GUIDE.md) | Run the AI-guided interview and generate your Titanium.yaml | ~20 min |
| 3 | [Deploy to AWS](DEPLOYMENT_GUIDE.md) | Generate CloudFormation templates and deploy to your AWS environment | ~2–4 hrs |

## How It Works

Titanium operates as two MCP server components that your AI assistant orchestrates end-to-end across four stages:

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐     ┌────────────────┐
│  Stage 1    │     │   Stage 2    │     │     Stage 3      │     │    Stage 4     │
│  DESIGN     │────▶│  GENERATE    │────▶│     DEPLOY       │────▶│    VERIFY      │
│  (Advisor)  │     │ (Generator)  │     │ (CloudFormation) │     │  (Validation)  │
└─────────────┘     └──────────────┘     └──────────────────┘     └────────────────┘
 AI interview        YAML → CFN          Stacks & StackSets       Confirm resources
 Titanium.yaml       templates           across accounts          match config
```

### Stage 1 — Design (Titanium Advisor)

The Advisor MCP server conducts a guided interview tailored to your organization. You select an industry overlay (Starter, Enterprise, UK Public Sector, or US Government) — each overlay adjusts the interview questions and defaults to match your industry's compliance and regulatory requirements. The assistant walks you through nine configuration sections:

| Section | What It Captures |
|---------|-----------------|
| Global | Home region, enabled regions, management account role |
| Control Tower | Landing zone version, logging retention, region deny |
| Organization | OU structure, service control policies, tagging and backup policies |
| Identity & Access | Password policy, SSO/Identity Center, access analyzer |
| Logging | CloudTrail, VPC Flow Logs, Session Manager, log retention |
| Security | GuardDuty, SecurityHub, compliance standards, SNS topics |
| Accounts | Management, LogArchive, Audit, infrastructure and workload accounts |
| Network | VPCs, Transit Gateway, IPAM, Network Firewall, DNS, VPC Endpoints |
| Finance | Budgets, Compute Optimizer, Cost Optimization Hub |

The output is a single `Titanium.yaml` file — a complete, human-readable record of every landing zone decision. The Advisor validates the configuration before you move on.

### Stage 2 — Generate (Titanium Generator)

The Generator MCP server reads your `Titanium.yaml` and produces:

- **CloudFormation templates** — Standard YAML templates ready for deployment, one per logical resource group
- **LLM_AGENT_DEPLOYMENT_GUIDE.md** — A step-by-step deployment guide designed for your AI assistant to follow interactively
- **llm_agent_steps.json** — A machine-readable version of the deployment steps for programmatic access

> These two files (`LLM_AGENT_DEPLOYMENT_GUIDE.md` and `llm_agent_steps.json`) don't exist in the repo — the Generator creates them in your output directory when you generate templates.

Templates are generated per section. Each template is named with a convention that determines how it gets deployed:
- `stack-mgmt-*` → CloudFormation stack in the management account
- `stackset-*` → StackSet targeting specific accounts or OUs

For the full list of generated templates per module and current support status, see [About Titanium](ABOUT.md#generator-support-status).

### Stage 3 — Deploy (CloudFormation)

Your AI assistant follows the generated `LLM_AGENT_DEPLOYMENT_GUIDE.md` to deploy templates in the correct order. Deployment proceeds in five phases, each building on the previous. For the detailed breakdown of templates per phase, see [About Titanium](ABOUT.md#deployment-phases).

During deployment, the assistant:
- Resolves parameters dynamically (account IDs, OU IDs, bucket names)
- Prompts you for confirmation before each stack/StackSet deployment
- Waits for each deployment to complete before proceeding to the next
- Reports success or failure at each step

### Stage 4 — Verify

After deployment, the assistant verifies that your AWS environment matches the `Titanium.yaml` configuration — checking Organizations/OUs and SCPs, account placement, networking, security services, and centralized logging. For the full checklist, see [Step 5: Verify Deployment](DEPLOYMENT_GUIDE.md#step-5-verify-deployment).

## Learn More

- [Architecture Diagrams](docs/architecture-diagrams/README.md) — Visual overview of what Titanium deploys (accounts, networking, security)
- [Where Does Titanium Fit?](ABOUT.md) — How Titanium builds on AWS Control Tower
- [Titanium Advisor README](titanium-advisor/README.md) — Technical details on the Advisor MCP server
- [Titanium Generator README](titanium-generator/README.md) — Technical details on the Generator MCP server

## Team / Maintainers

Titanium is built and maintained by the Titanium Team. See [CONTRIBUTORS.md](CONTRIBUTORS.md) for the full list of contributors.

## Contributing

Contributions follow the [cloud-foundations-templates contribution guide](../CONTRIBUTING.md):

1. Fork the repository
2. Create a feature branch
3. Submit a pull request with a detailed description

## Support

- Create an issue in the [cloud-foundations-templates](https://github.com/cloud-foundations-on-aws/cloud-foundations-templates) repository

## License

This solution is part of the **cloud-foundations-templates** repository and is licensed under the MIT-0 License — see the repository-root [`LICENSE`](../LICENSE) file for details.

---

Ready to start? ➡️ [Step 1: Prerequisites & Setup](GETTING_STARTED.md)
