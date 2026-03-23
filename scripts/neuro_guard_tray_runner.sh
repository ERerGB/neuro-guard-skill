#!/usr/bin/env bash
# launchd entrypoint for Neuro Guard menu bar (rumps).
# Keeps Background Items label as "neuro_guard_tray_runner" instead of bare Python.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$HOME/.neuro-guard.env" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$HOME/.neuro-guard.env"
    set +a
fi

exec "$PROJECT_ROOT/.venv/bin/python3" -u "$PROJECT_ROOT/skill/neuro-guard/tray/menubar.py"
