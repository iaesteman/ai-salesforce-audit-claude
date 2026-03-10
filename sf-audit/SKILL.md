# SF Audit — Main Orchestrator

AI-powered Salesforce org health auditing tool. Run a full audit or target a specific domain.

## Commands

| Command | Description |
|---------|-------------|
| `/sf-audit [org-alias]` | Full audit — all 5 domains in parallel → `SF-AUDIT.md` |
| `/sf-audit security [org-alias]` | Security & access controls → `SF-SECURITY.md` |
| `/sf-audit data [org-alias]` | Data quality & completeness → `SF-DATA-QUALITY.md` |
| `/sf-audit automation [org-alias]` | Automation health & legacy debt → `SF-AUTOMATION.md` |
| `/sf-audit architecture [org-alias]` | Org architecture & limits → `SF-ARCHITECTURE.md` |
| `/sf-audit coverage [org-alias]` | Apex test coverage → `SF-TEST-COVERAGE.md` |
| `/sf-audit report-pdf [org-alias]` | Generate clean PDF report from audit data → `SF-AUDIT-REPORT.pdf` |

The `[org-alias]` is optional — if omitted, the default authenticated org is used.

---

## Routing Logic

Parse the user's input after `/sf-audit` to determine the action:

1. **No arguments** or **only an org alias** (no keyword match):
   → Route to: `skills/sf-audit` (full audit)
   → Pass: `[org-alias]` (if provided) or `--target-org` default org

2. **First argument is `security`**:
   → Route to: `skills/sf-security`
   → Pass: remaining argument as `[org-alias]`

3. **First argument is `data`**:
   → Route to: `skills/sf-data-quality`
   → Pass: remaining argument as `[org-alias]`

4. **First argument is `automation`**:
   → Route to: `skills/sf-automation`
   → Pass: remaining argument as `[org-alias]`

5. **First argument is `architecture`**:
   → Route to: `skills/sf-architecture`
   → Pass: remaining argument as `[org-alias]`

6. **First argument is `coverage`**:
   → Route to: `skills/sf-test-coverage`
   → Pass: remaining argument as `[org-alias]`

7. **First argument is `report-pdf`**:
   → Route to: `skills/sf-report-pdf`
   → Pass: remaining argument as `[org-alias]`

8. **Unrecognized argument**:
   → Print the commands table above and ask the user to try again

---

## Org Alias Resolution

If an org alias is provided, use it as `--target-org [alias]` in all `sf` CLI calls.

If no alias is provided:
1. Run `sf org display --json` (uses the default org)
2. If that fails, run `sf org list --json` to show available orgs
3. Ask the user to specify an alias from the list

---

## Context Detection

Before routing, detect the business context to help agents tailor their output:

```bash
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT Id, Name, OrganizationType FROM Organization" --json
```

Pass the `OrganizationType` (e.g., "Enterprise Edition", "Developer Edition", "Professional Edition") to the routed skill so it can adjust limit thresholds and recommendations accordingly.

---

## Output Standards

- All reports are saved as markdown or PDF files in the current working directory
- Full audit: `SF-AUDIT.md`
- Individual skills: `SF-SECURITY.md`, `SF-DATA-QUALITY.md`, `SF-AUTOMATION.md`, `SF-ARCHITECTURE.md`, `SF-TEST-COVERAGE.md`
- PDF report: `SF-AUDIT-REPORT.pdf` (requires `reportlab`: `pip3 install reportlab`)
- Reports reference each other: a `SF-SECURITY.md` from a prior run is noted in the full `SF-AUDIT.md` executive summary if it exists
- Scores use a 0–100 scale with letter grades: A+ (90-100), A (80-89), B (70-79), C (60-69), D (50-59), F (<50)
- All recommendations are specific, actionable, and reference exact Salesforce Setup paths or component names

---

## Prerequisites

- Salesforce CLI (`sf`) installed and in PATH
- At least one authenticated org: `sf org login web --alias my-org`
- For Tooling API queries: the authenticated user must have API access enabled on their profile

---

## Quick Start Examples

```bash
# Audit your default org
/sf-audit

# Audit a specific sandbox
/sf-audit my-sandbox

# Check only security on production
/sf-audit security prod

# Check only test coverage on developer org
/sf-audit coverage dev-org

# Check data quality issues
/sf-audit data my-sandbox

# Generate a PDF report from a previous audit
/sf-audit report-pdf my-sandbox
```
