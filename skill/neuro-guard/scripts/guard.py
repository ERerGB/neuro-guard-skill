#!/usr/bin/env python3
"""Neuro Guard v2 — Calendar-driven rest enforcement for Mac.

Core formula:
    cutoff_time = earliest_critical_event - sleep_hours - wind_down_hours

Intervention timeline (example: cutoff = 22:30):
    21:30  WARN        gentle notification
    22:00  DIM         screen dims + notification
    22:15  FINAL_WARN  "save your work, 15 min left"
    22:30  LOCK        lock screen
    22:35  grace ends  → if still active, offer snooze (max 2x 30min)
    snooze exhausted   → re-lock every 10 min

Override: touch ~/.neuro-guard-override → skip tonight entirely.
Snooze:   touch ~/.neuro-guard-snooze   → extend 30 min (auto-deleted).

Usage:
    python3 guard.py                  # one-shot check
    python3 guard.py --watch          # continuous daemon mode
    python3 guard.py --dry-run        # preview, no side effects
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timedelta, date
from pathlib import Path
from zoneinfo import ZoneInfo

from calendar_auth import get_credentials
from calendar_check import (
    EXTENDED_PROP_KEY,
    event_start_time,
    fetch_tomorrow_events,
    is_critical,
)
from config import GuardConfig
from llm_notify import generate_message
from googleapiclient.discovery import build

OVERRIDE_FILE = Path.home() / ".neuro-guard-override"
SNOOZE_FILE = Path.home() / ".neuro-guard-snooze"
STATE_FILE = Path.home() / ".neuro-guard-state.json"


# ---------------------------------------------------------------------------
# State persistence — survives daemon restarts
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state))


def reset_state_if_new_day(state: dict, today: str) -> dict:
    """Reset snooze counter and lock tracking at midnight."""
    if state.get("date") != today:
        return {"date": today, "snooze_count": 0, "lock_count": 0, "last_lock_ts": None}
    return state


# ---------------------------------------------------------------------------
# Override & Snooze file protocol
# ---------------------------------------------------------------------------

def is_override_active() -> bool:
    """User created ~/.neuro-guard-override → skip tonight."""
    return OVERRIDE_FILE.exists()


def consume_snooze() -> bool:
    """If user created ~/.neuro-guard-snooze, consume it and return True."""
    if SNOOZE_FILE.exists():
        SNOOZE_FILE.unlink(missing_ok=True)
        return True
    return False


def clean_override_on_new_day(today: str) -> None:
    """Auto-delete stale override files from previous days."""
    if OVERRIDE_FILE.exists():
        try:
            mtime = datetime.fromtimestamp(OVERRIDE_FILE.stat().st_mtime)
            if mtime.strftime("%Y-%m-%d") != today:
                OVERRIDE_FILE.unlink(missing_ok=True)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# macOS system interactions
# ---------------------------------------------------------------------------

def get_mac_idle_seconds() -> float:
    """Seconds since last user input (keyboard/mouse)."""
    result = subprocess.run(
        ["ioreg", "-c", "IOHIDSystem", "-d", "4"],
        capture_output=True, text=True,
    )
    for line in result.stdout.splitlines():
        if "HIDIdleTime" in line:
            try:
                raw = line.split("=")[-1].strip()
                return int(raw) / 1_000_000_000
            except (ValueError, IndexError):
                continue
    return 0.0


def send_notification(title: str, message: str, sound: str = "Funk") -> None:
    """Send macOS notification."""
    escaped_msg = message.replace('"', '\\"')
    escaped_title = title.replace('"', '\\"')
    script = f'display notification "{escaped_msg}" with title "{escaped_title}" sound name "{sound}"'
    subprocess.run(["osascript", "-e", script], capture_output=True)


def lock_screen() -> None:
    """Lock screen via Ctrl+Cmd+Q. Requires Accessibility permission for Python/Terminal."""
    r = subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to keystroke "q" using {command down, control down}'],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(f"  [LOCK] osascript failed (code={r.returncode}): {r.stderr or r.stdout}")
        # Fallback: at least sleep the display
        subprocess.run(["pmset", "displaysleepnow"], capture_output=True)
        print(f"  [LOCK] Fallback: display sleep triggered")


# ---------------------------------------------------------------------------
# Core computation (pure, testable)
# ---------------------------------------------------------------------------

def compute_cutoff(earliest_critical: datetime, config: GuardConfig) -> datetime:
    return earliest_critical - timedelta(hours=config.total_buffer_hours)


def compute_intervention_tier(now: datetime, cutoff: datetime, config: GuardConfig) -> str | None:
    """WARN → DIM → FINAL_WARN → LOCK → POST_LOCK."""
    minutes_to_cutoff = (cutoff - now).total_seconds() / 60

    if minutes_to_cutoff <= config.lock_minutes_before:
        return "LOCK"
    if minutes_to_cutoff <= config.final_warn_minutes_before:
        return "FINAL_WARN"
    if minutes_to_cutoff <= config.dim_minutes_before:
        return "DIM"
    if minutes_to_cutoff <= config.warn_minutes_before:
        return "WARN"
    return None


# ---------------------------------------------------------------------------
# Intervention execution
# ---------------------------------------------------------------------------

TIER_SOUNDS = {
    "WARN": "Funk",
    "DIM": "Sosumi",
    "FINAL_WARN": "Hero",
    "LOCK": "Basso",
    "SNOOZE_OFFER": "Glass",
    "RE_LOCK": "Basso",
}


def _make_message(tier: str, ctx: dict) -> str:
    """Generate an LLM message with context, falling back to static."""
    return generate_message(
        tier=tier,
        now=ctx.get("now"),
        event_time=ctx.get("event_time"),
        event_title=ctx.get("event_title"),
        warn_count=ctx.get("warn_count", 0),
        snooze_count=ctx.get("snooze_count", 0),
    )


def execute_intervention(tier: str, ctx: dict, dry_run: bool = False) -> None:
    msg = _make_message(tier, ctx)
    sound = TIER_SOUNDS.get(tier, "Funk")

    if dry_run:
        action = "lock screen" if tier == "LOCK" else "notify"
        print(f"  [DRY RUN] {tier}: {action} — {msg}")
        return

    send_notification("Neuro Guard", msg, sound=sound)
    print(f"  {tier}: {msg}")

    if tier == "LOCK":
        time.sleep(3)
        lock_screen()


def notify_snooze_available(
    snooze_count: int, max_snooze: int, grace_seconds: int,
    ctx: dict, dry_run: bool = False,
) -> None:
    """After user unlocks, tell them snooze is available during grace period."""
    remaining = max_snooze - snooze_count
    grace_min = grace_seconds // 60

    llm_msg = _make_message("SNOOZE_OFFER", ctx)
    # Always append the actionable instruction
    action_hint = (
        f"\ntouch ~/.neuro-guard-snooze 延长 30 分钟 (剩余 {remaining} 次)"
        if remaining > 0 else ""
    )
    msg = f"{llm_msg}{action_hint}"

    if dry_run:
        print(f"  [DRY RUN] SNOOZE_OFFER: {msg}")
        return

    send_notification("Neuro Guard", msg, sound="Glass")
    print(f"  SNOOZE_OFFER: {msg}")


def execute_relock(ctx: dict, dry_run: bool = False) -> None:
    """Re-lock after grace period expired without snooze."""
    msg = _make_message("RE_LOCK", ctx)

    if dry_run:
        print(f"  [DRY RUN] RE-LOCK: {msg}")
        return

    send_notification("Neuro Guard", msg, sound="Basso")
    print(f"  RE-LOCK: {msg}")
    time.sleep(3)
    lock_screen()


# ---------------------------------------------------------------------------
# Calendar fetch
# ---------------------------------------------------------------------------

def fetch_earliest_critical_tomorrow(config: GuardConfig) -> tuple[datetime, str] | None:
    """Return (earliest_critical_time, event_title) or None if no critical events."""
    service = build("calendar", "v3", credentials=get_credentials())
    events = fetch_tomorrow_events(service)

    candidates: list[tuple[datetime, str]] = []
    for event in events:
        if is_critical(event):
            start = event_start_time(event)
            if start:
                title = event.get("summary", "(no title)")
                candidates.append((start, title))

    return min(candidates, key=lambda x: x[0]) if candidates else None


# ---------------------------------------------------------------------------
# Main check cycle
# ---------------------------------------------------------------------------

def run_check(config: GuardConfig, state: dict, dry_run: bool = False) -> dict:
    """One guard cycle. Mutates and returns state dict."""
    now = datetime.now(config.timezone)
    today = now.strftime("%Y-%m-%d")

    clean_override_on_new_day(today)
    state = reset_state_if_new_day(state, today)

    if is_override_active():
        print(f"[{now.strftime('%H:%M:%S')}] Override active. Guard skipped tonight.")
        return state

    result = fetch_earliest_critical_tomorrow(config)

    if result is None:
        print(f"[{now.strftime('%H:%M:%S')}] No critical events tomorrow. Guard is off.")
        return state

    earliest, event_title = result
    cutoff = compute_cutoff(earliest, config)
    tier = compute_intervention_tier(now, cutoff, config)
    idle = get_mac_idle_seconds()
    user_active = idle < config.idle_threshold_seconds

    tag = f"Critical: {earliest.strftime('%H:%M')} → Cutoff: {cutoff.strftime('%H:%M')}"
    print(f"[{now.strftime('%H:%M:%S')}] {tag} | Tier: {tier or 'OK'} | Idle: {idle:.0f}s | Snooze: {state.get('snooze_count', 0)}/{config.max_snooze_count}")

    # --- Write telemetry for UI Widget ---
    try:
        minutes_to_cutoff = (cutoff - now).total_seconds() / 60
        telemetry = {
            "tier": tier or "OK",
            "event_title": event_title,
            "event_time": earliest.strftime("%H:%M"),
            "cutoff_time": cutoff.strftime("%H:%M"),
            "minutes_to_cutoff": round(minutes_to_cutoff, 1),
            "snooze_count": state.get("snooze_count", 0),
            "max_snooze": config.max_snooze_count,
            "updated_at": now.isoformat()
        }
        (Path.home() / ".neuro-guard-telemetry.json").write_text(json.dumps(telemetry, ensure_ascii=False))
    except Exception as e:
        pass

    # Skip notify tiers when user idle (away from keyboard); LOCK always executes
    if not user_active and tier != "LOCK":
        if tier:
            print(f"  User idle ({idle:.0f}s), skipping intervention.")
        return state

    # Context dict shared by all LLM notification generators
    ctx = {
        "now": now,
        "event_time": earliest.strftime("%H:%M"),
        "event_title": event_title,
        "warn_count": state.get("lock_count", 0),
        "snooze_count": state.get("snooze_count", 0),
    }

    # --- Pre-lock tiers ---
    if tier in ("WARN", "DIM", "FINAL_WARN"):
        execute_intervention(tier, ctx, dry_run=dry_run)
        return state

    # --- LOCK tier: state machine ---
    #
    # Flow after first lock:
    #   LOCK → user unlocks → detect active → notify snooze available (grace starts)
    #   → grace period expires → check snooze file → snooze or re-lock
    #
    # States tracked in state dict:
    #   last_lock_ts:       when we last locked the screen
    #   grace_notified:     whether we already sent the "snooze available" notification
    #   snooze_until:       if snooze active, when it expires
    #   snooze_count:       how many snoozes used today

    if tier == "LOCK":
        snooze_count = state.get("snooze_count", 0)

        # --- Active snooze window: user already snoozed, respect it ---
        snooze_until_str = state.get("snooze_until")
        if snooze_until_str:
            snooze_until_dt = datetime.fromisoformat(snooze_until_str)
            if now < snooze_until_dt:
                remaining = (snooze_until_dt - now).total_seconds() / 60
                print(f"  Snooze active: {remaining:.0f}min remaining.")
                return state
            # Snooze expired
            state["snooze_until"] = None
            state["last_lock_ts"] = None
            state["grace_notified"] = False
            save_state(state)
            # Fall through to lock again

        last_lock = state.get("last_lock_ts")

        # --- First lock (or after snooze expired) ---
        if last_lock is None:
            execute_intervention("LOCK", ctx, dry_run=dry_run)
            state["last_lock_ts"] = now.isoformat()
            state["lock_count"] = state.get("lock_count", 0) + 1
            state["grace_notified"] = False
            save_state(state)
            return state

        last_lock_dt = datetime.fromisoformat(last_lock)
        elapsed = (now - last_lock_dt).total_seconds()

        # --- Grace period: user unlocked, offer snooze ---
        if elapsed < config.grace_period_seconds:
            if not state.get("grace_notified"):
                notify_snooze_available(
                    snooze_count, config.max_snooze_count,
                    config.grace_period_seconds, ctx, dry_run=dry_run,
                )
                state["grace_notified"] = True
                save_state(state)
            else:
                remaining = config.grace_period_seconds - elapsed
                print(f"  Grace period: {remaining:.0f}s remaining. Waiting for snooze decision...")

                # Check early snooze during grace period
                if consume_snooze() and snooze_count < config.max_snooze_count:
                    state["snooze_count"] = snooze_count + 1
                    snooze_until = now + timedelta(minutes=config.snooze_duration_minutes)
                    state["snooze_until"] = snooze_until.isoformat()
                    state["grace_notified"] = False
                    msg = f"Snooze #{state['snooze_count']} 激活！延长至 {snooze_until.strftime('%H:%M')}。"
                    if not dry_run:
                        send_notification("Neuro Guard", msg, sound="Glass")
                    print(f"  SNOOZE: {msg}")
                    save_state(state)
            return state

        # --- Grace period expired: check snooze one last time, then re-lock ---
        if consume_snooze() and snooze_count < config.max_snooze_count:
            state["snooze_count"] = snooze_count + 1
            snooze_until = now + timedelta(minutes=config.snooze_duration_minutes)
            state["snooze_until"] = snooze_until.isoformat()
            state["grace_notified"] = False
            msg = f"Snooze #{state['snooze_count']} 激活！延长至 {snooze_until.strftime('%H:%M')}。"
            if not dry_run:
                send_notification("Neuro Guard", msg, sound="Glass")
            print(f"  SNOOZE: {msg}")
            save_state(state)
            return state

        # No snooze requested → re-lock
        execute_relock(ctx, dry_run=dry_run)
        state["last_lock_ts"] = now.isoformat()
        state["lock_count"] = state.get("lock_count", 0) + 1
        state["grace_notified"] = False
        save_state(state)

    return state


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Neuro Guard v2 — Calendar-driven rest enforcement")
    parser.add_argument("--watch", action="store_true", help="Continuous daemon mode (check every 5 min)")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without executing")
    parser.add_argument("--sleep-hours", type=float, help="Override sleep hours")
    parser.add_argument("--wind-down-hours", type=float, help="Override wind-down buffer hours")
    parser.add_argument("--interval", type=int, default=300, help="Check interval in seconds (default: 300)")
    args = parser.parse_args()

    overrides = {}
    if args.sleep_hours is not None:
        overrides["sleep_hours"] = args.sleep_hours
    if args.wind_down_hours is not None:
        overrides["wind_down_hours"] = args.wind_down_hours

    config = GuardConfig(**overrides) if overrides else GuardConfig()
    state = load_state()

    print("Neuro Guard v2")
    print(f"  Sleep: {config.sleep_hours}h | Buffer: {config.wind_down_hours}h | Total: {config.total_buffer_hours}h")
    print(f"  Tiers: WARN@-{config.warn_minutes_before}min, DIM@-{config.dim_minutes_before}min, "
          f"FINAL_WARN@-{config.final_warn_minutes_before}min, LOCK@cutoff")
    print(f"  Post-lock: grace={config.grace_period_seconds}s, snooze={config.max_snooze_count}x{config.snooze_duration_minutes}min, "
          f"re-lock every {config.relock_interval_seconds}s")
    print(f"  Override: touch {OVERRIDE_FILE}")
    print(f"  Snooze:   touch {SNOOZE_FILE}")
    print()

    if args.watch:
        print(f"Watching (every {args.interval}s)... Ctrl+C to stop\n")
        try:
            while True:
                state = run_check(config, state, dry_run=args.dry_run)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nGuard stopped.")
    else:
        state = run_check(config, state, dry_run=args.dry_run)
        save_state(state)


if __name__ == "__main__":
    main()
