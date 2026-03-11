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

REPO="iaesteman/ai-salesforce-audit-claude"

# ─── Paths ────────────────────────────────────────────────────────────────────
SKILLS_DIR="$HOME/.claude/skills"
AGENTS_DIR="$HOME/.claude/agents"

# ─── Detect: local clone vs curl | bash ───────────────────────────────────────
# When piped via curl, BASH_SOURCE[0] is empty or "bash" — no local files exist.
# Detect by checking whether the sf-audit skill file exists next to this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd 2>/dev/null || echo "")"

if [ -f "$SCRIPT_DIR/sf-audit/SKILL.md" ]; then
  # Running from a local git clone
  SOURCE_DIR="$SCRIPT_DIR"
  CLEANUP_TMP=false
else
  # Running via curl | bash — download repo to a temp directory
  TMP_DIR=$(mktemp -d)
  CLEANUP_TMP=true
  SOURCE_DIR="$TMP_DIR"

  if command -v git &>/dev/null; then
    git clone --quiet --depth 1 "https://github.com/$REPO.git" "$TMP_DIR"
  else
    echo -e "${RED}ERROR: git is required for remote installation but was not found.${NC}"
    echo "Install git or clone the repo manually:"
    echo "  git clone https://github.com/$REPO.git"
    exit 1
  fi
fi

# ─── Banner ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}${BOLD}  Salesforce Org Audit — Claude Code Installer       ${NC}"
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ─── Prerequisite: Claude Code ────────────────────────────────────────────────
if command -v claude &>/dev/null; then
  CLAUDE_VERSION=$(claude --version 2>/dev/null | head -1 || echo "unknown")
  echo -e "${GREEN}✓ Claude Code found:${NC} $CLAUDE_VERSION"
elif [ -d "$HOME/.claude" ]; then
  echo -e "${GREEN}✓ Claude Code detected${NC} (~/.claude directory exists)"
else
  echo -e "${YELLOW}⚠  Claude Code not detected in PATH.${NC}"
  echo "   Install from: https://claude.ai/code"
  echo "   Continuing install — files will be ready once Claude Code is installed."
fi

# ─── Prerequisite: Salesforce CLI ─────────────────────────────────────────────
if command -v sf &>/dev/null; then
  SF_VERSION=$(sf --version 2>/dev/null | head -1 || echo "unknown")
  echo -e "${GREEN}✓ Salesforce CLI found:${NC} $SF_VERSION"
elif command -v sfdx &>/dev/null; then
  echo -e "${YELLOW}⚠  Found 'sfdx' but not 'sf'. Consider upgrading to the unified Salesforce CLI.${NC}"
  echo "   Install from: https://developer.salesforce.com/tools/salesforcecli"
else
  echo -e "${YELLOW}⚠  Salesforce CLI (sf) not found in PATH.${NC}"
  echo "   Install from: https://developer.salesforce.com/tools/salesforcecli"
  echo "   Continuing install — authenticate an org before running /sf-audit."
fi

# ─── Create directories ───────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}Creating install directories...${NC}"

mkdir -p "$SKILLS_DIR/sf-audit"
mkdir -p "$SKILLS_DIR/sf-audit-security"
mkdir -p "$SKILLS_DIR/sf-audit-data"
mkdir -p "$SKILLS_DIR/sf-audit-automation"
mkdir -p "$SKILLS_DIR/sf-audit-architecture"
mkdir -p "$SKILLS_DIR/sf-audit-coverage"
mkdir -p "$SKILLS_DIR/sf-audit-naming"
mkdir -p "$SKILLS_DIR/sf-audit-report-pdf"
mkdir -p "$AGENTS_DIR"

echo -e "${GREEN}✓ Directories ready${NC}"

# ─── Install all skills ───────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}Installing skills...${NC}"

