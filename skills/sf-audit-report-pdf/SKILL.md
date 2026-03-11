# Skill: sf-audit report-pdf

Generate a professional, print-ready PDF report from a Salesforce org audit.

## Activated by
`/sf-audit-report-pdf [org-alias]`

## What This Skill Does

Compiles Salesforce audit data into a clean, client-ready PDF report using `scripts/generate_sf_pdf_report.py`. Produces a multi-page document with score gauges, domain breakdowns, findings tables, and a prioritized action plan — styled with light, clean colors suitable for sharing with stakeholders or clients.

Output file: `SF-AUDIT-REPORT.pdf` (written to current directory)

---

## Phase 1: Collect Audit Data

Check the current directory for existing audit reports (most recent run):

```bash
ls -la SF-AUDIT.md SF-SECURITY.md SF-DATA-QUALITY.md SF-AUTOMATION.md SF-ARCHITECTURE.md SF-TEST-COVERAGE.md SF-NAMING.md SF-ORPHANED.md SF-DESCRIPTIONS.md SF-FIELD-SPRAWL.md 2>/dev/null
```

**If `SF-AUDIT.md` exists:** Use it as the primary data source — extract all 5 section scores and findings.

**If only individual reports exist (no full SF-AUDIT.md):** Combine available reports.

**If no audit data exists:** Run a full audit first:
```
Inform the user: "No audit data found. Running /sf-audit [org-alias] first..."
```
Then proceed with the audit skill before continuing.

---

## Phase 2: Extract & Structure Data

Parse the available audit markdown files and extract:

- **Org name, username, edition, audit date** (from report header)
- **Overall score** (0–100) and grade (if SF-AUDIT.md exists)
- **Per-domain scores** (Security, Data Quality, Automation, Architecture, Test Coverage, Naming Conventions, Orphaned Metadata, Description Completeness, Custom Field Sprawl)
- **Per-domain dimension scores** (extract the Dimension Scores table from each domain section — values 0–10 per dimension)
- **Per-domain top findings** (up to 3 Critical/Important findings per domain)
- **Priority Action Matrix items** (Critical / Important / Strategic)

If the full composite score doesn't exist (individual reports only), calculate it:
```
overall_score = (security × 0.20) + (data_quality × 0.15) + (automation × 0.15) + (architecture × 0.12) + (test_coverage × 0.08) + (naming × 0.08) + (orphaned × 0.08) + (descriptions × 0.07) + (field_sprawl × 0.07)
```

---

## Phase 3: Build JSON for PDF Script

Write a temporary JSON file at `/tmp/sf_report_data.json` with this exact structure:

