#!/usr/bin/env bash
#
# update-harness.sh — Sync ~/.aztec/harness/ with the latest scripts and skills.
#
# Run this from the harness-driven-dev repo after pulling changes.
# Equivalent to install.sh but non-interactive (no next-steps prompt).
#

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

HARNESS_DIR="$HOME/.aztec/harness/scripts"
SKILLS_SRC="$REPO_DIR/.claude/skills"
SKILLS_DST="$HOME/.claude/skills"

GREEN='\033[0;32m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo "========================================"
echo "  Aztec HDD Harness — Update"
echo "========================================"
echo ""

# ── 1. Sync scripts ──

echo -n "Syncing scripts to $HARNESS_DIR ... "
mkdir -p "$HARNESS_DIR"
cp -r "$REPO_DIR/scripts/." "$HARNESS_DIR/"
echo -e "${GREEN}done${NC}"

# ── 2. Sync skills ──

echo -n "Syncing skills to $SKILLS_DST ... "
mkdir -p "$SKILLS_DST"

for skill_dir in "$SKILLS_SRC"/*/; do
    skill_name="$(basename "$skill_dir")"
    dest="$SKILLS_DST/$skill_name"
    mkdir -p "$dest"
    cp -r "$skill_dir/." "$dest/"
done
echo -e "${GREEN}done${NC}"

# ── 3. Rewrite script paths inside the copied skills ──

echo -n "Updating script paths in installed skills ... "

for skill_file in "$SKILLS_DST"/*/SKILL.md; do
    sed -i.bak \
        -e "s|python3 scripts/|python3 $HOME/.aztec/harness/scripts/|g" \
        -e "s|bash scripts/|bash $HOME/.aztec/harness/scripts/|g" \
        "$skill_file"
    rm -f "${skill_file}.bak"
done
echo -e "${GREEN}done${NC}"

echo ""
echo -e "${GREEN}${BOLD}Harness updated successfully.${NC}"
echo ""
