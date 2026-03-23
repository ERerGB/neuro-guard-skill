#!/usr/bin/env bash
# Deprecated: menu bar is started by LaunchAgent (scripts/tray.sh).
# This script only helps migrate old habits.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_DST="$HOME/Library/LaunchAgents/com.neuroguard.tray.plist"

if [ -f "$PLIST_DST" ]; then
    echo "Using LaunchAgent: $PLIST_DST"
    exec "$SCRIPT_DIR/tray.sh" restart
fi

echo "Tray LaunchAgent is not installed. Run once:"
echo "  $SCRIPT_DIR/tray.sh install"
exit 1
