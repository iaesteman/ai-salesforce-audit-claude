# Skill: sf-audit naming

Run a standalone Salesforce naming conventions audit on a live org.

## Activated by
`/sf-audit-naming [org-alias]`

## What This Skill Does

Audits naming conventions across the org's metadata — Apex classes, triggers, custom objects, custom fields, and flows. Identifies inconsistent, generic, or non-standard names that create technical debt and slow onboarding.

Output file: `SF-NAMING.md` (written to current directory)

---

## Phase 1: Connectivity Check

```bash
sf org display --target-org [org-alias] --json
```

If this fails, instruct the user: `sf org login web --alias [alias]`

Extract: Org Name, Username, Org ID, Edition, Instance URL.

---

## Phase 2: Run Naming Convention Queries

```bash
# --- APEX CLASSES ---
# All active Apex classes (name + type info)
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT Id, Name, ApiVersion, LastModifiedDate FROM ApexClass WHERE Status = 'Active' ORDER BY Name LIMIT 500" \
  --json

# Total active Apex class count
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT COUNT() FROM ApexClass WHERE Status = 'Active'" \
  --json

# --- APEX TRIGGERS ---
# All active triggers
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT Id, Name, TableEnumOrId, ApiVersion FROM ApexTrigger WHERE Status = 'Active' ORDER BY TableEnumOrId, Name" \
  --json

# Objects with multiple triggers (trigger sprawl)
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT TableEnumOrId, COUNT(Id) triggerCount FROM ApexTrigger WHERE Status = 'Active' GROUP BY TableEnumOrId HAVING COUNT(Id) > 1 ORDER BY COUNT(Id) DESC" \
  --json

# --- CUSTOM OBJECTS ---
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT QualifiedApiName, Label FROM EntityDefinition WHERE IsCustomizable = true AND IsCustomSetting = false AND QualifiedApiName LIKE '%__c' ORDER BY QualifiedApiName LIMIT 300" \
  --json

# --- CUSTOM FIELDS (sample across top objects) ---
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT QualifiedApiName, EntityDefinition.QualifiedApiName, Label FROM FieldDefinition WHERE EntityDefinition.IsCustomizable = true AND QualifiedApiName LIKE '%__c' ORDER BY QualifiedApiName LIMIT 500" \
  --json

# --- FLOWS ---
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT ApiName, Label, ProcessType, TriggerType FROM FlowDefinition WHERE ActiveVersion.VersionNumber != null ORDER BY ApiName LIMIT 200" \
  --json

# --- CUSTOM METADATA TYPES ---
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT QualifiedApiName, Label FROM EntityDefinition WHERE QualifiedApiName LIKE '%__mdt' ORDER BY QualifiedApiName LIMIT 100" \
  --json
```

---

## Phase 3: Analyze & Score

### Apex Class Naming Analysis

Classify each class name and flag violations:

**Conventions to enforce:**
- Test classes must end in `_TEST` (e.g., `AccountService_Test`)
- Controller classes must end in `_CTRL` (e.g., `Account_CTRL`)
- Service classes should end in `_SERVICE` (e.g., `Account_SERVICE`)
- Handler classes should end in `_HANDLER` (e.g., `AccountTrigger_HANDLER`)
- Batch classes should end in `_BATCH` (e.g., `CleanupContacts_BATCH`)
- Scheduled classes should end in `_SCHEDULER` or `_SCHEDULE`
- No single-word, vague names: `Utility`, `Manager`, `Helper`, `Utils`, `Common`, `Misc`
- No names with spaces or special characters
- Names should be PascalCase

**Violation rate** = classes violating conventions / total × 100

Score:
| Violation Rate | Score |
|----------------|-------|
| < 5%           |  10   |
| 5–14%          |   8   |
| 15–29%         |   6   |
| 30–49%         |   4   |
| 50–74%         |   2   |
| ≥ 75%.         |   0   |

### Apex Trigger Naming Analysis

**Conventions to enforce:**
- Trigger name should follow `[ObjectName]Trigger` pattern (e.g., `AccountTrigger`, `ContactTrigger`)
- One trigger per object — multiple triggers on the same object is a violation

**Trigger naming violation rate** = triggers not matching `[Object]Trigger` pattern / total × 100

**Multiple trigger penalty:** each object with >1 trigger counts as a full violation block

Score: same table as above

### Custom Object Naming Analysis

**Conventions to enforce:**
- API name should be PascalCase (e.g., `CustomerOrder__c`, not `customer_order__c` or `Customer_Order__c`)
- No single-letter or ambiguous abbreviations (e.g., `CO__c`, `Obj1__c`)
- No generic names (`Test__c`, `Temp__c`, `New__c`, `Old__c`)
- Label and API name should align meaningfully

**Object violation rate** = non-conforming objects / total custom objects × 100

Score: same table as above

### Custom Field Naming Analysis

**Conventions to enforce:**
- API name should be PascalCase with underscores (e.g., `BillingAddress__c`, not `billing_address__c` or `Billing_Address__c`)
- No single-letter or numeric-only names (`F1__c`, `Field1__c`, `X__c`)
- No generic names (`Test__c`, `Temp__c`, `Flag__c`, `Misc__c`)
- Checkbox fields should reflect boolean meaning (e.g., `IsActive__c`, `HasContract__c`, not `Is_Active__c` or `Has_Contract__c`)

**Field violation rate** = non-conforming fields / total custom fields sampled × 100

Score: same table as above

### Flow Naming Analysis

**Conventions to enforce:**
- Flow API names should be descriptive and structured
- Recommended pattern: `[Object]_[Action]_[Trigger]` (e.g., `Account_SendWelcomeEmail_AfterInsert`)
- No single-word names (`Flow1`, `Test`, `New_Flow`)
- No spaces in API names (enforced by Salesforce, but label may have generic names)
- Flow label should clearly describe what the flow does

