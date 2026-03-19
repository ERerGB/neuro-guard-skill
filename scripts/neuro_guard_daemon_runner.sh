#!/usr/bin/env bash
# Dedicated launchd entrypoint for Neuro Guard daemon.
# Using a named runner avoids showing "Python 3" in Background Items.
# Loads NEURO_GUARD_API_URL from ~/.neuro-guard.env if present.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$HOME/.neuro-guard.env" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$HOME/.neuro-guard.env"
    set +a
fi

exec "$PROJECT_ROOT/.venv/bin/python3" -u "$PROJECT_ROOT/skill/neuro-guard/scripts/guard.py" --watch --interval 300
