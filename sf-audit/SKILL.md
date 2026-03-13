# SF Audit — Full Org Health Audit

Run a comprehensive Salesforce org health audit across all 9 domains simultaneously. And create a synthesized `SF-AUDIT.md` report with an overall health score, executive summary, and prioritized action matrix.

## Activated by
`/sf-audit [org-alias]`

## Special commands
- `/sf-audit --version` — print the installed version and exit
- `/sf-audit help` — print all available commands and exit

If either flag is passed, print the following and stop:
```
sf-audit v1.2.0
Available commands:
  /sf-audit [org]                Full audit — all 9 domains in parallel
  /sf-audit-security [org]       Security & access controls
  /sf-audit-data [org]           Data quality & completeness
  /sf-audit-automation [org]     Automation health & legacy debt
  /sf-audit-architecture [org]   Org architecture & limits
  /sf-audit-coverage [org]       Apex test coverage
  /sf-audit-naming [org]         Naming convention enforcement
  /sf-audit-orphaned [org]       Orphaned & inactive metadata
  /sf-audit-descriptions [org]   Description completeness
  /sf-audit-field-sprawl [org]   Custom field sprawl
  /sf-audit-report-pdf [org]     Generate PDF report
  /sf-audit-all                  Audit all authenticated orgs
  /sf-audit --version            Show version
```

## Available Commands

| Command | Output | Description |
|---------|--------|-------------|
| `/sf-audit [org-alias]` | `SF-AUDIT.md` | Full audit — all 9 domains in parallel |
| `/sf-audit-security [org-alias]` | `SF-SECURITY.md` | Security & access controls |
| `/sf-audit-data [org-alias]` | `SF-DATA-QUALITY.md` | Data quality & completeness |
| `/sf-audit-automation [org-alias]` | `SF-AUTOMATION.md` | Automation health & legacy debt |
| `/sf-audit-architecture [org-alias]` | `SF-ARCHITECTURE.md` | Org architecture & limits |
| `/sf-audit-coverage [org-alias]` | `SF-TEST-COVERAGE.md` | Apex test coverage |
| `/sf-audit-naming [org-alias]` | `SF-NAMING.md` | Naming convention enforcement |
| `/sf-audit-orphaned [org-alias]` | `SF-ORPHANED.md` | Orphaned & inactive metadata |
| `/sf-audit-descriptions [org-alias]` | `SF-DESCRIPTIONS.md` | Description completeness |
| `/sf-audit-field-sprawl [org-alias]` | `SF-FIELD-SPRAWL.md` | Custom field sprawl |
| `/sf-audit-report-pdf [org-alias]` | `SF-AUDIT-REPORT.pdf` | Generate PDF from audit data |

The `[org-alias]` is optional — if omitted, the default authenticated org is used.

---

## What This Skill Does

Dispatches 9 specialized subagents in parallel — each auditing a specific domain of the Salesforce org. Synthesizes results into a weighted Org Health Score (0–100) and produces a comprehensive `SF-AUDIT.md` report with executive summary and prioritized action matrix.

**The 9 domains audited in parallel:**
| Agent | Domain | Weight |
|-------|--------|--------|
| `sf-security` | Security & Access Controls | 20% |
| `sf-data-quality` | Data Quality & Completeness | 15% |
| `sf-automation` | Automation Health & Legacy Debt | 15% |
| `sf-architecture` | Org Architecture & Limits | 12% |
| `sf-coverage` | Apex Test Coverage | 8% |
| `sf-naming` | Naming Conventions | 8% |
| `sf-orphaned` | Orphaned Metadata | 8% |
| `sf-descriptions` | Description Completeness | 7% |
| `sf-field-sprawl` | Custom Field Sprawl | 7% |

---

## Phase 1: Discovery

### Step 1a — Verify org access

```bash
sf org display --target-org [org-alias] --json
```

If this fails:
- If no org-alias was provided: run `sf org list --json` to list available orgs, then ask the user to specify an alias
- If authentication expired: instruct the user to run `sf org login web --alias [alias]`
- Do not proceed until confirmed

Extract and store: `ORG_NAME`, `ORG_ID`, `ORG_EDITION`, `ORG_USERNAME`, `ORG_INSTANCE_URL`

**Pre-flight permission check:** Run the following to verify API access before dispatching agents:

```bash
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT Id FROM ApexClass LIMIT 1" --json
```

If this fails with `API_DISABLED_FOR_ORG` or a permissions error, stop and instruct the user:
> The authenticated user does not have API Enabled on their profile. Grant **API Enabled** and **View Setup and Configuration** permissions before running the audit.

Also check for a custom weights config file in the current directory:
```bash
# If sf-audit-weights-config.md exists, read and apply custom domain weights.
# Otherwise use defaults: Security=20%, Data=15%, Automation=15%, Architecture=12%,
# Coverage=8%, Naming=8%, Orphaned=8%, Descriptions=7%, FieldSprawl=7%
```

