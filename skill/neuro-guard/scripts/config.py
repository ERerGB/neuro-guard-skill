"""Neuro Guard configuration.

All personal parameters live here. Edit to match your routine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class GuardConfig:
    # Sleep parameters
    sleep_hours: float = 8.0
    sleep_hours_minimum: float = 7.0
    wind_down_hours: float = 2.5  # buffer before sleep (phone browsing, etc.)

    # Intervention escalation (minutes before cutoff)
    warn_minutes_before: int = 60    # gentle reminder
    dim_minutes_before: int = 30     # screen dims
    final_warn_minutes_before: int = 15  # last warning: save your work
    lock_minutes_before: int = 0     # hard cutoff

    # Post-lock behavior
    grace_period_seconds: int = 300  # 5 min after lock before re-checking
    max_snooze_count: int = 2        # max snooze presses (30 min each)
    snooze_duration_minutes: int = 30
    relock_interval_seconds: int = 600  # after snoozes exhausted, re-lock every 10 min

    # Calendar
    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo("Asia/Shanghai"))
    critical_keywords: list[str] = field(default_factory=lambda: [
        "投资", "investor", "pitch", "demo", "面试", "interview",
        "演示", "board", "review", "客户", "client",
    ])
    auto_critical_if_has_attendees: bool = True

    # Mac idle
    idle_threshold_seconds: int = 300  # 5 min idle = user stepped away

    @property
    def total_buffer_hours(self) -> float:
        """Total hours needed before a meeting: sleep + wind-down."""
        return self.sleep_hours + self.wind_down_hours

    @property
    def minimum_buffer_hours(self) -> float:
        return self.sleep_hours_minimum + self.wind_down_hours