```json
{
  "org_name": "Acme Corp",
  "org_username": "admin@acme.com",
  "org_edition": "Enterprise Edition",
  "audit_date": "March 10, 2026",
  "overall_score": 72,
  "grade": "B",
  "executive_summary": "2-4 sentence summary of org health, top risk, top strength, and immediate priority.",
  "domains": {
    "Security & Access": {
      "score": 65, "weight": "20%",
      "dimension_scores": {"Profile Hygiene": 6, "Permission Set Sprawl": 7, "Sharing Model": 8, "MFA Enforcement": 5, "IP/Session Restrictions": 4, "Field-Level Security": 7},
      "top_findings": ["2 non-admin profiles with Modify All Data", "14 users inactive 90+ days"]
    },
    "Data Quality": {
      "score": 78, "weight": "15%",
      "dimension_scores": {"Contact Completeness": 8, "Account Completeness": 7, "Lead Hygiene": 6, "Duplicate Rule Coverage": 9, "Opportunity Hygiene": 7},
      "top_findings": ["Contact Email null rate 18%"]
    },
    "Automation Health": {
      "score": 70, "weight": "15%",
      "dimension_scores": {"Flow Health": 7, "Process Builder Debt": 5, "Workflow Rules": 4, "Trigger Hygiene": 8, "Validation Quality": 8},
      "top_findings": ["6 active Workflow Rules", "3 Process Builder processes"]
    },
    "Org Architecture": {
      "score": 82, "weight": "12%",
      "dimension_scores": {"Object/Field Sprawl": 8, "Governor Limits": 9, "Apex API Version Debt": 7, "Package Health": 9, "Custom Settings vs CMDT": 6},
      "top_findings": ["8 classes on API v45"]
    },
    "Test Coverage": {
      "score": 68, "weight": "8%",
      "dimension_scores": {"Org-Wide Coverage %": 7, "Classes Below 75%": 6, "Test Class Quality": 7, "Trigger Coverage": 8},
      "top_findings": ["4 classes below 75% coverage"]
    },
    "Naming Conventions": {
      "score": 74, "weight": "8%",
      "dimension_scores": {"Apex Class Naming": 7, "Apex Trigger Naming": 8, "Custom Field Naming": 7, "Flow Naming": 6, "Validation Rule Naming": 7},
      "top_findings": ["28% of classes missing type suffix"]
    },
    "Orphaned Metadata": {
      "score": 72, "weight": "8%",
      "dimension_scores": {"Inactive Flows": 8, "Dead Validation Rules": 7, "Deactivated Workflow Rules": 6, "Stale Custom Fields": 7},
      "top_findings": ["12 inactive flows", "5 deactivated validation rules"]
    },
    "Description Completeness": {
      "score": 55, "weight": "7%",
      "dimension_scores": {"Custom Field Help Text": 4, "Flow Descriptions": 5, "Validation Rule Descriptions": 6, "Object Descriptions": 5, "Apex Class Doc Comments": 6},
      "top_findings": ["62% of fields missing help text", "38% of flows undocumented"]
    },
    "Custom Field Sprawl": {
      "score": 80, "weight": "7%",
      "dimension_scores": {"Objects >=100 Fields": 8, "Objects 50-99 Fields": 7, "Stale Fields >730 days": 8, "Duplicate-Purpose Fields": 8},
      "top_findings": ["1 object at 127 custom fields"]
    }
  },
  "findings": [
    {"severity": "Critical", "domain": "Security", "finding": "Specific finding text"},
    {"severity": "Critical", "domain": "Automation", "finding": "Specific finding text"},
    {"severity": "High", "domain": "Data Quality", "finding": "Specific finding text"},
    {"severity": "Medium", "domain": "Test Coverage", "finding": "Specific finding text"}
  ],
  "critical_actions": [
    "Specific action item 1",
    "Specific action item 2"
  ],
  "important_actions": [
    "Specific action item 1",
    "Specific action item 2"
  ],
  "strategic_actions": [
    "Specific action item 1",
    "Specific action item 2"
  ],
  "audit_metadata": {
    "queries_run": "42",
    "api_version": "v62.0",
    "execution_mode": "Parallel (9 agents)"
  }
}
```

Write this to `/tmp/sf_report_data.json`:
```bash
cat > /tmp/sf_report_data.json << 'JSONEOF'
{ ... populated JSON ... }
JSONEOF
```

---

## Phase 4: Install reportlab if Needed

```bash
python3 -c "import reportlab" 2>/dev/null || pip3 install reportlab --quiet
```

---

## Phase 5: Generate PDF

```bash
python3 scripts/generate_sf_pdf_report.py /tmp/sf_report_data.json "SF-AUDIT-REPORT.pdf"
```

---

## Phase 6: Verify & Cleanup

```bash
ls -lh "SF-AUDIT-REPORT.pdf"
rm -f /tmp/sf_report_data.json
```

---

## Phase 7: Terminal Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SF AUDIT PDF REPORT GENERATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Org:    [Org Name] ([Edition])
  Score:  [XX]/100 — Grade [X]
  File:   SF-AUDIT-REPORT.pdf
  Size:   [file size]
  Pages:  ~14 (1 cover + 1 overview + 9 domain + findings + action plan + methodology)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## PDF Contents

|   Page    |                                 Content                                  |
|:---------:|:------------------------------------------------------------------------:|
|     1     |   Cover — org name, score gauge, grade, executive summary, quick scores  |
|     2     |  Domain Overview — all-domains bar chart + score table with weights      |
|   3–11    |  Per-Domain pages — each with score gauge, dimension bar chart, findings  |
|    12     |              Key Findings — all findings, severity-coded                 |
|    13     |  Action Plan — Critical / Important / Strategic with timeline guidance   |
|    14     |      Methodology — scoring weights, grade scale, audit metadata          |

---

## Data Quality Rules

- Use only real data extracted from audit reports — never fabricate scores
- Findings must be specific (include object names, counts, percentages from the audit)
- Executive summary: 2–4 sentences maximum, non-technical language
- Scores must be integers (0–100)
- If a domain report is missing, mark that domain as "N/A" in the JSON

---

## Troubleshooting

|        Problem        |                                        Solution                                        |
|:---------------------:|:--------------------------------------------------------------------------------------:|
| `reportlab` not found |                              Run `pip3 install reportlab`                              |
|   Script not found    |       Ensure `scripts/generate_sf_pdf_report.py` exists — re-run `./install.sh`        |
|       Empty PDF       | Validate JSON: `python3 -c "import json; json.load(open('/tmp/sf_report_data.json'))"` |
|     No audit data     |             Run `/sf-audit [org]` first, then `/sf-audit report-pdf [org]`             |