### Step 1b — Gather shared context

```bash
# Active user count
sf data query --target-org [org-alias] \
  --query "SELECT COUNT() FROM User WHERE IsActive = true" --json

# Custom object count
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT COUNT() FROM EntityDefinition WHERE IsCustomizable = true AND IsCustomSetting = false" --json

# Org edition
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT Id, Name, OrganizationType FROM Organization" --json
```

Print to terminal:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SALESFORCE ORG AUDIT STARTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Org:       [ORG_NAME]
  Username:  [ORG_USERNAME]
  Edition:   [ORG_EDITION]
  Users:     [ACTIVE_USERS] active
  Objects:   [CUSTOM_OBJECT_COUNT] custom
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Launching 9 parallel audit agents...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 2: Parallel Agent Dispatch

**CRITICAL: Launch all 9 agents simultaneously using the Task tool. Do NOT run them sequentially.**

Dispatch each Task with the following prompt structure:

```
You are the [AGENT_NAME] agent for a Salesforce org audit.

SHARED ORG CONTEXT:
ORG_ALIAS: [org-alias]
ORG_ID: [ORG_ID]
ORG_EDITION: [ORG_EDITION]
ORG_USERNAME: [ORG_USERNAME]
ACTIVE_USERS: [ACTIVE_USERS]
CUSTOM_OBJECT_COUNT: [CUSTOM_OBJECT_COUNT]

Run your full analysis following your agent instructions exactly.
Return your complete scored markdown section using your output template.
Do not truncate or summarize — return the full section.
```

**Task dispatches (all at once):**
1. Agent: `sf-security` — prompt as above
2. Agent: `sf-data-quality` — prompt as above
3. Agent: `sf-automation` — prompt as above
4. Agent: `sf-architecture` — prompt as above
5. Agent: `sf-coverage` — prompt as above
6. Agent: `sf-naming` — prompt as above
7. Agent: `sf-orphaned` — prompt as above
8. Agent: `sf-descriptions` — prompt as above
9. Agent: `sf-field-sprawl` — prompt as above

Wait for all 9 agents to complete before proceeding to Phase 3.

**Graceful degradation:** If any agent returns an error, times out, or produces no output:
- Mark that domain as `N/A` in the score table
- Exclude it from the weighted composite (redistribute its weight proportionally across remaining domains)
- Add a note in the Audit Metadata section: `[domain] — unavailable: [reason]`
- Do NOT abort the entire audit — partial results are still valuable

---

## Phase 3: Synthesis

### Calculate composite score

```
org_health_score = (
  security_score      × 0.20 +
  data_quality_score  × 0.15 +
  automation_score    × 0.15 +
  architecture_score  × 0.12 +
  test_coverage_score × 0.08 +
  naming_score        × 0.08 +
  orphaned_score      × 0.08 +
  descriptions_score  × 0.07 +
  field_sprawl_score  × 0.07
)
```

### Assign grade

| Score  | Grade | Label                                   |
|--------|-------|-----------------------------------------|
| 90–100 |   A+  | Excellent — Production-grade org        |
| 80–89  |   A   | Strong — Minor improvements recommended |
| 70–79  |   B   | Good — Some areas need attention        |
| 60–69  |   C   | Fair — Multiple risk areas identified   |
| 50–59  |   D   | Poor — Significant remediation required |
| < 50   |   F   | Critical — Immediate action required    |

### Build Priority Action Matrix

- **Critical (act within 1 week):** Any dimension < 40, security data exposure, any limit ≥ 95%, org coverage < 60%
- **Important (act within 1 month):** Dimensions 40–65, legacy automation, inactive users, stale data, legacy API versions
- **Strategic (this quarter):** Dimensions 65–79, migration roadmaps, architecture improvements

---

## Phase 4: Write SF-AUDIT.md

Write **two files** to the current working directory:
1. `SF-AUDIT-[YYYY-MM-DD].md` — dated archive (e.g. `SF-AUDIT-2026-03-13.md`)
2. `SF-AUDIT.md` — latest report (always overwritten; used by PDF generation)

Both files have identical content. The dated file allows tracking org health over time.

