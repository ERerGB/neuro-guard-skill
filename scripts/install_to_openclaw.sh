#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)/skill/neuro-guard"
TARGET_ROOT="${1:-$HOME/.openclaw/skills}"
TARGET_DIR="$TARGET_ROOT/neuro-guard"

mkdir -p "$TARGET_ROOT"
rm -rf "$TARGET_DIR"
cp -R "$SOURCE_DIR" "$TARGET_DIR"

echo "Installed neuro-guard skill to: $TARGET_DIR"
echo "Next step: start a new OpenClaw session to refresh skill snapshot."
