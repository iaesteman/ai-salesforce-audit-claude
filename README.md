# AI Salesforce Audit — Claude Code

AI-powered Salesforce org health auditing tool for [Claude Code](https://claude.ai/code). Runs 5 parallel AI agents to audit your org across security, data quality, automation health, architecture, and test coverage — producing a scored health report in seconds.

---

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/iaesteman/ai-salesforce-audit-claude/main/install.sh | bash
```

Then start a new Claude Code session.

> **Manual install (alternative):**
> ```bash
> git clone https://github.com/iaesteman/ai-salesforce-audit-claude.git
> cd ai-salesforce-audit-claude
> ./install.sh
> ```

---

## Prerequisites

- [Claude Code](https://claude.ai/code) installed
- [Salesforce CLI](https://developer.salesforce.com/tools/salesforcecli) (`sf`) installed
- An authenticated Salesforce org:
  ```bash
  sf org login web --alias my-org
  ```

---

## Usage

### Full Org Audit (all 5 domains in parallel)

```
/sf-audit [org-alias]
```

Runs all 5 agents simultaneously and produces a comprehensive `SF-AUDIT.md` with:
- Weighted Org Health Score (0–100) with letter grade
- Executive summary (non-technical)
- Priority Action Matrix (Critical / Important / Strategic)
- Detailed findings for all 5 domains

### Standalone Domain Audits

Run any single domain for a focused, faster report:

| Command | Output | Domain |
|---------|--------|--------|
| `/sf-audit security [org]` | `SF-SECURITY.md` | Profiles, perm sets, sharing model, MFA, login activity |
| `/sf-audit data [org]` | `SF-DATA-QUALITY.md` | Contact/Account/Lead completeness, duplicates, stale records |
| `/sf-audit automation [org]` | `SF-AUTOMATION.md` | Flows, Process Builder, Workflow Rules, Apex triggers |
| `/sf-audit architecture [org]` | `SF-ARCHITECTURE.md` | Limits, custom objects, Apex API versions, packages |
| `/sf-audit coverage [org]` | `SF-TEST-COVERAGE.md` | Apex test coverage %, classes below 75%, test failures |

The `[org-alias]` is optional — omit to audit your default authenticated org.

---

## What Gets Audited

### Security & Access (30% weight)
- Profiles with dangerous permissions (Modify All Data, View All Data)
- Permission set sprawl and over-permissioned users
- Object-wide default sharing settings
- MFA enforcement status
- IP restrictions and session policies
- Login failure patterns and suspicious activity
- Stale active users (no login in 90+ days)

### Data Quality (20% weight)
- Contact completeness: Email, Phone, Account linkage
- Account completeness: Industry, Type, Phone, BillingCity
- Lead hygiene: Stale open leads, missing email
- Opportunity hygiene: Stale pipeline, overdue close dates
- Active duplicate rules coverage
- Orphaned and unlinked records

### Automation Health (20% weight)
- Active Flows inventory and error analysis
- Process Builder processes (deprecated — migration required)
- Workflow Rules (deprecated — migration required)
- Apex trigger quality: handler pattern, multi-trigger conflicts
- Validation rule documentation quality
- Legacy automation debt score

### Org Architecture (15% weight)
- Governor limit consumption (API calls, data storage, file storage)
- Custom object and field sprawl vs. edition limits
- Apex class API version distribution
- Classes not modified in 2+ years (dead code risk)
- Installed managed packages and license utilization
- Custom Settings vs. Custom Metadata Types usage

### Test Coverage (15% weight)
- Org-wide Apex test coverage percentage
- Classes and triggers below 75% deployment threshold
- Recent test run results and failure analysis
- Test class quality and test-to-production ratio

---

## Scoring

Each domain is scored 0–100, then weighted into a composite Org Health Score:

| Score | Grade | Label |
|-------|-------|-------|
| 90–100 | A+ | Excellent — Production-grade org |
| 80–89 | A | Strong — Minor improvements recommended |
| 70–79 | B | Good — Some areas need attention |
| 60–69 | C | Fair — Multiple risk areas identified |
| 50–59 | D | Poor — Significant remediation required |
| < 50 | F | Critical — Immediate action required |

---

## Architecture

```
ai-salesforce-audit-claude/
├── sf-audit/SKILL.md              ← Main router (handles all /sf-audit commands)
├── skills/
│   ├── sf-audit/SKILL.md          ← Full parallel audit orchestrator
│   ├── sf-security/SKILL.md       ← Standalone security skill
│   ├── sf-data-quality/SKILL.md   ← Standalone data quality skill
│   ├── sf-automation/SKILL.md     ← Standalone automation skill
│   ├── sf-architecture/SKILL.md   ← Standalone architecture skill
│   └── sf-test-coverage/SKILL.md  ← Standalone test coverage skill
├── agents/
│   ├── sf-security.md             ← Security agent (used in full audit)
│   ├── sf-data-quality.md         ← Data quality agent
│   ├── sf-automation.md           ← Automation agent
│   ├── sf-architecture.md         ← Architecture agent
│   └── sf-test-coverage.md        ← Test coverage agent
├── install.sh
└── uninstall.sh
```

**How it works:**
1. `/sf-audit [org]` → router parses input → routes to full audit skill
2. Full audit skill runs Phase 1 (discovery) → Phase 2 (dispatches 5 agents in parallel) → Phase 3 (synthesis)
3. Each agent queries the live org via `sf` CLI and Tooling API, scores its domain, returns a section
4. Orchestrator combines sections into the final weighted score and `SF-AUDIT.md`

---

## Uninstall

```bash
./uninstall.sh
```

---

## Data Access & Privacy

This tool queries your Salesforce org using **read-only SOQL and Tooling API calls**. It does not:
- Modify any Salesforce data or configuration
- Store or transmit org data outside your local Claude Code session
- Require system administrator credentials beyond what SOQL/Tooling API access requires

The authenticated user running the audit should have API access and read permissions on the objects being queried (Profiles, PermissionSets, LoginHistory, etc.). System Administrator profile is recommended for full audit coverage.

---

## Limitations

- **MFA enforcement status** cannot always be determined via SOQL — manual verification in Setup > Identity Verification may be required
- **Sharing rules** (beyond OWD settings) require Metadata API access — the audit notes this as a manual review item
- **Field-Level Security** gaps are assessed heuristically — a full FLS audit requires Metadata API retrieval
- **Flow Interview Logs** may not be available in all orgs — requires Flow Debug Logging to be enabled
- **Tooling API** access is required for Apex, Flow, and metadata queries — the authenticated user must have API Enabled on their profile

---

## Contributing

Issues and PRs welcome. When adding new audit checks, follow the agent pattern in `agents/sf-security.md` — each check should include: the SOQL query, the scoring logic, and the output template section.
