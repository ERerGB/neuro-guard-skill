#!/usr/bin/env python3
"""Fetch tomorrow's calendar events and identify critical ones.

Usage:
    python3 calendar_check.py              # show tomorrow's events
    python3 calendar_check.py --mark-critical "投资人"  # also mark matching events as critical
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build

from calendar_auth import get_credentials

LOCAL_TZ = ZoneInfo("Asia/Shanghai")

CRITICAL_KEYWORDS = [
    "投资", "investor", "pitch", "demo", "面试", "interview",
    "演示", "board", "review", "客户", "client",
]

CRITICAL_COLOR_ID = "11"  # Tomato red in Google Calendar
EXTENDED_PROP_KEY = "neuro_guard_critical"


def get_calendar_service():
    creds = get_credentials()
    return build("calendar", "v3", credentials=creds)


def fetch_tomorrow_events(service) -> list[dict]:
    """Return all events between tomorrow 00:00 and 23:59 local time."""
    now_local = datetime.now(LOCAL_TZ)
    tomorrow_start = (now_local + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    tomorrow_end = tomorrow_start.replace(hour=23, minute=59, second=59)

    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=tomorrow_start.isoformat(),
            timeMax=tomorrow_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return result.get("items", [])


def is_critical(event: dict) -> bool:
    """Check if event is already marked or matches critical keywords."""
    props = event.get("extendedProperties", {}).get("private", {})
    if props.get(EXTENDED_PROP_KEY) == "true":
        return True

    has_others = len(event.get("attendees", [])) > 1
    title = event.get("summary", "").lower()
    keyword_hit = any(kw in title for kw in CRITICAL_KEYWORDS)

    return has_others or keyword_hit


def mark_event_critical(service, event: dict) -> None:
    """Add neuro_guard_critical flag and red color to an event."""
    event_id = event["id"]
    patch_body: dict = {
        "colorId": CRITICAL_COLOR_ID,
        "extendedProperties": {
            "private": {EXTENDED_PROP_KEY: "true"},
        },
    }
    service.events().patch(
        calendarId="primary", eventId=event_id, body=patch_body
    ).execute()


def event_start_time(event: dict) -> datetime | None:
    """Extract start time as timezone-aware datetime."""
    start = event.get("start", {})
    dt_str = start.get("dateTime")
    if dt_str:
        return datetime.fromisoformat(dt_str)
    date_str = start.get("date")
    if date_str:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=LOCAL_TZ)
    return None


def format_event(event: dict, critical: bool) -> str:
    start = event_start_time(event)
    time_str = start.strftime("%H:%M") if start else "all-day"
    tag = " [CRITICAL]" if critical else ""
    return f"  {time_str}  {event.get('summary', '(no title)')}{tag}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Check tomorrow's calendar")
    parser.add_argument(
        "--mark-critical",
        type=str,
        nargs="*",
        help="Extra keywords to match and mark as critical",
    )
    args = parser.parse_args()

    extra_keywords = [k.lower() for k in (args.mark_critical or [])]

    service = get_calendar_service()
    events = fetch_tomorrow_events(service)

    if not events:
        print("Tomorrow: no events found.")
        return

    print(f"Tomorrow ({(datetime.now(LOCAL_TZ) + timedelta(days=1)).strftime('%Y-%m-%d')}):\n")

    critical_events = []
    for event in events:
        title_lower = event.get("summary", "").lower()
        extra_hit = any(kw in title_lower for kw in extra_keywords)
        critical = is_critical(event) or extra_hit

        if critical and args.mark_critical is not None:
            props = event.get("extendedProperties", {}).get("private", {})
            if props.get(EXTENDED_PROP_KEY) != "true":
                mark_event_critical(service, event)
                print(f"  -> Marked as critical: {event.get('summary', '')}")

        if critical:
            critical_events.append(event)

        print(format_event(event, critical))

    if critical_events:
        earliest = min(critical_events, key=lambda e: event_start_time(e) or datetime.max.replace(tzinfo=LOCAL_TZ))
        earliest_time = event_start_time(earliest)
        if earliest_time:
            print(f"\nEarliest critical event: {earliest_time.strftime('%H:%M')}")
    else:
        print("\nNo critical events tomorrow.")


if __name__ == "__main__":
    main()
