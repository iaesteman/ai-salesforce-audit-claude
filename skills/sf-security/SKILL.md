# Skill: sf-audit security

Run a standalone Salesforce security & access audit on a live org.

## Activated by
`/sf-audit security [org-alias]`

## What This Skill Does

Audits user profiles, permission sets, object-wide defaults (OWD), MFA enforcement, IP restrictions, login activity, and field-level security. This is the highest-risk domain in any Salesforce org — misconfigurations create active data exposure.

Output file: `SF-SECURITY.md` (written to current directory)

---

## Phase 1: Connectivity Check

```bash
sf org display --target-org [org-alias] --json
```

If this fails, instruct the user: `sf org login web --alias [alias]`

Extract: Org Name, Username, Org ID, Edition, Instance URL.

---

## Phase 2: Run Security Queries

```bash
# Profiles and their permissions
sf data query --target-org [org-alias] \
  --query "SELECT Id, Name, UserType, PermissionsModifyAllData, PermissionsViewAllData, PermissionsManageUsers, PermissionsCustomizeApplication FROM Profile ORDER BY Name" \
  --json

# Active users per profile
sf data query --target-org [org-alias] \
  --query "SELECT Profile.Name, COUNT(Id) userCount FROM User WHERE IsActive = true GROUP BY Profile.Name ORDER BY COUNT(Id) DESC" \
  --json

# Permission sets with dangerous permissions
sf data query --target-org [org-alias] \
  --query "SELECT Id, Name, Label, PermissionsModifyAllData, PermissionsViewAllData, PermissionsManageUsers, PermissionsAuthorApex FROM PermissionSet WHERE IsOwnedByProfile = false" \
  --json

# Users with more than 5 permission sets
sf data query --target-org [org-alias] \
  --query "SELECT AssigneeId, Assignee.Name, Assignee.Username, COUNT(Id) permSetCount FROM PermissionSetAssignment WHERE PermissionSet.IsOwnedByProfile = false GROUP BY AssigneeId, Assignee.Name, Assignee.Username HAVING COUNT(Id) > 5 ORDER BY COUNT(Id) DESC" \
  --json

# Object sharing model (OWD) via Tooling API
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT QualifiedApiName, Label, InternalSharingModel, ExternalSharingModel FROM EntityDefinition WHERE IsCustomizable = true AND IsCustomSetting = false ORDER BY QualifiedApiName" \
  --json

# Stale active users (no login in 90+ days)
sf data query --target-org [org-alias] \
  --query "SELECT Id, Name, Username, LastLoginDate, Profile.Name FROM User WHERE IsActive = true AND UserType = 'Standard' AND (LastLoginDate < LAST_N_DAYS:90 OR LastLoginDate = null) ORDER BY LastLoginDate ASC NULLS FIRST" \
  --json

# Active guest users
sf data query --target-org [org-alias] \
  --query "SELECT Id, Name, Username, IsActive, Profile.Name FROM User WHERE Profile.UserType = 'Guest' AND IsActive = true" \
  --json

# Failed login attempts — last 30 days
sf data query --target-org [org-alias] \
  --query "SELECT UserId, User.Name, LoginTime, LoginType, SourceIp, Status FROM LoginHistory WHERE LoginTime = LAST_N_DAYS:30 AND Status != 'Success' ORDER BY LoginTime DESC LIMIT 200" \
  --json

# Login types summary (last 30 days)
sf data query --target-org [org-alias] \
  --query "SELECT LoginType, COUNT(Id) loginCount FROM LoginHistory WHERE LoginTime = LAST_N_DAYS:30 GROUP BY LoginType ORDER BY COUNT(Id) DESC" \
  --json

# IP restrictions per profile
sf data query --target-org [org-alias] \
  --query "SELECT ProfileId, Profile.Name, StartAddress, EndAddress FROM LoginIpRange ORDER BY Profile.Name" \
  --json

# Org security level
sf data query --target-org [org-alias] --use-tooling-api \
  --query "SELECT Id, Name FROM Organization" \
  --json
```

---

## Phase 3: Analyze & Score

**Profile hygiene:**
- Count profiles with `PermissionsModifyAllData = true`
- Expected: only "System Administrator"
- Flag any non-SysAdmin profile with this permission

**Permission set analysis:**
- Flag perm sets with `PermissionsModifyAllData = true` or `PermissionsManageUsers = true`
- Flag users with > 5 perm sets

**Sharing model:**
Flag these `InternalSharingModel` values on sensitive objects (Account, Contact, Opportunity, Case, Lead):
- `ReadWrite` → HIGH RISK
- `Read` → MEDIUM RISK
- `Private` / `ControlledByParent` → Acceptable

