# Skill: sf-audit automation

Run a standalone Salesforce automation health audit on a live org.

## Activated by
`/sf-audit-automation [org-alias]`

## What This Skill Does

Inventories all automation in the org — Flows, Process Builder, Workflow Rules, Apex Triggers, and Validation Rules. Identifies legacy technologies that must be migrated, execution conflicts, flow errors, and trigger quality issues.

Output file: `SF-AUTOMATION.md` (written to current directory)

---

## Phase 1: Connectivity Check

```bash
sf org display --target-org [org-alias] --json
```

If this fails, instruct the user: `sf org login web --alias [alias]`

Extract: Org Name, Username, Org ID, Edition.

---

## Phase 2: Run Automation Queries

All metadata queries require `--use-tooling-api`:

```bash
# Active flows with type and API version
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT Id, ApiName, Label, ProcessType, Status, ApiVersion, LastModifiedDate, LastModifiedBy.Name FROM FlowDefinition WHERE Status = 'Active' ORDER BY ProcessType, LastModifiedDate DESC" \
  --json

# All flows for full inventory (active + inactive)
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT Id, ApiName, Label, ProcessType, Status, ApiVersion FROM FlowDefinition ORDER BY ProcessType, Status" \
  --json

# Flow errors in last 30 days
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT Id, InterviewLabel, CurrentElement, ErrorMessage, CreatedDate FROM FlowInterviewLog WHERE CreatedDate > LAST_N_DAYS:30 AND ErrorMessage != null ORDER BY CreatedDate DESC LIMIT 100" \
  --json

# Active Process Builder processes
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT Id, ApiName, Label, ProcessType, Status, ApiVersion, LastModifiedDate FROM FlowDefinition WHERE ProcessType = 'Workflow' AND Status = 'Active' ORDER BY LastModifiedDate DESC" \
  --json

# Active Workflow Rules
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT Id, Name, TableEnumOrId, IsActive, Description FROM WorkflowRule WHERE IsActive = true ORDER BY TableEnumOrId" \
  --json

# Total Workflow Rules (active + inactive)
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT IsActive, COUNT(Id) total FROM WorkflowRule GROUP BY IsActive" \
  --json

# All active Apex triggers
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT Id, Name, TableEnumOrId, Status, IsValid, ApiVersion, LengthWithoutComments, LastModifiedDate FROM ApexTrigger WHERE Status = 'Active' ORDER BY TableEnumOrId, Name" \
  --json

# Objects with multiple triggers
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT TableEnumOrId, COUNT(Id) triggerCount FROM ApexTrigger WHERE Status = 'Active' GROUP BY TableEnumOrId HAVING COUNT(Id) > 1 ORDER BY COUNT(Id) DESC" \
  --json

# Handler classes (for trigger pattern check)
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT Id, Name FROM ApexClass WHERE Status = 'Active' AND Name LIKE '%Handler%' ORDER BY Name" \
  --json

# All active Apex class names (for trigger handler cross-reference)
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT Id, Name FROM ApexClass WHERE Status = 'Active' ORDER BY Name" \
  --json

# Active validation rules
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT Id, Active, Description, ErrorMessage, ValidationName, EntityDefinition.QualifiedApiName FROM ValidationRule WHERE Active = true ORDER BY EntityDefinition.QualifiedApiName, ValidationName" \
  --json

# Validation rules per object
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT EntityDefinition.QualifiedApiName, COUNT(Id) ruleCount FROM ValidationRule WHERE Active = true GROUP BY EntityDefinition.QualifiedApiName ORDER BY COUNT(Id) DESC LIMIT 20" \
  --json
```

---

## Phase 3: Analyze & Score

**Flow type classification** (by `ProcessType`):
| ProcessType | Technology | Current? |
|------------|------------|----------|
| `Flow` | Screen Flow | Yes |
| `AutoLaunchedFlow` | Record-Triggered / Autolaunched Flow | Yes |
| `Workflow` | Process Builder | DEPRECATED |
| `InvocableProcess` | Invocable Process Builder | DEPRECATED |
| `CustomEvent` | Platform Event Flow | Yes |
| `Orchestrator` | Flow Orchestration | Yes |

**Legacy debt score:**
```
legacy_debt = (active_workflow_rules × 2) + (active_process_builder × 1)
```
- 0 = None | 1-5 = Low | 6-15 = Medium | 16-30 = High | >30 = Critical

**Trigger handler check:**
For each trigger named `[X]Trigger`, check if `[X]TriggerHandler` exists in Apex classes. Missing = flag.

