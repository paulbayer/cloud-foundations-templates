# Step 2: Design Your Landing Zone

This guide walks you through the AI-guided interview that produces your `Titanium.yaml` configuration file.

## Choose Your Overlay

Titanium supports multiple industry overlays that tailor the interview to your organization:

| Overlay | Best For | Duration |
|---------|----------|----------|
| **Starter** (recommended) | Small-to-medium orgs, first-time users | ~15–20 min |
| Enterprise | Large corporate environments, multi-region | ~30–40 min |
| UK Public Sector | UK government, NCSC compliance | ~30–40 min |
| US Government | Federal/state agencies, FedRAMP/NIST | ~30–40 min |

If you're unsure, start with **Starter**. You can always re-run the interview with a different overlay later.

## Run the Interview

Start a conversation with your AI assistant:

> "I need to design a landing zone for my organization. Can you help me through the process?"

The assistant will:
1. Ask which industry overlay to use
2. Walk you through each section of the interview (organization, security, networking, etc.)
3. Compile your answers into a `Titanium.yaml` configuration file
4. Offer to validate the generated configuration

### What You'll Be Asked About

The interview covers nine sections:

| Section | Example Questions |
|---------|------------------|
| Global | Home region, enabled regions |
| Control Tower | Landing zone version, logging retention |
| Organization | OU structure, service control policies |
| Identity & Access | Password policy, SSO, access analyzer |
| Logging | CloudTrail, VPC Flow Logs, log retention |
| Security | GuardDuty, SecurityHub, compliance standards |
| Accounts | Infrastructure accounts, workload accounts |
| Network | VPCs, Transit Gateway, IPAM, DNS |
| Finance | Budgets, cost allocation, CUR |

The Starter overlay simplifies most of these to Yes/No questions.

## Review Your Titanium.yaml

After the interview, review the generated file:

1. **Check email addresses** — Search for `@example.com` and replace with real addresses
2. **Verify regions** — Confirm your home region and enabled regions are correct
3. **Validate** — Ask the assistant:

   > "Can you validate my Titanium.yaml configuration?"

The assistant will run the validation tool and report any issues.

## Example Configurations

The repository includes example configurations you can reference:

- `Titanium.yaml` (repo root) — a complete standard example
- `titanium-advisor/output-examples/` — per-overlay samples: `starter-example.yaml`, `uk-council.yaml`, `us-federal.yaml`

## Next Step

➡️ [Step 3: Deploy to AWS](DEPLOYMENT_GUIDE.md)
