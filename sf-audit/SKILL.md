# SF Audit — Full Org Health Audit

Run a comprehensive Salesforce org health audit across all 5 domains simultaneously. And create a synthesized `SF-AUDIT.md` report with an overall health score, executive summary, and prioritized action matrix.

## Activated by
`/sf-audit [org-alias]`

## Available Commands

| Command | Output | Description |
|---------|--------|-------------|
| `/sf-audit [org-alias]` | `SF-AUDIT.md` | Full audit — all 6 domains in parallel |
| `/sf-audit-security [org-alias]` | `SF-SECURITY.md` | Security & access controls |
| `/sf-audit-data [org-alias]` | `SF-DATA-QUALITY.md` | Data quality & completeness |
| `/sf-audit-automation [org-alias]` | `SF-AUTOMATION.md` | Automation health & legacy debt |
| `/sf-audit-architecture [org-alias]` | `SF-ARCHITECTURE.md` | Org architecture & limits |
| `/sf-audit-coverage [org-alias]` | `SF-TEST-COVERAGE.md` | Apex test coverage |
| `/sf-audit-naming [org-alias]` | `SF-NAMING.md` | Naming conventions audit |
| `/sf-audit-report-pdf [org-alias]` | `SF-AUDIT-REPORT.pdf` | Generate PDF from audit data |

The `[org-alias]` is optional — if omitted, the default authenticated org is used.

---

## What This Skill Does

Dispatches 6 specialized subagents in parallel — each auditing a specific domain of the Salesforce org. Synthesizes results into a weighted Org Health Score (0–100) and produces a comprehensive `SF-AUDIT.md` report with executive summary and prioritized action matrix.

**The 6 domains audited in parallel:**
| Agent | Domain | Weight |
|-------|--------|--------|
| `sf-security` | Security & Access Controls | 25% |
| `sf-data-quality` | Data Quality & Completeness | 20% |
| `sf-automation` | Automation Health & Legacy Debt | 20% |
| `sf-architecture` | Org Architecture & Limits | 15% |
| `sf-test-coverage` | Apex Test Coverage | 10% |
| `sf-naming` | Naming Conventions | 10% |

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
  Launching 6 parallel audit agents...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 2: Parallel Agent Dispatch

**CRITICAL: Launch all 6 agents simultaneously using the Task tool. Do NOT run them sequentially.**

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
5. Agent: `sf-test-coverage` — prompt as above
6. Agent: `sf-naming` — prompt as above

Wait for all 6 agents to complete before proceeding to Phase 3.

---

## Phase 3: Synthesis

### Calculate composite score

```
org_health_score = (
  security_score      × 0.25 +
  data_quality_score  × 0.20 +
  automation_score    × 0.20 +
  architecture_score  × 0.15 +
  test_coverage_score × 0.10 +
  naming_score        × 0.10
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

Write this complete file to the current working directory:

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

| Domain               | Weight |  Score  | Grade |  Status |
|----------------------|--------|---------|-------|---------|
| Security & Access    |   25%  |[XX]/100 |  [X]  | ✅/⚠️/❌ |
| Data Quality         |   20%  |[XX]/100 |  [X]  | ✅/⚠️/❌ |
| Automation Health    |   20%  |[XX]/100 |  [X]  | ✅/⚠️/❌ |
| Org Architecture     |   15%  |[XX]/100 |  [X]  | ✅/⚠️/❌ |
| Test Coverage        |   10%  |[XX]/100 |  [X]  | ✅/⚠️/❌ |
| Naming Conventions   |   10%  |[XX]/100 |  [X]  | ✅/⚠️/❌ |

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
[PASTE FULL SECTION 5 from sf-test-coverage agent]
[PASTE FULL SECTION 6 from sf-naming agent]

---

## Audit Metadata
| Item | Value |
|------|-------|
| sf CLI version | [sf --version] |
| API version | v62.0 |
| Execution mode | Parallel (6 agents) |
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

  ┌─────────────────────────┬────────┬────────┐
  │ Domain                  │ Weight │ Score  │
  ├─────────────────────────┼────────┼────────┤
  │ Security & Access       │  25%   │ [XX]   │
  │ Data Quality            │  20%   │ [XX]   │
  │ Automation Health       │  20%   │ [XX]   │
  │ Org Architecture        │  15%   │ [XX]   │
  │ Test Coverage           │  10%   │ [XX]   │
  │ Naming Conventions      │  10%   │ [XX]   │
  └─────────────────────────┴────────┴────────┘

  TOP PRIORITIES:
  1. [Top critical finding]
  2. [Second priority]
  3. [Third priority]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Full report saved: SF-AUDIT.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Output Standards

- Phase 2 MUST dispatch all 6 agents simultaneously — parallel execution is required
- Paste full agent sections verbatim into SF-AUDIT.md — do not summarize
- Executive summary must be in plain language — no SOQL, no technical jargon
- Score thresholds: ✅ PASS ≥ 70 | ⚠️ WARN 50–69 | ❌ FAIL < 50
