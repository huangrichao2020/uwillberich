#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
SKILL_NAME="a-share-decision-desk"
SKILL_SRC="$REPO_ROOT/skill/$SKILL_NAME"
MODE="${1:-auto}"
TARGET_BASE="${2:-}"

usage() {
  cat <<'EOF'
Usage:
  ./install_skill.sh [auto|codex|openclaw] [target_base]

Examples:
  ./install_skill.sh
  ./install_skill.sh codex
  ./install_skill.sh openclaw
  ./install_skill.sh codex /tmp/test-skills
EOF
}

if [[ ! -d "$SKILL_SRC" ]]; then
  echo "skill source not found: $SKILL_SRC" >&2
  exit 1
fi

if [[ -z "$TARGET_BASE" ]]; then
  case "$MODE" in
    auto)
      if [[ -d "$HOME/.codex" ]] || [[ ! -d "$HOME/.openclaw" ]]; then
        TARGET_BASE="$HOME/.codex/skills"
        MODE="codex"
      else
        TARGET_BASE="$HOME/.openclaw/skills"
        MODE="openclaw"
      fi
      ;;
    codex)
      TARGET_BASE="$HOME/.codex/skills"
      ;;
    openclaw)
      TARGET_BASE="$HOME/.openclaw/skills"
      ;;
    *)
      usage >&2
      exit 1
      ;;
  esac
fi

TARGET_DIR="$TARGET_BASE/$SKILL_NAME"
mkdir -p "$TARGET_BASE"
rm -rf "$TARGET_DIR"
cp -R "$SKILL_SRC" "$TARGET_DIR"

echo "installed_skill=$SKILL_NAME"
echo "mode=$MODE"
echo "target_dir=$TARGET_DIR"
echo "em_api_key_required=true"
echo "eastmoney_apply_url=https://ai.eastmoney.com/p/signup/index.html"
echo "setup_example=printf '%s' 'your_em_api_key' | python3 $TARGET_DIR/scripts/runtime_config.py set-em-key --stdin"
