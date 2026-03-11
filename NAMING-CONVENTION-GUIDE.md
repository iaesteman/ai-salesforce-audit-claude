# Naming Convention Audit — Setup & Usage Guide

A step-by-step guide for setting up and running `/sf-audit-naming` on a Salesforce org — no prior experience with this tool required.

---

## What This Skill Does

The **Naming Convention** skill audits your Salesforce org's metadata against a defined set of naming standards. It scans:

|    Metadata Type     |                                             What It Checks                                             |
|:--------------------:|:------------------------------------------------------------------------------------------------------:|
|   **Apex Classes**   |      Do class names end with a type suffix? (`_CTRL`, `_SERVICE`, `_HANDLER`, `_BATCH`, `_TEST`)       |
|  **Apex Triggers**   | Does each trigger follow the `[ObjectName]Trigger` pattern? Is there more than one trigger per object? |
|  **Custom Fields**   |        Are field names generic, single-character, or numeric? (`Field1__c`, `X__c`, `Test__c`)         |
|      **Flows**       |               Do flow names describe what they do? Are single-word or vague names used?                |
| **Validation Rules** |            Are rule names descriptive enough to understand the business rule they enforce?             |

At the end of the scan it produces a **score from 0–100** with a letter grade, a **markdown report** (`SF-NAMING.md`), and a list of specific violations with examples.

---

## Prerequisites

Before you can run the skill you need three things installed on your machine.

### 1. Claude Code

Claude Code is the AI assistant that runs the skill. Download and install it from:

```
https://claude.ai/code
```

Verify it is installed by opening a terminal and running:

```bash
claude --version
```

### 2. Salesforce CLI (`sf`)

The Salesforce CLI is what connects Claude Code to your org. Install it from:

```
https://developer.salesforce.com/tools/salesforcecli
```

Verify it is installed:

```bash
sf --version
```

You should see output like `@salesforce/cli/2.x.x ...`.

### 3. The sf-audit Tool

Install the full audit tool suite (this installs the naming skill along with all others):

```bash
curl -fsSL https://raw.githubusercontent.com/iaesteman/ai-salesforce-audit-claude/main/install.sh | bash
```

Or, if you have already cloned the repository:

```bash
cd ai-salesforce-audit-claude
./install.sh
```

After installation you will see a confirmation listing the installed skills and agents. **Start a new Claude Code session** after installing — skills are only available in sessions started after installation.

---

## Step 1 — Authenticate Your Salesforce Org

The skill connects to your org using the Salesforce CLI. You need to authenticate at least once before running a scan.

### Option A — Web Login (recommended)

```bash
sf org login web --alias my-org
```

This opens a browser window. Log in with your Salesforce credentials. The `--alias` flag gives the connection a short name you will use when running the skill (you can choose any name).

### Option B — If your org uses a custom domain (sandbox or production)

```bash
# For a sandbox:
sf org login web --alias my-sandbox --instance-url https://test.salesforce.com

# For a production org with a custom domain:
sf org login web --alias my-prod --instance-url https://mycompany.my.salesforce.com
```

### Verify the connection

```bash
sf org display --target-org my-org
```

You should see your org name, username, and instance URL. If this fails, re-run the login command.

### Who should run the audit?

The authenticated user needs:
- **API Enabled** on their profile
- **View Setup and Configuration** permission
- Ideally: **System Administrator** profile for full audit coverage

Without these, some Tooling API queries may return empty results or errors.

---

## Step 2 — Run the Naming Convention Audit

Open a **Claude Code session** and type:

```
/sf-audit-naming my-org
```

Replace `my-org` with the alias you set during login.

If you want to audit your **default authenticated org** (the last one you logged into), you can omit the alias:

```
/sf-audit-naming
```

### What happens next

Claude Code will:

1. Verify the org connection
2. Run a series of Tooling API and SOQL queries against your org (read-only — nothing is modified)
3. Analyse each metadata type against the naming convention rules
4. Calculate a score for each dimension
5. Write the full report to `SF-NAMING.md` in your current directory
6. Print a summary in the terminal

The scan typically takes **1–3 minutes** depending on org size.