**MFA scoring:**
MFA enforcement cannot always be verified via SOQL. If you cannot determine status, assign 5/10 with a note: "MFA enforcement requires manual check in Setup > Identity Verification."

**Scoring (0–10 per dimension):**

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| Profile hygiene | 20% | Only SysAdmin has ModifyAll=10; 1 extra profile=7; 2-3=4; 4+=1 |
| Permission set sprawl | 20% | No users >5 perm sets, no dangerous perm sets=10; minor=7; 1-2 dangerous=4; widespread=1 |
| Sharing model | 20% | All sensitive objects Private=10; 1-2 ReadOnly=7; any ReadWrite on sensitive=3 |
| MFA enforcement | 15% | Enforced org-wide=10; partial=6; not enforced=2; unknown=5 |
| IP/Session restrictions | 15% | IP ranges on admin profiles + low failed logins=10; partial=6; none=3 |
| Field-Level Security | 10% | No obvious gaps=10; some gaps=6; widespread access to sensitive fields=2 |

```
section_score = (profile×0.20 + permset×0.20 + sharing×0.20 + mfa×0.15 + ip×0.15 + fls×0.10) × 10
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

## Phase 4: Write SF-SECURITY.md

```markdown
# Salesforce Security & Access Report
**Org:** [name] | **Username:** [username] | **Edition:** [edition]
**Date:** [YYYY-MM-DD HH:MM UTC]
**Generated by:** /sf-audit security

---

## Score: [XX]/100 — Grade [X]

### Dimension Scores
| Dimension | Score | Key Finding |
|-----------|-------|-------------|
| Profile Hygiene | [X]/10 | [n] profiles with elevated permissions |
| Permission Set Sprawl | [X]/10 | [n] users with >5 perm sets |
| Sharing Model | [X]/10 | [n] objects with Public Read/Write |
| MFA Enforcement | [X]/10 | [finding] |
| IP / Session Restrictions | [X]/10 | [n] admin profiles with IP restrictions |
| Field-Level Security | [X]/10 | [finding] |

### Profile Analysis
| Profile | Users | ModifyAll | ViewAll | ManageUsers | Risk |
|---------|-------|-----------|---------|-------------|------|
| System Administrator | [n] | ✓ | ✓ | ✓ | Expected |
| [Other elevated profiles...] | [n] | ✓/✗ | ✓/✗ | ✓/✗ | HIGH/MED/LOW |

**Total active profiles in use:** [n]
**Profiles with ModifyAllData:** [n] (expected: 1)

### Permission Set Risks
| Permission Set | ModifyAll | ManageUsers | Assigned Users |
|----------------|-----------|-------------|----------------|
| [Name] | ✓/✗ | ✓/✗ | [n] |

**Users with >5 permission sets:**
| User | Username | Count |
|------|----------|-------|
| [name] | [username] | [n] |

### Sharing Model (Object-Wide Defaults)
**High Risk (Public Read/Write):**
[List objects — especially Account, Contact, Opportunity, Case]

**Medium Risk (Public Read Only):**
[List sensitive objects]

**Well-configured:**
[Count of Private / ControlledByParent objects]

### User Access Health
| Issue | Count | Action |
|-------|-------|--------|
| Active users — no login in 90+ days | [n] | Deactivate |
| Active users — never logged in | [n] | Deactivate if unused |
| Active guest users | [n] | Review |

### Login Activity (Last 30 Days)
**Failed logins:** [n]
[If > 50: "WARNING: High failed login volume — possible brute force activity."]

| Login Type | Count |
|------------|-------|
| [type] | [n] |

### IP Restrictions
[n] admin profiles have IP range restrictions.
[If 0: "No IP restrictions configured — admin accounts accessible from any network."]

### Recommendations
[Critical / Important / Best Practices with specific profile/permission set names]

---
*Run `/sf-audit` for a full org health audit across all domains.*
```

---

## Phase 5: Terminal Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SF SECURITY AUDIT — [Org Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Score:           [XX]/100 (Grade [X])
  Admin profiles:  [n] with ModifyAll
  Perm set risk:   [n] dangerous perm sets
  Sharing risk:    [n] objects Public R/W
  Stale users:     [n] active, no login 90d
  Failed logins:   [n] in last 30 days
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Report saved: SF-SECURITY.md
  Run /sf-audit [org] for full audit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Output Standards
- Never fabricate data — all numbers from live query results
- If `LoginIpRange` query fails, note it and skip gracefully
- For MFA, note "Manual verification required" if SOQL cannot confirm it
- Prioritize findings by blast radius: data exposure first, then access control, then policies