```markdown
# Salesforce Org Health Audit
**Org:** [ORG_NAME] | **Username:** [ORG_USERNAME] | **Edition:** [ORG_EDITION]
**Audit Date:** [YYYY-MM-DD HH:MM UTC]
**Instance:** [ORG_INSTANCE_URL]
**Generated by:** sf-audit (Claude Code)

---

## Overall Org Health Score

╔═══════════════════════════════════════╗
║   ORG HEALTH SCORE:  [XX] / 100      ║
║   Grade: [X]  —  [Label]             ║
╚═══════════════════════════════════════╝

| Domain                  | Weight |  Score  | Grade |  Status |
|-------------------------|--------|---------|-------|---------|
| Security & Access       |   20%  |[XX]/100 |  [X]  | ✅/⚠️/❌ |
| Data Quality            |   15%  |[XX]/100 |  [X]  | ✅/⚠️/❌ |
| Automation Health       |   15%  |[XX]/100 |  [X]  | ✅/⚠️/❌ |
| Org Architecture        |   12%  |[XX]/100 |  [X]  | ✅/⚠️/❌ |
| Test Coverage           |    8%  |[XX]/100 |  [X]  | ✅/⚠️/❌ |
| Naming Conventions      |    8%  |[XX]/100 |  [X]  | ✅/⚠️/❌ |
| Orphaned Metadata       |    8%  |[XX]/100 |  [X]  | ✅/⚠️/❌ |
| Description Completeness|    7%  |[XX]/100 |  [X]  | ✅/⚠️/❌ |
| Custom Field Sprawl     |    7%  |[XX]/100 |  [X]  | ✅/⚠️/❌ |

*✅ PASS ≥ 70 | ⚠️ WARN 50–69 | ❌ FAIL < 50*

---

## Executive Summary
[3–5 paragraphs, non-technical language]

---

## Priority Action Matrix
### ❌ Critical — Act Within 1 Week
### ⚠️ Important — Act Within 1 Month
### 📋 Strategic — Plan for This Quarter

---

[PASTE FULL SECTION 1 from sf-security agent]
[PASTE FULL SECTION 2 from sf-data-quality agent]
[PASTE FULL SECTION 3 from sf-automation agent]
[PASTE FULL SECTION 4 from sf-architecture agent]
[PASTE FULL SECTION 5 from sf-coverage agent]
[PASTE FULL SECTION 6 from sf-naming agent]
[PASTE FULL SECTION 7 from sf-orphaned agent]
[PASTE FULL SECTION 8 from sf-descriptions agent]
[PASTE FULL SECTION 9 from sf-field-sprawl agent]

---

## Audit Metadata
| Item | Value |
|------|-------|
| sf CLI version | [sf --version] |
| API version | v62.0 |
| Execution mode | Parallel (9 agents) |
| Report generated | [timestamp] |
| Limitations | [any skipped queries] |

---
*Run individual domain commands for focused reports:*
- `/sf-audit-security [org]` → SF-SECURITY.md
- `/sf-audit-data [org]` → SF-DATA-QUALITY.md
- `/sf-audit-automation [org]` → SF-AUTOMATION.md
- `/sf-audit-architecture [org]` → SF-ARCHITECTURE.md
- `/sf-audit-coverage [org]` → SF-TEST-COVERAGE.md
- `/sf-audit-naming [org]` → SF-NAMING.md
- `/sf-audit-orphaned [org]` → SF-ORPHANED.md
- `/sf-audit-descriptions [org]` → SF-DESCRIPTIONS.md
- `/sf-audit-field-sprawl [org]` → SF-FIELD-SPRAWL.md
- `/sf-audit-report-pdf [org]` → SF-AUDIT-REPORT.pdf
```

---

## Phase 5: Terminal Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SALESFORCE ORG HEALTH AUDIT COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Org:    [ORG_NAME] ([ORG_EDITION])

  OVERALL HEALTH SCORE: [XX]/100 — Grade [X]

  ┌──────────────────────────┬────────┬────────┐
  │ Domain                   │ Weight │ Score  │
  ├──────────────────────────┼────────┼────────┤
  │ Security & Access        │  20%   │ [XX]   │
  │ Data Quality             │  15%   │ [XX]   │
  │ Automation Health        │  15%   │ [XX]   │
  │ Org Architecture         │  12%   │ [XX]   │
  │ Test Coverage            │   8%   │ [XX]   │
  │ Naming Conventions       │   8%   │ [XX]   │
  │ Orphaned Metadata        │   8%   │ [XX]   │
  │ Description Completeness │   7%   │ [XX]   │
  │ Custom Field Sprawl      │   7%   │ [XX]   │
  └──────────────────────────┴────────┴────────┘

  TOP PRIORITIES:
  1. [Top critical finding]
  2. [Second priority]
  3. [Third priority]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Full report saved: SF-AUDIT.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 6: Auto-Generate PDF Report

After the Phase 5 terminal summary, automatically trigger the PDF skill:

```
Run /sf-audit-report-pdf [org-alias]
```

Generates `SF-AUDIT-REPORT.pdf` in the current directory. No user prompt required — run automatically after every full audit.

---


## Output Standards

- Phase 2 MUST dispatch all 9 agents simultaneously — parallel execution is required
- Paste full agent sections verbatim into SF-AUDIT.md — do not summarize
- Executive summary must be in plain language — no SOQL, no technical jargon
- Score thresholds: ✅ PASS ≥ 70 | ⚠️ WARN 50–69 | ❌ FAIL < 50
