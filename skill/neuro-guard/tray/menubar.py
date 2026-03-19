#!/usr/bin/env python3
"""Neuro Guard menu bar app — passive status, click to open full web view."""

from __future__ import annotations

import json
import subprocess
import threading
import webbrowser
from pathlib import Path

import rumps

TELEMETRY_PATH = Path.home() / ".neuro-guard-telemetry.json"
WIDGET_URL = "http://127.0.0.1:9877/"
PORT = 9877
SERVE_SCRIPT = Path(__file__).resolve().parent.parent / "ui" / "serve.py"

TIER_LABELS = {
    "OK": "NOMINAL",
    "WARN": "WIND DOWN",
    "DIM": "WIND DOWN",
    "FINAL_WARN": "CRITICAL",
    "LOCK": "LOCKDOWN",
}

TIER_EMOJI = {
    "OK": "🟢",
    "WARN": "🟡",
    "DIM": "🟡",
    "FINAL_WARN": "🟠",
    "LOCK": "🔴",
}


def load_telemetry() -> dict | None:
    try:
        if TELEMETRY_PATH.exists():
            return json.loads(TELEMETRY_PATH.read_text())
    except Exception:
        pass
    return None


def format_countdown(minutes: float) -> str:
    if minutes is None or minutes < 0:
        return "—"
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h:02d}:{m:02d}"


def is_port_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_serve_background():
    """Start serve.py in background if not already running."""
    if is_port_in_use(PORT):
        return
    if SERVE_SCRIPT.exists():
        subprocess.Popen(
            ["python3", str(SERVE_SCRIPT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


class NeuroGuardApp(rumps.App):
    def __init__(self):
        super().__init__("Neuro Guard", title="🟢")
        self.telemetry: dict | None = None
        self.timer = rumps.Timer(self._on_tick, 10)
        self.timer.start()
        self._on_tick(None)

    def _on_tick(self, _):
        self.telemetry = load_telemetry()
        if self.telemetry:
            tier = self.telemetry.get("tier", "OK")
            emoji = TIER_EMOJI.get(tier, "🟢")
            mins = self.telemetry.get("minutes_to_cutoff")
            if mins is not None and mins >= 0:
                self.title = f"{emoji} {format_countdown(mins)}"
            else:
                self.title = f"{emoji} {TIER_LABELS.get(tier, 'NOMINAL')}"
        else:
            self.title = "🟢 —"

    @rumps.clicked("Open full view")
    def open_full_view(self, _):
        start_serve_background()
        # Give server a moment to start
        threading.Timer(0.5, lambda: webbrowser.open(WIDGET_URL)).start()

    @rumps.clicked("Quit")
    def quit_app(self, _):
        rumps.quit_application()


def main():
    app = NeuroGuardApp()
    app.run()


if __name__ == "__main__":
    main()
