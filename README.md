# Neuro Guard Skill

Behavior-first skill for managing late-night deep-work arousal and protecting important meetings.

## Goal

Build a reusable skill that:

1. Detects high arousal before sleep.
2. Enforces a cooldown protocol.
3. Protects next-day critical meetings.
4. Uses fact-first, fully honest communication when incidents happen.

## Why this exists

Deep coding sessions can create hyperarousal. Hyperarousal reduces sleep quality and increases missed-meeting risk.
This repository treats the problem as a protocol problem, not a willpower problem.

## macOS Widget (Notification Center)

A GitHub Action builds the NeuroGuard.app on every push to `main`.

**Setup:**
1. Download the `NeuroGuard-macOS` artifact from [Actions](https://github.com/ERerGB/neuro-guard-skill/actions) (latest run → Artifacts).
2. Unzip and move `NeuroGuard.app` to Applications or keep in Downloads.
3. Run `NeuroGuard.app` — a menu bar icon appears.
4. Click the date/time in the menu bar → Edit Widgets → add "Neuro Guard" to the sidebar.

**Usage:** The app syncs `~/.neuro-guard-telemetry.json` (from the daemon) to the widget every 10s. Click the widget to open the full web view at http://127.0.0.1:9877/ (requires `serve.py` or daemon to be running).

**Monitor CI build** (optional): After `git push`, run `./scripts/watch-build.sh` to get a macOS notification when the build completes. Requires [Wander](https://github.com/ERerGB/wander) cloned as a sibling repo.

## Configuration (manual)

Create `~/.neuro-guard.env` with your API proxy URL. The daemon and login script read this at runtime:

```bash
echo 'NEURO_GUARD_API_URL=https://your-api-proxy.example.com' > ~/.neuro-guard.env
```

Replace with your actual Magpie API proxy URL. Without this file, LLM notifications fall back to static messages.

## Quick setup (Calendar-driven daemon)

1. **Calendar auth** — one-time Google Calendar OAuth:
   ```bash
   cd skill/neuro-guard/scripts && python3 calendar_auth.py
   ```

2. **API URL + token** — set your Magpie API proxy URL and run one-shot login:
   ```bash
   # Create ~/.neuro-guard.env with:
   # NEURO_GUARD_API_URL=https://your-api-proxy.example.com
   # (Get the URL from your API proxy deployment; not included in repo for security.)

   cd skill/neuro-guard/scripts && source ~/.neuro-guard.env && python3 login.py
   ```
   Opens browser; after magic-link verification, token is saved to `~/.neuro-guard-api-token`. Without API URL or token, notifications use static fallback messages.

3. **Daemon install** — install and start the LaunchAgent:
   ```bash
   ./scripts/daemon.sh install
   ```

4. **Daemon commands**:
   ```bash
   ./scripts/daemon.sh status   # running state + last logs
   ./scripts/daemon.sh logs     # tail log
   ./scripts/daemon.sh override # skip tonight
   ./scripts/daemon.sh snooze   # extend 30 min
   ./scripts/daemon.sh stop     # stop daemon
   ./scripts/daemon.sh uninstall
   ```

## Daily usage (after setup)

| What you want | Command or action |
|---------------|-------------------|
| Check if daemon is running | `./scripts/daemon.sh status` |
| See recent logs | `./scripts/daemon.sh logs` |
| Skip tonight (no lock) | `./scripts/daemon.sh override` |
| Extend 30 min when offered | `./scripts/daemon.sh snooze` |
| Menu bar status + open full view | `./scripts/run-tray.sh` |
| Standalone web widget | `python3 skill/neuro-guard/ui/serve.py` then open http://127.0.0.1:9877/ |

The daemon runs in the background via LaunchAgent. You get macOS notifications at tier transitions (WARN → DIM → FINAL_WARN → LOCK). **NeuroGuard.app** uses a monochrome SF Symbol in the menu bar (template style, same black/white treatment as system extras); hover the icon for the current tier. "Open full view" opens the status card in the browser.

5. **Menu bar tray** (optional) — passive status in menu bar, click to open full web view:
   ```bash
   ./scripts/run-tray.sh
   ```
   Requires `pip install rumps`. Menu bar uses **monochrome symbols** (no colored emoji); "Open full view" starts the web server and opens the full widget in browser.

6. **Widget** (optional) — full web view, or run standalone:
   ```bash
   python3 skill/neuro-guard/ui/serve.py
   ```
   Reads `~/.neuro-guard-telemetry.json` (written by daemon) every 5s.

## Repository layout

- `.workflows.yml`: Wander workflow registry (CI build monitoring).
- `scripts/watch-build.sh`: Monitor build-macos workflow via Wander.
- `skill/neuro-guard/SKILL.md`: OpenClaw-compatible skill entry.
- `skill/neuro-guard/references/protocols.md`: Operational playbook and decision rules.
- `skill/neuro-guard/scripts/guard.py`: Calendar-driven daemon (main runtime).
- `skill/neuro-guard/scripts/login.py`: One-shot API proxy login (magic link).
- `skill/neuro-guard/scripts/llm_notify.py`: Gemini-based notification text (via API proxy).
- `skill/neuro-guard/scripts/neuro_guard.py`: Legacy manual/mock signal mode.
- `skill/neuro-guard/ui/widget.html`: Status card (Matrix-style).
- `skill/neuro-guard/ui/serve.py`: Local server for widget + telemetry.
- `skill/neuro-guard/tray/menubar.py`: Menu bar app (rumps); click opens full web view.
- `tests/test_neuro_guard.py`, `tests/test_guard_v2.py`: Boundary and policy tests.

## MVP boundaries

- No Apple Watch API integration yet.
- No food delivery integration yet.
- Uses manual or simulated metrics to validate workflow first.

## Reuse in OpenClaw

The `skill/neuro-guard` directory can be copied into your OpenClaw skills path directly.

Install helper:

```bash
./scripts/install_to_openclaw.sh
# or custom target root
./scripts/install_to_openclaw.sh "/path/to/openclaw/skills"
```

## Local run (manual / mock mode)

```bash
python3 skill/neuro-guard/scripts/neuro_guard.py --next-event-hours 10 --arousal-score 78 --meeting-critical yes
python3 skill/neuro-guard/scripts/neuro_guard.py --next-event-hours 10 --meeting-critical yes --signal-provider mock --signal-json '{"resting_hr_deviation":8,"hrv_drop_ratio":0.35,"sleep_debt_hours":2}'
python3 skill/neuro-guard/scripts/neuro_guard.py --next-event-hours 8 --arousal-score 82 --meeting-critical yes --draft-incident-message
```

## Tests

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

## Phase-3 readiness

The script already includes a `SignalProvider` adapter seam:

- `--signal-provider manual` + `--arousal-score` for local/manual mode.
- `--signal-provider mock` + `--signal-json` for wearable-bridge simulation.

This keeps one decision core while allowing future real hardware providers.

## Local trial in Cursor / Claude Code (subagent-harness base)

SSOT source files:

- `agents/archetypes/neuro-guard.agent.md`
- `agents/archetypes/neuro-guard.agent.ext.yaml`

Compose to local runtimes:

```bash
# Preview only
./scripts/compose_subagents_local.sh dry-run

# Write to ~/.cursor/agents and ~/.claude/agents
./scripts/compose_subagents_local.sh apply

# Clean generated files
./scripts/compose_subagents_local.sh clean
```

Optional overrides:

```bash
HARNESS_DIR=/path/to/subagent-harness CURSOR_DST=/custom/cursor/agents CLAUDE_DST=/custom/claude/agents ./scripts/compose_subagents_local.sh apply
```
