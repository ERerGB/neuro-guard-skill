"""Tests for Neuro Guard v2 — calendar-driven rest enforcement."""

import importlib.util
import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skill" / "neuro-guard" / "scripts"

# Add scripts dir to sys.path so guard.py can find its sibling modules
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

config_mod = load_module("config", SCRIPTS_DIR / "config.py")
load_module("calendar_auth", SCRIPTS_DIR / "calendar_auth.py")
load_module("calendar_check", SCRIPTS_DIR / "calendar_check.py")
guard_mod = load_module("guard", SCRIPTS_DIR / "guard.py")

GuardConfig = config_mod.GuardConfig
compute_cutoff = guard_mod.compute_cutoff
compute_intervention_tier = guard_mod.compute_intervention_tier
reset_state_if_new_day = guard_mod.reset_state_if_new_day
OVERRIDE_FILE = guard_mod.OVERRIDE_FILE
SNOOZE_FILE = guard_mod.SNOOZE_FILE

TZ = ZoneInfo("Asia/Shanghai")


class CutoffCalculationTests(unittest.TestCase):
    """Verify cutoff = event_time - sleep - wind_down."""

    def test_default_config_9am_meeting(self) -> None:
        config = GuardConfig()  # 8h sleep + 2.5h buffer = 10.5h
        event = datetime(2026, 3, 20, 9, 0, tzinfo=TZ)
        cutoff = compute_cutoff(event, config)
        self.assertEqual(cutoff, datetime(2026, 3, 19, 22, 30, tzinfo=TZ))

    def test_custom_config_10am_meeting(self) -> None:
        config = GuardConfig(sleep_hours=7.0, wind_down_hours=1.5)  # 8.5h total
        event = datetime(2026, 3, 20, 10, 0, tzinfo=TZ)
        cutoff = compute_cutoff(event, config)
        self.assertEqual(cutoff, datetime(2026, 3, 20, 1, 30, tzinfo=TZ))

    def test_early_morning_meeting_yields_previous_evening(self) -> None:
        config = GuardConfig()
        event = datetime(2026, 3, 20, 7, 0, tzinfo=TZ)  # 7am meeting
        cutoff = compute_cutoff(event, config)
        self.assertEqual(cutoff, datetime(2026, 3, 19, 20, 30, tzinfo=TZ))

    def test_afternoon_meeting_is_lenient(self) -> None:
        config = GuardConfig()
        event = datetime(2026, 3, 20, 14, 0, tzinfo=TZ)  # 2pm meeting
        cutoff = compute_cutoff(event, config)
        self.assertEqual(cutoff, datetime(2026, 3, 20, 3, 30, tzinfo=TZ))


class InterventionTierTests(unittest.TestCase):
    """Verify tier escalation: WARN → DIM → FINAL_WARN → LOCK."""

    def setUp(self) -> None:
        self.config = GuardConfig()
        self.cutoff = datetime(2026, 3, 19, 22, 30, tzinfo=TZ)

    def test_ok_when_far_from_cutoff(self) -> None:
        now = datetime(2026, 3, 19, 20, 0, tzinfo=TZ)
        self.assertIsNone(compute_intervention_tier(now, self.cutoff, self.config))

    def test_warn_at_50_minutes_before(self) -> None:
        now = datetime(2026, 3, 19, 21, 40, tzinfo=TZ)
        self.assertEqual("WARN", compute_intervention_tier(now, self.cutoff, self.config))

    def test_dim_at_20_minutes_before(self) -> None:
        now = datetime(2026, 3, 19, 22, 5, tzinfo=TZ)  # 25min before → DIM zone
        self.assertEqual("DIM", compute_intervention_tier(now, self.cutoff, self.config))

    def test_final_warn_at_10_minutes_before(self) -> None:
        now = datetime(2026, 3, 19, 22, 20, tzinfo=TZ)  # 10min before → FINAL_WARN
        self.assertEqual("FINAL_WARN", compute_intervention_tier(now, self.cutoff, self.config))

    def test_lock_at_cutoff(self) -> None:
        now = datetime(2026, 3, 19, 22, 30, tzinfo=TZ)
        self.assertEqual("LOCK", compute_intervention_tier(now, self.cutoff, self.config))

    def test_lock_past_cutoff(self) -> None:
        now = datetime(2026, 3, 19, 23, 0, tzinfo=TZ)
        self.assertEqual("LOCK", compute_intervention_tier(now, self.cutoff, self.config))


class StateManagementTests(unittest.TestCase):
    """Verify daily reset and snooze counter behavior."""

    def test_new_day_resets_snooze_count(self) -> None:
        old_state = {"date": "2026-03-18", "snooze_count": 2, "lock_count": 3}
        new_state = reset_state_if_new_day(old_state, "2026-03-19")
        self.assertEqual(0, new_state["snooze_count"])
        self.assertEqual(0, new_state["lock_count"])
        self.assertEqual("2026-03-19", new_state["date"])

    def test_same_day_preserves_state(self) -> None:
        state = {"date": "2026-03-19", "snooze_count": 1, "lock_count": 2}
        result = reset_state_if_new_day(state, "2026-03-19")
        self.assertEqual(1, result["snooze_count"])
        self.assertEqual(2, result["lock_count"])


class ConfigTests(unittest.TestCase):
    """Verify config parameter defaults and derived values."""

    def test_default_total_buffer(self) -> None:
        config = GuardConfig()
        self.assertEqual(10.5, config.total_buffer_hours)

    def test_minimum_buffer(self) -> None:
        config = GuardConfig()
        # 7h minimum sleep + 2.5h wind-down
        self.assertEqual(9.5, config.minimum_buffer_hours)

    def test_custom_overrides(self) -> None:
        config = GuardConfig(sleep_hours=6.0, wind_down_hours=1.0)
        self.assertEqual(7.0, config.total_buffer_hours)

    def test_critical_keywords_include_investor(self) -> None:
        config = GuardConfig()
        self.assertIn("投资", config.critical_keywords)
        self.assertIn("investor", config.critical_keywords)


class CriticalEventDetectionTests(unittest.TestCase):
    """Verify event critical classification logic."""

    def _make_event(self, summary: str = "", attendees: int = 0, marked: bool = False) -> dict:
        event: dict = {"summary": summary, "id": "test-123"}
        if attendees > 0:
            event["attendees"] = [{"email": f"p{i}@example.com"} for i in range(attendees)]
        if marked:
            event["extendedProperties"] = {"private": {"neuro_guard_critical": "true"}}
        return event

    def test_keyword_match(self) -> None:
        # Need to import from calendar_check which requires google deps
        # so we test the logic inline
        from calendar_check import is_critical
        self.assertTrue(is_critical(self._make_event(summary="投资人面谈")))

    def test_attendees_make_it_critical(self) -> None:
        from calendar_check import is_critical
        self.assertTrue(is_critical(self._make_event(summary="随便聊聊", attendees=2)))

    def test_solo_non_keyword_is_not_critical(self) -> None:
        from calendar_check import is_critical
        self.assertFalse(is_critical(self._make_event(summary="买菜", attendees=0)))

    def test_already_marked_is_critical(self) -> None:
        from calendar_check import is_critical
        self.assertTrue(is_critical(self._make_event(summary="随便", marked=True)))


if __name__ == "__main__":
    unittest.main()
