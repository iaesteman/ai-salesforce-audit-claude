#!/usr/bin/env bash
# install.sh — Salesforce Org Audit Tool for Claude Code
# Installs /sf-audit skill and 5 parallel audit agents

set -e

# ─── Colors ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Paths ────────────────────────────────────────────────────────────────────
SKILLS_DIR="$HOME/.claude/skills"
AGENTS_DIR="$HOME/.claude/agents"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ─── Banner ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}${BOLD}  Salesforce Org Audit — Claude Code Installer       ${NC}"
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ─── Prerequisite: Claude Code ────────────────────────────────────────────────
if ! command -v claude &>/dev/null; then
  echo -e "${RED}ERROR: Claude Code CLI not found in PATH.${NC}"
  echo "Install from: https://claude.ai/code"
  exit 1
fi

# ─── Prerequisite: Salesforce CLI ─────────────────────────────────────────────
if ! command -v sf &>/dev/null; then
  if command -v sfdx &>/dev/null; then
    echo -e "${YELLOW}⚠  Found 'sfdx' but not 'sf'. Consider upgrading to the unified Salesforce CLI.${NC}"
    echo "   Install from: https://developer.salesforce.com/tools/salesforcecli"
  else
    echo -e "${RED}ERROR: Salesforce CLI (sf) not found in PATH.${NC}"
    echo "Install from: https://developer.salesforce.com/tools/salesforcecli"
    exit 1
  fi
else
  SF_VERSION=$(sf --version 2>/dev/null | head -1 || echo "unknown")
  echo -e "${GREEN}✓ Salesforce CLI found:${NC} $SF_VERSION"
fi

# ─── Create directories ───────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}Creating install directories...${NC}"

mkdir -p "$SKILLS_DIR/sf-audit"
mkdir -p "$SKILLS_DIR/sf-security"
mkdir -p "$SKILLS_DIR/sf-data-quality"
mkdir -p "$SKILLS_DIR/sf-automation"
mkdir -p "$SKILLS_DIR/sf-architecture"
mkdir -p "$SKILLS_DIR/sf-test-coverage"
mkdir -p "$AGENTS_DIR"

echo -e "${GREEN}✓ Directories ready${NC}"

# ─── Install main router skill ────────────────────────────────────────────────
echo ""
echo -e "${CYAN}Installing main skill (router)...${NC}"

if [ -f "$SCRIPT_DIR/sf-audit/SKILL.md" ]; then
  cp "$SCRIPT_DIR/sf-audit/SKILL.md" "$SKILLS_DIR/sf-audit/SKILL.md"
  echo -e "${GREEN}✓ Installed:${NC} sf-audit (router)"
else
  echo -e "${RED}ERROR: sf-audit/SKILL.md not found in $SCRIPT_DIR${NC}"
  exit 1
fi

# ─── Install sub-skills ───────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}Installing standalone skills...${NC}"

SKILLS=(
  "sf-audit:skills/sf-audit/SKILL.md"
  "sf-security:skills/sf-security/SKILL.md"
  "sf-data-quality:skills/sf-data-quality/SKILL.md"
  "sf-automation:skills/sf-automation/SKILL.md"
  "sf-architecture:skills/sf-architecture/SKILL.md"
  "sf-test-coverage:skills/sf-test-coverage/SKILL.md"
)

for entry in "${SKILLS[@]}"; do
  skill_name="${entry%%:*}"
  skill_src="${entry##*:}"

  if [ -f "$SCRIPT_DIR/$skill_src" ]; then
    cp "$SCRIPT_DIR/$skill_src" "$SKILLS_DIR/$skill_name/SKILL.md"
    echo -e "${GREEN}✓ Installed skill:${NC} $skill_name"
  else
    echo -e "${YELLOW}⚠  Skipping $skill_name — file not found: $SCRIPT_DIR/$skill_src${NC}"
  fi
done

# ─── Install agents ───────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}Installing audit agents...${NC}"

AGENTS=(
  "sf-security"
  "sf-data-quality"
  "sf-automation"
  "sf-architecture"
  "sf-test-coverage"
)

for agent in "${AGENTS[@]}"; do
  if [ -f "$SCRIPT_DIR/agents/$agent.md" ]; then
    cp "$SCRIPT_DIR/agents/$agent.md" "$AGENTS_DIR/$agent.md"
    echo -e "${GREEN}✓ Installed agent:${NC} $agent"
  else
    echo -e "${YELLOW}⚠  Skipping agent $agent — file not found${NC}"
  fi
done

# ─── Check for authenticated orgs ─────────────────────────────────────────────
echo ""
echo -e "${CYAN}Checking for authenticated Salesforce orgs...${NC}"

if command -v sf &>/dev/null; then
  ORG_COUNT=$(sf org list --json 2>/dev/null | grep -c '"username"' 2>/dev/null || echo "0")
  if [ "$ORG_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Found $ORG_COUNT authenticated org(s). Ready to audit.${NC}"
    echo ""
    echo -e "  Available orgs:"
    sf org list 2>/dev/null | grep -v "^$" | head -20 | while IFS= read -r line; do
      echo "  $line"
    done
  else
    echo -e "${YELLOW}⚠  No authenticated orgs found.${NC}"
    echo -e "  Authenticate an org before running the audit:"
    echo -e "  ${CYAN}sf org login web --alias my-org${NC}"
  fi
fi

# ─── Success banner ───────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  Installation complete!                              ${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Start a new Claude Code session, then use:"
echo ""
echo -e "  ${CYAN}/sf-audit [org]${NC}              Full audit — all 5 domains in parallel"
echo -e "  ${CYAN}/sf-audit security [org]${NC}     Security & access controls"
echo -e "  ${CYAN}/sf-audit data [org]${NC}         Data quality & completeness"
echo -e "  ${CYAN}/sf-audit automation [org]${NC}   Automation health & legacy debt"
echo -e "  ${CYAN}/sf-audit architecture [org]${NC} Org architecture & limits"
echo -e "  ${CYAN}/sf-audit coverage [org]${NC}     Apex test coverage"
echo ""
echo -e "  ${YELLOW}[org]${NC} is optional — omit to use the default authenticated org"
echo ""
