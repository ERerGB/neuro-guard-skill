#!/usr/bin/env bash
#
# Neuro Guard daemon manager.
#
# Usage:
#   ./daemon.sh install   — install + start LaunchAgent
#   ./daemon.sh start     — start daemon
#   ./daemon.sh stop      — stop daemon
#   ./daemon.sh restart   — stop + start
#   ./daemon.sh status    — show running state + last log lines
#   ./daemon.sh logs      — tail log
#   ./daemon.sh uninstall — stop + remove LaunchAgent
#   ./daemon.sh override  — skip tonight (creates override file)
#   ./daemon.sh snooze    — extend 30 min (creates snooze file)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRIPTS_DIR="$PROJECT_ROOT/skill/neuro-guard/scripts"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python3"
GUARD_SCRIPT="$SCRIPTS_DIR/guard.py"
RUNNER_SCRIPT="$SCRIPT_DIR/neuro_guard_daemon_runner.sh"

LABEL="com.neuroguard.daemon"
PLIST_SRC="$SCRIPT_DIR/com.neuroguard.daemon.plist"
PLIST_DST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs/NeuroGuard"

cmd_install() {
    echo "Installing Neuro Guard daemon..."

    if [ ! -f "$VENV_PYTHON" ]; then
        echo "Error: venv not found at $VENV_PYTHON"
        echo "Run: cd $PROJECT_ROOT && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
        exit 1
    fi

    if [ ! -f "$PROJECT_ROOT/token.json" ]; then
        echo "Error: token.json not found. Run calendar_auth.py first to authorize."
        exit 1
    fi
    if [ ! -f "$HOME/.neuro-guard-api-token" ]; then
        echo "Warning: ~/.neuro-guard-api-token not found. LLM notifications will use static fallback."
        echo "  Run: source ~/.neuro-guard.env && cd $SCRIPTS_DIR && python3 login.py"
    fi
    if [ ! -f "$HOME/.neuro-guard.env" ]; then
        echo "Warning: ~/.neuro-guard.env not found. Create it with NEURO_GUARD_API_URL=... for LLM notifications."
    fi
    if [ ! -x "$RUNNER_SCRIPT" ]; then
        echo "Error: runner script not executable: $RUNNER_SCRIPT"
        echo "Run: chmod +x $RUNNER_SCRIPT"
        exit 1
    fi

    mkdir -p "$LOG_DIR"
    mkdir -p "$(dirname "$PLIST_DST")"

    sed \
        -e "s|__RUNNER_SCRIPT__|$RUNNER_SCRIPT|g" \
        -e "s|__SCRIPTS_DIR__|$SCRIPTS_DIR|g" \
        -e "s|__LOG_DIR__|$LOG_DIR|g" \
        "$PLIST_SRC" > "$PLIST_DST"

    echo "  Plist installed: $PLIST_DST"
    echo "  Logs: $LOG_DIR/"

    cmd_start
    echo "Done. Neuro Guard is running."
}

cmd_start() {
    launchctl load -w "$PLIST_DST" 2>/dev/null || true
    echo "Daemon started."
}

cmd_stop() {
    launchctl unload "$PLIST_DST" 2>/dev/null || true
    echo "Daemon stopped."
}

cmd_restart() {
    cmd_stop
    sleep 1
    cmd_start
}

cmd_status() {
    if launchctl list | grep -q "$LABEL"; then
        echo "Status: RUNNING"
        pid=$(launchctl list "$LABEL" 2>/dev/null | head -1 | awk '{print $1}')
        if [ "$pid" != "-" ] && [ -n "$pid" ]; then
            echo "PID: $pid"
        fi
    else
        echo "Status: STOPPED"
    fi
    echo ""
    echo "Override file: $([ -f "$HOME/.neuro-guard-override" ] && echo "ACTIVE" || echo "none")"
    echo "Snooze file:   $([ -f "$HOME/.neuro-guard-snooze" ] && echo "PENDING" || echo "none")"
    echo ""
    if [ -f "$LOG_DIR/neuro-guard.log" ]; then
        echo "Last 10 log lines:"
        tail -10 "$LOG_DIR/neuro-guard.log"
    fi
}

cmd_logs() {
    if [ -f "$LOG_DIR/neuro-guard.log" ]; then
        tail -f "$LOG_DIR/neuro-guard.log"
    else
        echo "No log file yet."
    fi
}

cmd_uninstall() {
    cmd_stop
    rm -f "$PLIST_DST"
    echo "LaunchAgent removed."
    echo "Logs kept at: $LOG_DIR/"
    echo "To fully clean up: rm -rf $LOG_DIR ~/.neuro-guard-state.json ~/.neuro-guard-override ~/.neuro-guard-snooze"
}

cmd_override() {
    touch "$HOME/.neuro-guard-override"
    echo "Override active. Guard will skip tonight."
    echo "File auto-deletes tomorrow. Manual: rm ~/.neuro-guard-override"
}

cmd_snooze() {
    touch "$HOME/.neuro-guard-snooze"
    echo "Snooze requested. Guard will extend 30 minutes on next check."
}

case "${1:-help}" in
    install)   cmd_install ;;
    start)     cmd_start ;;
    stop)      cmd_stop ;;
    restart)   cmd_restart ;;
    status)    cmd_status ;;
    logs)      cmd_logs ;;
    uninstall) cmd_uninstall ;;
    override)  cmd_override ;;
    snooze)    cmd_snooze ;;
    *)
        echo "Usage: $0 {install|start|stop|restart|status|logs|uninstall|override|snooze}"
        exit 1
        ;;
esac