---

## Step 3 — Read the Terminal Summary

When the scan finishes you will see a summary like this:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SF NAMING CONVENTIONS AUDIT — Acme Corp
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Score:          72/100 (Grade B)
  Apex classes:   48 violations / 210 total (23%)
  Triggers:       2 non-standard / 14 total
  Custom fields:  31 violations / 890 sampled
  Flows:          9 non-descriptive / 42 total
  Validation rls: 5 generic / 38 total
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Report saved: SF-NAMING.md
  Run /sf-audit [org] for full audit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Score interpretation:**

| Score  | Grade |                           What it means                            |
|:------:|:-----:|:------------------------------------------------------------------:|
| 90–100 |  A+   |      Naming is consistent and well-structured across the org       |
| 80–89  |   A   |                Minor violations — easy to clean up                 |
| 70–79  |   B   |            Some inconsistencies, worth a cleanup sprint            |
| 60–69  |   C   |       Noticeable naming debt across multiple metadata types        |
| 50–59  |   D   |  Significant violations — onboarding and maintenance are affected  |
|  < 50  |   F   | Naming conventions are largely ignored — urgent remediation needed |

---

## Step 4 — Read the Full Report

Open `SF-NAMING.md` in your current directory. It contains five sections, one per metadata type.

### Apex Class Naming

The skill flags a class if it is missing a type suffix. The expected suffixes are:

|    Suffix    |            Used for            |
|:------------:|:------------------------------:|
|   `_CTRL`    | Visualforce / Aura controllers |
|  `_SERVICE`  | Business logic service classes |
|  `_HANDLER`  |  Apex trigger handler classes  |
|   `_BATCH`   |        Batch Apex jobs         |
|   `_TEST`    |          Test classes          |
| `_SCHEDULER` |      Scheduled Apex jobs       |
| `_SELECTOR`  |  Data access / query classes   |

**Example violation output:**

```
| Missing type suffix (_CTRL/_TEST/_HANDLER etc.) | 48 | AccountUtils, LeadProcessor, OpportunityHelper |
```

This means 48 classes do not end in a recognised type suffix. The class names listed are the worst offenders.

**What to do:** Rename the classes to add the appropriate suffix. In Salesforce, renaming an Apex class requires finding all references first — use your IDE's "Find References" before renaming.

---

### Apex Trigger Naming

The expected pattern is `[ObjectName]Trigger`. For example:

- ✅ `AccountTrigger`
- ✅ `ContactTrigger`
- ❌ `MyTrigger` — not descriptive enough
- ❌ `Trigger_Account` — wrong format

The skill also flags objects that have **more than one active trigger** — this is a known anti-pattern because execution order is not guaranteed.

**What to do:** Rename triggers to follow the `[ObjectName]Trigger` pattern. If multiple triggers exist for the same object, consolidate them into a single trigger with a handler class.

---

### Custom Field Naming

The skill flags custom fields that are:

- Single characters: `A__c`, `X__c`
- Numeric descriptors: `Field1__c`, `Col3__c`
- Generic standalone words: `Test__c`, `Temp__c`, `Flag__c`, `Data__c`, `Misc__c`

**Example violation output:**

```
| Field1__c | Account | Numeric suffix — not descriptive |
| X__c      | Contact | Single character — meaning unclear |
| Test__c   | Lead    | Generic name — likely leftover from development |
```

**What to do:** Rename fields to describe their business purpose. Note that renaming a custom field in Salesforce changes its API name, which can break integrations, SOQL queries, reports, and flows that reference the old name. Review all usages before renaming.

---

### Flow Naming

The skill flags flows that have:

- Single-word names: `Flow1`, `Test`, `NewFlow`
- No underscores in the API name (usually auto-generated)
- Generic labels: `Flow`, `New Flow`, `Untitled`, `My Flow`

The recommended naming pattern is:

```
[Object]_[Action]_[Trigger]

Examples:
  Account_SendWelcomeEmail_AfterInsert
  Lead_AssignOwner_BeforeUpdate
  Opportunity_NotifyManager_AfterClose
```

