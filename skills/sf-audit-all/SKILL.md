# SF Audit All — Batch Org Health Audit

Audits all authenticated Salesforce orgs and produces a comparison summary showing health scores and grades across every org.

## Activated by
`/sf-audit-all`

---

## What This Skill Does

1. Discovers all authenticated Salesforce orgs via `sf org list`
2. Runs `/sf-audit [alias]` sequentially for each org
3. Collects the composite Org Health Score and grade from each audit
4. Prints a side-by-side comparison table at the end

---

## Phase 1: Discover Authenticated Orgs

```bash
sf org list --json
```

Parse the JSON output to build a list of org aliases and usernames. Include both scratch orgs and non-scratch orgs. Skip orgs with `connectedStatus: "RefreshTokenAuthError"` (expired tokens) and note them as skipped.

If no orgs are found, print:
```
No authenticated orgs found. Run:
  sf org login web --alias my-org
```
and stop.

Print to terminal:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SF AUDIT ALL — BATCH ORG AUDIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Found [N] authenticated org(s). Auditing each in sequence.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 2: Audit Each Org Sequentially

For each org alias in the list:

1. Print:
   ```
   ──────────────────────────────────────────
   Auditing: [alias] ([username])
   ──────────────────────────────────────────
   ```

2. Run `/sf-audit [alias]`

3. After completion, extract from the generated `SF-AUDIT.md`:
   - `ORG_NAME`
   - `OVERALL_SCORE` (the numeric score 0–100)
   - `GRADE` (A+, A, B, C, D, or F)
   - Top 1–2 critical findings from the Priority Action Matrix

4. Store these results for the final summary.

**Important:** Run orgs sequentially (not in parallel) to avoid SOQL governor limit conflicts across multiple orgs running simultaneously.

---

## Phase 3: Print Comparison Summary

After all orgs are audited, print a comparison table to the terminal:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SF AUDIT ALL — RESULTS SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌─────────────────────────┬──────────┬───────┬───────┬────────────────────────────────┐
  │ Org                     │ Username │ Score │ Grade │ Top Priority                   │
  ├─────────────────────────┼──────────┼───────┼───────┼────────────────────────────────┤
  │ [alias]                 │ [user]   │ [XX]  │  [X]  │ [top critical finding]         │
  │ [alias]                 │ [user]   │ [XX]  │  [X]  │ [top critical finding]         │
  │ [alias] (skipped)       │ [user]   │  —    │   —   │ Auth token expired             │
  └─────────────────────────┴──────────┴───────┴───────┴────────────────────────────────┘

  Best:  [alias] — Score [XX] (Grade [X])
  Worst: [alias] — Score [XX] (Grade [X])

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Individual reports saved as SF-AUDIT-[YYYY-MM-DD].md in each org's
  working directory. Run /sf-audit-report-pdf [alias] for a PDF.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Output Standards

- Orgs are audited sequentially to avoid API conflicts
- Skipped orgs (expired auth) are listed in the summary with a note
- The comparison table is printed to terminal only — no additional combined report file is written
- Individual `SF-AUDIT.md` and `SF-AUDIT-[YYYY-MM-DD].md` files are written per org as usual
