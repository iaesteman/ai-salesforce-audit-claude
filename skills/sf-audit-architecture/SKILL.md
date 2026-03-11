# Skill: sf-audit architecture

Run a standalone Salesforce org architecture audit on a live org.

## Activated by
`/sf-audit-architecture [org-alias]`

## What This Skill Does

Audits the org's technical architecture — custom object and field sprawl, governor limit consumption, Apex API version debt, installed packages, and configuration pattern health (Custom Settings vs. Custom Metadata Types).

Output file: `SF-ARCHITECTURE.md` (written to current directory)

---

## Phase 1: Connectivity Check

```bash
sf org display --target-org [org-alias] --json
```

If this fails, instruct the user: `sf org login web --alias [alias]`

Extract: Org Name, Username, Org ID, Edition, Instance URL.

---

## Phase 2: Run Architecture Queries

```bash
# --- ORG LIMITS (REST API) ---
sf api request rest "/services/data/v62.0/limits/" --target-org [org-alias] 2>/dev/null \
  || sf api request rest "/services/data/v59.0/limits/" --target-org [org-alias] 2>/dev/null \
  || echo '{"_error": "REST limits unavailable"}'

# Org display for edition and basic info
sf org display --target-org [org-alias] --verbose --json

# --- CUSTOM OBJECTS ---
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT QualifiedApiName, Label, InternalSharingModel, ExternalSharingModel FROM EntityDefinition WHERE IsCustomizable = true AND IsCustomSetting = false ORDER BY QualifiedApiName LIMIT 200" \
  --json

# --- FIELD COUNTS PER OBJECT ---
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT EntityDefinitionId, EntityDefinition.QualifiedApiName, COUNT(Id) fieldCount FROM FieldDefinition WHERE EntityDefinition.IsCustomizable = true GROUP BY EntityDefinitionId, EntityDefinition.QualifiedApiName ORDER BY COUNT(Id) DESC LIMIT 25" \
  --json

# --- APEX CLASSES ---
# API version distribution
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT ApiVersion, COUNT(Id) classCount FROM ApexClass WHERE Status = 'Active' GROUP BY ApiVersion ORDER BY ApiVersion ASC" \
  --json

# Largest classes
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT Id, Name, ApiVersion, LengthWithoutComments, LastModifiedDate FROM ApexClass WHERE Status = 'Active' ORDER BY LengthWithoutComments DESC LIMIT 20" \
  --json

# Total active Apex classes
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT COUNT() FROM ApexClass WHERE Status = 'Active'" \
  --json

# Classes not modified in 2+ years (potential dead code)
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT Id, Name, ApiVersion, LengthWithoutComments, LastModifiedDate FROM ApexClass WHERE Status = 'Active' AND LastModifiedDate < LAST_N_DAYS:730 ORDER BY LastModifiedDate ASC LIMIT 30" \
  --json

# --- PACKAGES ---
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT NamespacePrefix, MajorVersion, MinorVersion, PatchVersion, Status, AllowedLicenses, UsedLicenses FROM PackageLicense ORDER BY NamespacePrefix" \
  --json

# --- CONFIGURATION PATTERNS ---
# Custom settings (legacy)
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT QualifiedApiName, Label FROM EntityDefinition WHERE IsCustomSetting = true ORDER BY QualifiedApiName" \
  --json

# Custom Metadata Types (modern)
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT QualifiedApiName, Label FROM EntityDefinition WHERE QualifiedApiName LIKE '%__mdt' ORDER BY QualifiedApiName" \
  --json

# Large static resources
sf data query --target-org [org-alias] \
  --query "SELECT Id, Name, ContentType, BodyLength, LastModifiedDate FROM StaticResource ORDER BY BodyLength DESC LIMIT 20" \
  --json
```

---

## Phase 3: Analyze & Score

**Parse org limits from REST response.**
Key limits to extract: `DailyApiRequests`, `DataStorageMB`, `FileStorageMB`, `ActiveFlowVersions`, `DailyBulkApiRequests`.

```
usage_pct = Current / Max × 100
```
Status: <50% = OK | 50-79% = WARN | 80-94% = HIGH | ≥95% = CRITICAL

**API version scoring:**
| API Version | Status |
|------------|--------|
| v60+ | Current |
| v55-59 | Recent — OK |
| v50-54 | Aging — WARN |
| v40-49 | Legacy — HIGH |
| v30-39 | Very Legacy — CRITICAL |
| <v30 | Ancient — CRITICAL |

Score: All v55+=10 | majority v50+, none <v40=8 | some v40-49=5 | any v30-39=3 | any <v30=1