**What to do:** Rename flows in Setup > Flows. Both the API Name and the Label should be updated. The API Name cannot contain spaces — use underscores.

---

### Validation Rule Naming

The skill flags validation rules that:

- Are fewer than 3 words/segments: `Rule1`, `VR_1`, `Validation`
- Use generic words with no business context: `Check`, `Validate`, `Error`

**Example violation output:**

```
| Rule1    | Account | Too short — gives no context |
| Validate | Contact | Generic — what is being validated? |
```

A good validation rule name describes the object and the rule:

- ✅ `Account_BillingCity_Required_For_Enterprise`
- ✅ `Contact_Email_Required_When_Lead_Source_Web`
- ❌ `Rule1`
- ❌ `Check`

**What to do:** Rename validation rules in Setup > Object Manager > [Object] > Validation Rules. Renaming does not affect functionality — the rule continues to work normally.

---

## Step 5 — Prioritise Your Fixes

Not all violations need to be fixed at the same priority. Use this guide:

### Fix immediately (before next deployment)

- Any class or trigger name that another team member would not be able to identify without reading the code
- Any flow named `Flow`, `Untitled`, or `New Flow`
- Any validation rule named `Rule1`, `Check`, or `Validate`

### Fix in the next sprint

- Classes missing their type suffix (start with the highest-traffic classes)
- Objects with multiple active triggers — consolidate into a handler pattern
- Fields with generic names like `Test__c` or `Temp__c` — these are usually leftover from development

### Fix as part of a cleanup sprint

- Fields with numeric suffixes (`Field1__c`) — these need a careful reference check before renaming
- Flows with missing underscores — rename and update any references in other flows or pages

---

## Common Questions

**Q: The scan shows violations in managed package classes. Do I need to fix those?**

No. The skill automatically excludes managed package metadata (any name containing a namespace prefix like `ns__`). If you see them in the results, they were not correctly excluded — please report it as a bug.

**Q: Can I configure which naming conventions are enforced?**

Yes. The naming rules are defined in the skill file at:

```
~/.claude/skills/sf-audit-naming/SKILL.md
```

Open this file, find the violation classification rules, and adjust them to match your team's standards. Changes take effect immediately in the next Claude Code session.

**Q: The scan failed with an authentication error. What do I do?**

Run:

```bash
sf org login web --alias my-org
```

Then retry `/sf-audit-naming my-org`. Authentication tokens expire periodically.

**Q: Can I run this in a sandbox?**

Yes. Authenticate your sandbox:

```bash
sf org login web --alias my-sandbox --instance-url https://test.salesforce.com
```

Then run:

```
/sf-audit-naming my-sandbox
```

**Q: How do I run the full audit (all domains) instead of just naming?**

```
/sf-audit my-org
```

This runs all 9 audit agents in parallel and produces a comprehensive `SF-AUDIT.md` and `SF-AUDIT-REPORT.pdf`.

---

## Quick Reference

|              Task              |                                     Command                                      |
|:------------------------------:|:--------------------------------------------------------------------------------:|
|   Log in to a production org   |                        `sf org login web --alias my-prod`                        |
|      Log in to a sandbox       | `sf org login web --alias my-sandbox --instance-url https://test.salesforce.com` |
|     Verify org connection      |                       `sf org display --target-org my-org`                       |
|    List authenticated orgs     |                                  `sf org list`                                   |
|  Run naming convention audit   |                            `/sf-audit-naming my-org`                             |
| Run full audit (all 9 domains) |                                `/sf-audit my-org`                                |
|      Generate PDF report       |                          `/sf-audit-report-pdf my-org`                           |
|       Uninstall the tool       |                    `./uninstall.sh` (from the repo directory)                    |

---

## Need Help?

- **Tool issues or bugs:** Open an issue at [github.com/iaesteman/ai-salesforce-audit-claude](https://github.com/iaesteman/ai-salesforce-audit-claude)
- **Salesforce CLI docs:** [developer.salesforce.com/tools/salesforcecli](https://developer.salesforce.com/tools/salesforcecli)
- **Claude Code docs:** [claude.ai/code](https://claude.ai/code)
