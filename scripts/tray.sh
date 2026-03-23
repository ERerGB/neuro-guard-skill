#!/usr/bin/env bash
#
# Neuro Guard menu bar (rumps) — LaunchAgent only.
#
# Usage:
#   ./tray.sh install   — install + load LaunchAgent (stops any manual menubar.py)
#   ./tray.sh start     — load agent
#   ./tray.sh stop      — unload agent
#   ./tray.sh restart   — unload + load
#   ./tray.sh status    — launchd state + last log lines
#   ./tray.sh logs      — tail tray log
#   ./tray.sh uninstall — unload + remove plist

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python3"
TRAY_RUNNER="$SCRIPT_DIR/neuro_guard_tray_runner.sh"

LABEL="com.neuroguard.tray"
PLIST_SRC="$SCRIPT_DIR/com.neuroguard.tray.plist"
PLIST_DST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs/NeuroGuard"

kill_manual_tray() {
    # Stop nohup / Terminal runs so only launchd owns the menu bar process.
    pkill -f "/skill/neuro-guard/tray/menubar.py" 2>/dev/null || true
}

cmd_install() {
    echo "Installing Neuro Guard tray LaunchAgent..."

    if [ ! -f "$VENV_PYTHON" ]; then
        echo "Error: venv not found at $VENV_PYTHON"
        echo "Run: cd $PROJECT_ROOT && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
        exit 1
    fi

    if ! "$VENV_PYTHON" -c "import rumps" 2>/dev/null; then
        echo "Error: rumps not installed in venv."
        echo "Run: $VENV_PYTHON -m pip install rumps"
        exit 1
    fi

    if [ ! -x "$TRAY_RUNNER" ]; then
        echo "Error: tray runner not executable: $TRAY_RUNNER"
        echo "Run: chmod +x $TRAY_RUNNER"
        exit 1
    fi

    mkdir -p "$LOG_DIR"
    mkdir -p "$(dirname "$PLIST_DST")"

    kill_manual_tray
    sleep 0.5

    sed \
        -e "s|__TRAY_RUNNER__|$TRAY_RUNNER|g" \
        -e "s|__PROJECT_ROOT__|$PROJECT_ROOT|g" \
        -e "s|__LOG_DIR__|$LOG_DIR|g" \
        "$PLIST_SRC" > "$PLIST_DST"

    echo "  Plist installed: $PLIST_DST"
    echo "  Logs: $LOG_DIR/neuro-guard-tray.log"

    cmd_start
    echo "Done. Menu bar tray is managed by launchd ($LABEL)."
}

cmd_start() {
    if [ ! -f "$PLIST_DST" ]; then
        echo "No plist at $PLIST_DST — run: $0 install"
        exit 1
    fi
    launchctl load -w "$PLIST_DST" 2>/dev/null || true
    echo "Tray LaunchAgent loaded."
}

cmd_stop() {
    launchctl unload "$PLIST_DST" 2>/dev/null || true
    echo "Tray LaunchAgent unloaded."
}

cmd_restart() {
    cmd_stop
    sleep 1
    cmd_start
}

cmd_status() {
    if launchctl list | grep -q "$LABEL"; then
        echo "Tray status: LOADED (see launchctl list for PID)"
        launchctl list "$LABEL" 2>/dev/null || true
    else
        echo "Tray status: NOT LOADED"
    fi
    echo ""
    if [ -f "$LOG_DIR/neuro-guard-tray.log" ]; then
        echo "Last 10 tray log lines:"
        tail -10 "$LOG_DIR/neuro-guard-tray.log"
    else
        echo "No tray log yet."
    fi
    if [ -f "$LOG_DIR/neuro-guard-tray.err" ] && [ -s "$LOG_DIR/neuro-guard-tray.err" ]; then
        echo ""
        echo "Last 5 stderr lines:"
        tail -5 "$LOG_DIR/neuro-guard-tray.err"
    fi
}

cmd_logs() {
    if [ -f "$LOG_DIR/neuro-guard-tray.log" ]; then
        tail -f "$LOG_DIR/neuro-guard-tray.log"
    else
        echo "No tray log file yet."
    fi
}

cmd_uninstall() {
    kill_manual_tray
    cmd_stop
    rm -f "$PLIST_DST"
    echo "Tray LaunchAgent removed."
    echo "Logs kept at: $LOG_DIR/"
}

case "${1:-help}" in
    install)   cmd_install ;;
    start)     cmd_start ;;
    stop)      cmd_stop ;;
    restart)   cmd_restart ;;
    status)    cmd_status ;;
    logs)      cmd_logs ;;
    uninstall) cmd_uninstall ;;
    *)
        echo "Usage: $0 {install|start|stop|restart|status|logs|uninstall}"
        exit 1
        ;;
esac