**Object/field sprawl:**
Compare custom object count against edition limits:
- Enterprise: ~800 custom objects
- Unlimited: ~2000 custom objects
Score by usage %: <25%=10 | 25-49%=8 | 50-74%=6 | 75-89%=4 | ≥90%=1

**Scoring (0–10 per dimension):**

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| Object/field sprawl | 25% | See usage % table |
| Governor limits | 25% | All <50%=10; any 50-79%=7; any 80-94%=4; any ≥95%=1 |
| Apex API version | 20% | See version table |
| Package health | 15% | No unused licenses, all active=10; minor issues=7; unused/overlicensed=4 |
| Custom settings vs CMDT | 15% | 0 custom settings, using CMDT=10; few=7; heavy custom settings=3 |

```
section_score = (sprawl×0.25 + limits×0.25 + api×0.20 + packages×0.15 + config×0.15) × 10
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

## Phase 4: Write SF-ARCHITECTURE.md

```markdown
# Salesforce Org Architecture Report
**Org:** [name] | **Username:** [username] | **Edition:** [edition]
**Date:** [YYYY-MM-DD HH:MM UTC]
**Generated by:** /sf-audit architecture

---

## Score: [XX]/100 — Grade [X]

### Dimension Scores
| Dimension | Score | Key Finding |
|:---------:|:-----:|:-----------:|
| Object / Field Sprawl | [X]/10 | [n] custom objects ([x]% of limit) |
| Governor Limits | [X]/10 | Highest: [limit] at [x]% |
| Apex API Version Debt | [X]/10 | [n] classes on v<50 |
| Package Health | [X]/10 | [n] packages; [n] with unused licenses |
| Custom Settings vs. CMDT | [X]/10 | [n] custom settings; [n] metadata types |

### Org Limits Dashboard
| Limit | Used | Maximum | % Used | Status |
|-------|------|---------|--------|--------|
| Daily API Calls | [n] | [n] | [x]% | OK/WARN/HIGH/CRITICAL |
| Data Storage | [n] MB | [n] MB | [x]% | OK/WARN/HIGH/CRITICAL |
| File Storage | [n] MB | [n] MB | [x]% | OK/WARN/HIGH/CRITICAL |
| Active Flows | [n] | [n] | [x]% | OK/WARN/HIGH/CRITICAL |
[All available limits...]

### Custom Object Analysis
**Total custom objects:** [n] ([x]% of [edition] limit of ~[max])
**Total active Apex classes:** [n]

**Most field-heavy objects:**
| Object | Field Count | Notes |
|--------|------------|-------|
| [Object] | [n] | [flag if >100 custom fields] |

### Apex API Version Distribution
| API Version | Count | Release Era | Status |
|------------|-------|-------------|--------|
| v60+ | [n] | 2024+ | Current |
| v55–59 | [n] | 2022–2023 | OK |
| v50–54 | [n] | 2020–2021 | WARN |
| v40–49 | [n] | 2018–2019 | HIGH |
| v30–39 | [n] | 2015–2017 | CRITICAL |
| <v30 | [n] | Pre-2015 | CRITICAL |

**Classes not modified in 2+ years (potential dead code):**
| Class | API Version | Last Modified | Lines |
|-------|------------|---------------|-------|
| [Name] | v[n] | [date] | [n] |

### Installed Packages
| Namespace | Version | Status | Licenses Used/Total |
|-----------|---------|--------|---------------------|
| [namespace] | [v] | Active | [n]/[n] |
[Or: "No managed packages installed."]

### Configuration Patterns
| Pattern | Count | Recommendation |
|---------|-------|----------------|
| Custom Settings | [n] | Migrate to Custom Metadata Types |
| Custom Metadata Types | [n] | Current — continue using |
| Large Static Resources (>1MB) | [n] | Review for CDN or compression |

### Recommendations
[Critical / Important / Best Practices with specific names and counts]

---
*Run `/sf-audit` for a full org health audit across all domains.*
```

---

## Phase 5: Terminal Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SF ARCHITECTURE AUDIT — [Org Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Score:            [XX]/100 (Grade [X])
  Custom objects:   [n] ([x]% of limit)
  Apex classes:     [n] ([n] on legacy API)
  Highest limit:    [name] at [x]%
  Packages:         [n] installed
  Custom settings:  [n] (legacy pattern)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Report saved: SF-ARCHITECTURE.md
  Run /sf-audit [org] for full audit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Output Standards
- If REST limits endpoint fails, skip that section and note it — do not block the rest
- Exclude managed package objects from custom object count (objects with namespace prefix)
- If 0 Apex classes, score API version at 10 (no debt) and note it
- Never fabricate limits or counts