**Validation rule quality:**
- No `Description` → undocumented
- `ErrorMessage` = generic ("Error", "Invalid") → poor UX
- Object with > 10 rules → flag for review

**Scoring (0–10 per dimension):**

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| Flow health | 25% | All current API + 0 errors=10; some errors=7; frequent errors=4; many outdated=2 |
| Process Builder | 20% | 0 active=10; 1-2=7; 3-5=5; 6-10=3; >10=1 |
| Workflow Rules | 20% | 0 active=10; 1-3=7; 4-10=5; 11-20=3; >20=1 |
| Trigger hygiene | 20% | All handler pattern + no multi-trigger=10; minor=7; no handlers + conflicts=3 |
| Validation quality | 15% | All documented=10; mostly ok=7; many undocumented=4 |

```
section_score = (flow×0.25 + pb×0.20 + wf×0.20 + trigger×0.20 + validation×0.15) × 10
```

**Grade:**
| Score | Grade |
|-------|-------|
| 90–100 | A+ |
| 80–89 | A |
| 70–79 | B |
| 60–69 | C |
| 50–59 | D |
| < 50 | F |

---

## Phase 4: Write SF-AUTOMATION.md

```markdown
# Salesforce Automation Health Report
**Org:** [name] | **Username:** [username] | **Edition:** [edition]
**Date:** [YYYY-MM-DD HH:MM UTC]
**Generated by:** /sf-audit automation

---

## Score: [XX]/100 — Grade [X]

### Dimension Scores
| Dimension | Score | Key Finding |
|:---------:|:-----:|:-----------:|
| Flow Health | [X]/10 | [n] active flows; [n] errors in 30 days |
| Process Builder (Legacy) | [X]/10 | [n] active — DEPRECATED |
| Workflow Rules (Legacy) | [X]/10 | [n] active — DEPRECATED |
| Apex Trigger Hygiene | [X]/10 | [n] triggers; [n] without handler pattern |
| Validation Rule Quality | [X]/10 | [n] rules; [n] undocumented |

### Automation Inventory
| Technology | Active | Inactive | Status | Risk |
|-----------|--------|----------|--------|------|
| Record-Triggered Flows | [n] | [n] | Current | LOW |
| Screen Flows | [n] | [n] | Current | LOW |
| Autolaunched Flows | [n] | [n] | Current | LOW |
| Process Builder | [n] | [n] | DEPRECATED | HIGH |
| Workflow Rules | [n] | [n] | DEPRECATED | HIGH |
| Apex Triggers | [n] | — | Current | Varies |
| Validation Rules | [n] | — | Current | LOW |

**Legacy Automation Debt Score: [n]** ([LOW/MEDIUM/HIGH/CRITICAL])

### Flow Error Analysis (Last 30 Days)
[Table of flows with errors, or "No flow errors detected."]

### Process Builder — Migration Required
[List each active PB process with name, object, API version, last modified, priority HIGH]
[Or: "No active Process Builder processes. Excellent!"]

### Workflow Rules — Migration Required
[List each active WF rule with name, object, description]
[Or: "No active Workflow Rules. Excellent!"]

### Apex Trigger Analysis
| Object | Trigger Count | Handler Exists | Issue |
|--------|--------------|----------------|-------|
| [Object] | [n] | ✓/✗ | None / No handler / Multiple triggers |

### Validation Rule Quality
| Object | Rules | Undocumented | Poor Error Messages |
|--------|-------|-------------|---------------------|
| [Object] | [n] | [n] | [n] |

### Migration Roadmap
**Priority 1 — Workflow Rules (retired technology, no Salesforce investment):**
[Numbered list of WF rules to migrate, with migration approach]

**Priority 2 — Process Builder (retired technology):**
[Numbered list of PB processes to migrate]

### Recommendations
[Critical / Important / Best Practices with specific names]

---
*Run `/sf-audit` for a full org health audit across all domains.*
```

---

## Phase 5: Terminal Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SF AUTOMATION AUDIT — [Org Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Score:            [XX]/100 (Grade [X])
  Active flows:     [n] (current)
  Process Builder:  [n] DEPRECATED
  Workflow Rules:   [n] DEPRECATED
  Legacy debt:      [n] ([LOW/MED/HIGH])
  Triggers:         [n] ([n] without handler)
  Flow errors:      [n] in last 30 days
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Report saved: SF-AUTOMATION.md
  Run /sf-audit [org] for full audit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Output Standards
- If `FlowInterviewLog` is unavailable, note it and skip flow errors section
- Legacy automation migration priority is always HIGH — these technologies are retired
- Be specific with names so admins can find automation in Setup directly