SKILLS=(
  "sf-audit:sf-audit/SKILL.md"
  "sf-audit-security:skills/sf-audit-security/SKILL.md"
  "sf-audit-data:skills/sf-audit-data/SKILL.md"
  "sf-audit-automation:skills/sf-audit-automation/SKILL.md"
  "sf-audit-architecture:skills/sf-audit-architecture/SKILL.md"
  "sf-audit-coverage:skills/sf-audit-coverage/SKILL.md"
  "sf-audit-naming:skills/sf-audit-naming/SKILL.md"
  "sf-audit-report-pdf:skills/sf-audit-report-pdf/SKILL.md"
)

for entry in "${SKILLS[@]}"; do
  skill_name="${entry%%:*}"
  skill_src="${entry##*:}"
  cp "$SOURCE_DIR/$skill_src" "$SKILLS_DIR/$skill_name/SKILL.md"
  echo -e "${GREEN}✓ Installed skill:${NC} $skill_name"
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
  "sf-naming"
)

for agent in "${AGENTS[@]}"; do
  cp "$SOURCE_DIR/agents/$agent.md" "$AGENTS_DIR/$agent.md"
  echo -e "${GREEN}✓ Installed agent:${NC} $agent"
done

# ─── Install Python scripts ───────────────────────────────────────────────────
echo ""
echo -e "${CYAN}Installing PDF report script...${NC}"

SCRIPTS_DEST="$HOME/.claude/scripts"
mkdir -p "$SCRIPTS_DEST"

if [ -f "$SOURCE_DIR/scripts/generate_sf_pdf_report.py" ]; then
  cp "$SOURCE_DIR/scripts/generate_sf_pdf_report.py" "$SCRIPTS_DEST/generate_sf_pdf_report.py"
  chmod +x "$SCRIPTS_DEST/generate_sf_pdf_report.py"
  echo -e "${GREEN}✓ Installed script:${NC} generate_sf_pdf_report.py"

  # Also copy to current working directory so /sf-audit report-pdf can find it
  cp "$SOURCE_DIR/scripts/generate_sf_pdf_report.py" "./generate_sf_pdf_report.py" 2>/dev/null || true
fi

# Check for Python 3 and reportlab
echo ""
echo -e "${CYAN}Checking Python dependencies (required for PDF reports)...${NC}"

if command -v python3 &>/dev/null; then
  echo -e "${GREEN}✓ Python3 found:${NC} $(python3 --version 2>&1)"
  if python3 -c "import reportlab" &>/dev/null; then
    echo -e "${GREEN}✓ reportlab found${NC}"
  else
    echo -e "${YELLOW}⚠  reportlab not installed.${NC}"
    echo -e "  Required for PDF reports. Install with:"
    echo -e "  ${CYAN}pip3 install reportlab${NC}"
  fi
else
  echo -e "${YELLOW}⚠  Python3 not found — PDF report generation will not be available.${NC}"
fi

# ─── Cleanup temp dir (curl install only) ─────────────────────────────────────
[ "$CLEANUP_TMP" = true ] && rm -rf "$TMP_DIR"

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
echo -e "  Installed: 1 router + 8 skills + 6 agents + 1 PDF script"
echo ""
echo -e "  Start a new Claude Code session, then use:"
echo ""
echo -e "  ${CYAN}/sf-audit [org]${NC}              Full audit — all 5 domains in parallel"
echo -e "  ${CYAN}/sf-audit security [org]${NC}     Security & access controls"
echo -e "  ${CYAN}/sf-audit data [org]${NC}         Data quality & completeness"
echo -e "  ${CYAN}/sf-audit automation [org]${NC}   Automation health & legacy debt"
echo -e "  ${CYAN}/sf-audit architecture [org]${NC} Org architecture & limits"
echo -e "  ${CYAN}/sf-audit coverage [org]${NC}     Apex test coverage"
echo -e "  ${CYAN}/sf-audit naming [org]${NC}       Naming conventions audit"
echo -e "  ${CYAN}/sf-audit report-pdf [org]${NC}   Generate PDF report → SF-AUDIT-REPORT.pdf"
echo ""
echo -e "  ${YELLOW}[org]${NC} is optional — omit to use the default authenticated org"
echo ""
