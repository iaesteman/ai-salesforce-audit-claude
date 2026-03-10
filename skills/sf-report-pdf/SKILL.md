# Skill: sf-audit report-pdf

Generate a professional, print-ready PDF report from a Salesforce org audit.

## Activated by
`/sf-audit report-pdf [org-alias]`

## What This Skill Does

Compiles Salesforce audit data into a clean, client-ready PDF report using `scripts/generate_sf_pdf_report.py`. Produces a multi-page document with score gauges, domain breakdowns, findings tables, and a prioritized action plan — styled with light, clean colors suitable for sharing with stakeholders or clients.

Output file: `SF-AUDIT-REPORT.pdf` (written to current directory)

---

## Phase 1: Collect Audit Data

Check the current directory for existing audit reports (most recent run):

```bash
ls -la SF-AUDIT.md SF-SECURITY.md SF-DATA-QUALITY.md SF-AUTOMATION.md SF-ARCHITECTURE.md SF-TEST-COVERAGE.md 2>/dev/null
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
- **Per-domain scores** (Security, Data Quality, Automation, Architecture, Test Coverage)
- **Top findings per domain** (Critical and Important items from recommendations sections)
- **Priority Action Matrix items** (Critical / Important / Strategic)

If the full composite score doesn't exist (individual reports only), calculate it:
```
overall_score = (security × 0.30) + (data_quality × 0.20) + (automation × 0.20) + (architecture × 0.15) + (test_coverage × 0.15)
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
    "Security & Access": {"score": 65, "weight": "30%"},
    "Data Quality": {"score": 78, "weight": "20%"},
    "Automation Health": {"score": 70, "weight": "20%"},
    "Org Architecture": {"score": 82, "weight": "15%"},
    "Test Coverage": {"score": 68, "weight": "15%"}
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
    "execution_mode": "Parallel (5 agents)"
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
  Pages:  5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## PDF Contents

| Page | Content |
|------|---------|
| 1 | Cover — org name, score gauge, grade, executive summary |
| 2 | Domain Scores — horizontal bar chart + score table with weights |
| 3 | Key Findings — severity-coded findings table |
| 4 | Action Plan — Critical / Important / Strategic with timeline guidance |
| 5 | Methodology — scoring weights, grade scale, audit metadata |

---

## Data Quality Rules

- Use only real data extracted from audit reports — never fabricate scores
- Findings must be specific (include object names, counts, percentages from the audit)
- Executive summary: 2–4 sentences maximum, non-technical language
- Scores must be integers (0–100)
- If a domain report is missing, mark that domain as "N/A" in the JSON

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `reportlab` not found | Run `pip3 install reportlab` |
| Script not found | Ensure `scripts/generate_sf_pdf_report.py` exists — re-run `./install.sh` |
| Empty PDF | Validate JSON: `python3 -c "import json; json.load(open('/tmp/sf_report_data.json'))"` |
| No audit data | Run `/sf-audit [org]` first, then `/sf-audit report-pdf [org]` |