**Flow violation rate** = non-descriptive flow names / total active flows × 100

Score: same table as above

### Composite Score

**Scoring dimensions (0–10 each):**

| Dimension            | Weight |
|----------------------|--------|
| Apex class naming    |   25%  |
| Apex trigger naming  |   20%  |
| Custom object naming |   20%  |
| Custom field naming  |   20%  |
| Flow naming          |   15%  |

```
section_score = (
  apex_class_score × 0.25 +
  trigger_score    × 0.20 +
  object_score     × 0.20 +
  field_score      × 0.20 +
  flow_score       × 0.15
) × 10
```

**Grade:**
| Score  | Grade |
|--------|-------|
| 90–100 |   A+  |
| 80–89  |   A   |
| 70–79  |   B   |
| 60–69  |   C   |
| 50–59  |   D   |
| < 50   |   F   |

---

## Phase 4: Write SF-NAMING.md

```markdown
# Salesforce Naming Conventions Report
**Org:** [name] | **Username:** [username] | **Edition:** [edition]
**Date:** [YYYY-MM-DD HH:MM UTC]
**Generated by:** /sf-audit-naming

---

## Score: [XX]/100 — Grade [X]

### Dimension Scores
| Dimension            |  Score | Key Finding                                        |
|----------------------|--------|----------------------------------------------------|
| Apex Class Naming    | [X]/10 | [n] violations out of [n] classes ([x]%)           |
| Apex Trigger Naming  | [X]/10 | [n] triggers not following [Object]Trigger pattern |
| Custom Object Naming | [X]/10 | [n] objects with naming issues                     |
| Custom Field Naming  | [X]/10 | [n] fields with generic or non-standard names      |
| Flow Naming          | [X]/10 | [n] flows with non-descriptive names               |

---

### Apex Class Naming Analysis
**Total active classes:** [n] | **Violations:** [n] ([x]%)

| Violation Type                                                 | Count | Examples           |
|----------------------------------------------------------------|-------|--------------------|
| Missing type suffix (no Controller/Service/Handler/Test/Batch) |  [n]  | [Class1], [Class2] |
| Generic/vague names                                            |  [n]  | [Class1], [Class2] |
| Non-PascalCase                                                 |  [n]  | [Class1], [Class2] |

**Well-named examples:** [ClassName1], [ClassName2]

---

### Apex Trigger Naming Analysis
**Total active triggers:** [n] | **Objects with multiple triggers:** [n]

| Object   | Trigger Name  | Follows Convention? | Issue                              |
|----------|---------------|---------------------|------------------------------------|
| [Object] | [TriggerName] |        Yes/No       | [e.g., "Should be AccountTrigger"] |

[If all follow convention: "All triggers follow the [ObjectName]Trigger pattern."]

---

### Custom Object Naming Analysis
**Total custom objects:** [n] | **Violations:** [n] ([x]%)

| Object API Name | Label   | Issue                                           |
|-----------------|---------|-------------------------------------------------|
| [Object__c]     | [Label] | [e.g., "Abbreviation detected", "Generic name"] |

[Or: "All custom objects follow PascalCase naming conventions."]

---

### Custom Field Naming Analysis
**Fields sampled:** [n] | **Violations:** [n] ([x]%)

| Field API Name |   Object    | Issue                                                        |
|----------------|-------------|--------------------------------------------------------------|
| [Field__c]     | [Object__c] | [e.g., "Generic name", "Single character", "Numeric suffix"] |

---

### Flow Naming Analysis
**Total active flows:** [n] | **Violations:** [n] ([x]%)

| Flow API Name | Process Type       | Issue                                                    |
|---------------|--------------------|----------------------------------------------------------|
| [FlowApiName] | [AutoLaunchedFlow] | [e.g., "Non-descriptive name", "Missing object context"] |

[Or: "All active flows have descriptive, structured names."]

---

### Recommendations

**Critical:**
[Only if score < 5 on any dimension]
- [n] Apex classes have no type suffix — add `_CTRL`, `_SRV`, `_HNDLR`, `_BATCH`, or `_TEST` suffix to clarify purpose.
- [n] triggers do not follow the `[ObjectName]Trigger` pattern — rename for consistency.

**Important:**
- [n] custom fields use generic names (`Test`, `Temp`, `Flag`) — rename to reflect business meaning.
- [n] flows have single-word or non-descriptive names — adopt a naming pattern like `[Object]_[Action]_[Trigger]`.

**Best Practices:**
- Enforce naming conventions via a team coding standards document or PR review checklist.
- Use a linter (e.g., PMD with Apex rules) in your CI pipeline to flag new naming violations automatically.
- Consider a naming convention cleanup sprint for legacy metadata.

---
*Run `/sf-audit` for a full org health audit across all domains.*
```

---

## Phase 5: Terminal Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SF NAMING CONVENTIONS AUDIT — [Org Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Score:          [XX]/100 (Grade [X])
  Apex classes:   [n] total, [n] violations ([x]%)
  Triggers:       [n] total, [n] non-standard
  Custom objects: [n] total, [n] violations
  Custom fields:  [n] sampled, [n] violations
  Flows:          [n] total, [n] non-descriptive
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Report saved: SF-NAMING.md
  Run /sf-audit [org] for full audit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Output Standards
- If a query returns 0 records, note it and score that dimension at 10 (no violations possible)
- Show specific examples of violations — never just counts
- Never fabricate class names, object names, or field names
- Exclude managed package metadata from violation counts (any name with a namespace prefix like `ns__`)
- Limit violation examples to top 10 per category to keep the report readable
