#!/usr/bin/env bash
set -euo pipefail

REPO="abrahambahez/scholartools"
SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
LANG="en"
UNINSTALL=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang) LANG="$2"; shift 2 ;;
    --uninstall) UNINSTALL=true; shift ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if $UNINSTALL; then
  rm -rf "$SKILLS_DIR"/scholartools-*/
  echo "Uninstalled scholartools skills from $SKILLS_DIR"
  exit 0
fi

RELEASE=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest")
ASSET_URL=$(echo "$RELEASE" | grep -o '"browser_download_url": "[^"]*scholartools-skills-'"$LANG"'-[^"]*\.zip"' | grep -o 'https://[^"]*' | head -1)

if [ -z "$ASSET_URL" ]; then
  echo "Error: no skills asset found for language '$LANG'" >&2
  exit 1
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

curl -fsSL -o "$TMP/skills.zip" "$ASSET_URL"
mkdir -p "$SKILLS_DIR"
unzip -q "$TMP/skills.zip" -d "$TMP/extracted"

for dir in "$TMP/extracted"/*/; do
  name=$(basename "$dir")
  rm -rf "$SKILLS_DIR/$name"
  cp -r "$dir" "$SKILLS_DIR/$name"
  echo "Installed: $name"
done
