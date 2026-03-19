#!/usr/bin/env bash
# Run Neuro Guard menu bar app (tray).
# Requires: pip install rumps (in project venv)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python3"
TRAY_SCRIPT="$PROJECT_ROOT/skill/neuro-guard/tray/menubar.py"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: venv not found. Run: cd $PROJECT_ROOT && python3 -m venv .venv && .venv/bin/pip install rumps"
    exit 1
fi

exec "$VENV_PYTHON" "$TRAY_SCRIPT"
