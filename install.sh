#!/usr/bin/env bash
#
# install.sh — Install the Aztec HDD harness globally.
#
# What this does:
#   1. Copies scripts/ → ~/.aztec/harness/scripts/
#   2. Copies .claude/skills/ → ~/.claude/skills/  (each skill in its own subfolder)
#   3. Rewrites script paths inside the copied skills so they point to
#      ~/.aztec/harness/scripts/ instead of the local scripts/ directory.
#
# Idempotent: safe to run multiple times.
#

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

HARNESS_DIR="$HOME/.aztec/harness/scripts"
SKILLS_SRC="$REPO_DIR/.claude/skills"
SKILLS_DST="$HOME/.claude/skills"

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo "========================================"
echo "  Aztec HDD Harness — Global Install"
echo "========================================"
echo ""

# ── 1. Copy scripts ──

echo -n "Installing scripts to $HARNESS_DIR ... "
mkdir -p "$HARNESS_DIR"
cp -r "$REPO_DIR/scripts/." "$HARNESS_DIR/"
echo -e "${GREEN}done${NC}"

# ── 2. Copy skills ──

echo -n "Installing skills to $SKILLS_DST ... "
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
    # python3 scripts/ → python3 ~/.aztec/harness/scripts/
    sed -i.bak \
        -e "s|python3 scripts/|python3 $HOME/.aztec/harness/scripts/|g" \
        -e "s|bash scripts/|bash $HOME/.aztec/harness/scripts/|g" \
        "$skill_file"
    rm -f "${skill_file}.bak"
done
echo -e "${GREEN}done${NC}"

echo ""
echo -e "${GREEN}${BOLD}Installation complete!${NC}"
echo ""
echo "========================================"
echo "  Next steps"
echo "========================================"
echo ""
echo "1. Generate an API key in Aztec Plataforma:"
echo "   Settings → API Keys → New Key"
echo ""
echo "2. In each project you work on, copy the template and fill it in:"
echo "   cp $REPO_DIR/project-env-template <your-project>/.env"
echo ""
echo "3. The harness is now available in every project."
echo "   Open any project in Cursor/terminal and use:"
echo "   /start-issue <KEY>   /close-issue <KEY>   /status   /create-issue"
echo ""
