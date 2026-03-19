#!/usr/bin/env python3
"""Create a test event tomorrow to verify calendar read + critical marking."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build

from calendar_auth import get_credentials

LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def main() -> None:
    service = build("calendar", "v3", credentials=get_credentials())

    tomorrow = datetime.now(LOCAL_TZ) + timedelta(days=1)
    start = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)

    event = {
        "summary": "投资人会议 - Test Event",
        "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Shanghai"},
        "end": {"dateTime": end.isoformat(), "timeZone": "Asia/Shanghai"},
        "attendees": [
            {"email": "test-investor@example.com"},
        ],
    }

    created = service.events().insert(calendarId="primary", body=event).execute()
    print(f"Created test event: {created.get('summary')}")
    print(f"  Start: {start.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Event ID: {created['id']}")
    print(f"\nNow run: python3 calendar_check.py --mark-critical")


if __name__ == "__main__":
    main()
