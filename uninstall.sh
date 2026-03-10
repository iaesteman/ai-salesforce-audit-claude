#!/usr/bin/env bash
# uninstall.sh — Remove Salesforce Org Audit Tool from Claude Code

set -e

# ─── Colors ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

SKILLS_DIR="$HOME/.claude/skills"
AGENTS_DIR="$HOME/.claude/agents"

echo ""
echo -e "${YELLOW}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}${BOLD}  Salesforce Org Audit — Uninstaller                 ${NC}"
echo -e "${YELLOW}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ─── Remove skills ────────────────────────────────────────────────────────────
echo -e "${CYAN}Removing skills...${NC}"

SKILL_DIRS=(
  "sf-audit"
  "sf-security"
  "sf-data-quality"
  "sf-automation"
  "sf-architecture"
  "sf-test-coverage"
)

for skill in "${SKILL_DIRS[@]}"; do
  if [ -d "$SKILLS_DIR/$skill" ]; then
    rm -rf "$SKILLS_DIR/$skill"
    echo -e "${GREEN}✓ Removed skill:${NC} $skill"
  else
    echo -e "${YELLOW}  (not found, skipping):${NC} $skill"
  fi
done

# ─── Remove agents ────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}Removing agents...${NC}"

AGENTS=(
  "sf-security"
  "sf-data-quality"
  "sf-automation"
  "sf-architecture"
  "sf-test-coverage"
)

for agent in "${AGENTS[@]}"; do
  if [ -f "$AGENTS_DIR/$agent.md" ]; then
    rm -f "$AGENTS_DIR/$agent.md"
    echo -e "${GREEN}✓ Removed agent:${NC} $agent"
  else
    echo -e "${YELLOW}  (not found, skipping):${NC} $agent"
  fi
done

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  Uninstall complete.                                 ${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  All sf-audit skills and agents have been removed."
echo "  Start a new Claude Code session for changes to take effect."
echo ""
