#!/usr/bin/env python3
"""Serve Neuro Guard widget with live telemetry.

Reads ~/.neuro-guard-telemetry.json (written by guard daemon) and serves it
at /telemetry. Opens the widget in the default browser.

Usage:
    python3 serve.py              # port 9877
    python3 serve.py 8888         # custom port
"""

from __future__ import annotations

import http.server
import json
import webbrowser
from pathlib import Path

PORT = 9877
TELEMETRY_PATH = Path.home() / ".neuro-guard-telemetry.json"


def make_handler(directory):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def do_GET(self):
            if self.path == "/" or self.path == "/index.html":
                self.path = "/widget.html"
            elif self.path == "/telemetry":
                self._serve_telemetry()
                return
            super().do_GET()

        def _serve_telemetry(self):
            try:
                if TELEMETRY_PATH.exists():
                    data = json.loads(TELEMETRY_PATH.read_text())
                else:
                    data = {"tier": "OK", "event_title": "—", "event_time": "—", "cutoff_time": "—",
                            "minutes_to_cutoff": 0, "snooze_count": 0, "max_snooze": 2}
            except Exception:
                data = {"tier": "OK", "event_title": "—", "event_time": "—", "cutoff_time": "—",
                        "minutes_to_cutoff": 0, "snooze_count": 0, "max_snooze": 2}

            body = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    return Handler


def main():
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    ui_dir = Path(__file__).resolve().parent

    Handler = make_handler(str(ui_dir))
    server = http.server.HTTPServer(("127.0.0.1", port), Handler)

    url = f"http://127.0.0.1:{port}/"
    print(f"Neuro Guard Widget: {url}")
    print("Press Ctrl+C to stop.")
    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        print("\nStopped.")


if __name__ == "__main__":
    main()
