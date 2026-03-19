"""One-shot login helper for Neuro Guard.

Opens the API proxy login page with a local callback. After the user
authenticates via magic link, the token is automatically saved to
~/.neuro-guard-api-token. The script then exits.
"""

from __future__ import annotations

import http.server
import os
import sys
import threading
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# API base URL from env; no default to avoid exposing production URL in open source
_API_BASE = (os.environ.get("NEURO_GUARD_API_URL") or "").rstrip("/")
API_LOGIN = f"{_API_BASE}/login" if _API_BASE else ""
TOKEN_PATH = Path.home() / ".neuro-guard-api-token"
CALLBACK_PORT = 9876


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Receives the redirect after magic-link verification."""

    token: str | None = None

    def do_GET(self) -> None:
        qs = parse_qs(urlparse(self.path).query)
        token = qs.get("token", [None])[0]

        if token:
            _CallbackHandler.token = token
            TOKEN_PATH.write_text(token)
            self._respond(200, _success_html(token))
        else:
            self._respond(400, _error_html("No token received."))

        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def _respond(self, code: int, html: str) -> None:
        body = html.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:
        pass


def _success_html(token: str) -> str:
    preview = token[:32] + "..."
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Neuro Guard — Logged in</title>
<style>body{{font-family:system-ui;background:#0a0a0a;color:#fff;display:flex;
align-items:center;justify-content:center;min-height:100vh;margin:0}}
.c{{text-align:center;max-width:400px}}
h1{{color:#4ade80;font-size:28px}}
p{{color:rgba(255,255,255,.6);line-height:1.6}}
code{{display:block;margin:16px 0;padding:12px;background:#111;border:1px solid #333;
border-radius:8px;font-size:12px;color:#888;word-break:break-all}}
small{{color:rgba(255,255,255,.35)}}</style></head>
<body><div class="c"><h1>Done ✓</h1>
<p>Token saved to <code>~/.neuro-guard-api-token</code></p>
<code>{preview}</code>
<p><small>You can close this tab. Neuro Guard daemon will pick up the token automatically.</small></p>
</div></body></html>"""


def _error_html(msg: str) -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Error</title>
<style>body{{font-family:system-ui;background:#0a0a0a;color:#f87171;display:flex;
align-items:center;justify-content:center;min-height:100vh;margin:0}}</style></head>
<body><p>{msg}</p></body></html>"""


def main() -> None:
    if not API_LOGIN:
        print("Error: NEURO_GUARD_API_URL not set. Set it to your Magpie API proxy URL.", file=sys.stderr)
        sys.exit(1)

    redirect_uri = f"http://localhost:{CALLBACK_PORT}/callback"
    login_url = f"{API_LOGIN}?redirect_uri={redirect_uri}"

    print("Neuro Guard — Login")
    print(f"  Opening: {login_url}")
    print(f"  Waiting for callback on port {CALLBACK_PORT}...")
    print()

    server = http.server.HTTPServer(("127.0.0.1", CALLBACK_PORT), _CallbackHandler)

    threading.Timer(1.0, lambda: webbrowser.open(login_url)).start()

    server.serve_forever()

    if _CallbackHandler.token:
        print(f"  Token saved to {TOKEN_PATH}")
        print("  Done!")
    else:
        print("  No token received.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
