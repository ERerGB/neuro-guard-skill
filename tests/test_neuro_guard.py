import importlib.util
from pathlib import Path
import sys
import unittest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "skill" / "neuro-guard" / "scripts" / "neuro_guard.py"
SPEC = importlib.util.spec_from_file_location("neuro_guard_script", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

GuardInput = MODULE.GuardInput
SignalInput = MODULE.SignalInput
build_incident_message = MODULE.build_incident_message
build_decision = MODULE.build_decision
classify_risk = MODULE.classify_risk
message_policy_violations = MODULE.message_policy_violations
score_from_signal = MODULE.score_from_signal


class RiskTierTests(unittest.TestCase):
    def test_red_when_meeting_is_critical_and_window_is_short(self) -> None:
        tier = classify_risk(GuardInput(next_event_hours=8, arousal_score=72, meeting_critical=True))
        self.assertEqual("RED", tier)

    def test_yellow_for_medium_risk_path(self) -> None:
        tier = classify_risk(GuardInput(next_event_hours=16, arousal_score=55, meeting_critical=True))
        self.assertEqual("YELLOW", tier)

    def test_green_for_low_risk_case(self) -> None:
        tier = classify_risk(GuardInput(next_event_hours=20, arousal_score=30, meeting_critical=False))
        self.assertEqual("GREEN", tier)


class DecisionMappingTests(unittest.TestCase):
    def test_red_decision_contains_hard_cooldown(self) -> None:
        decision = build_decision(GuardInput(next_event_hours=10, arousal_score=90, meeting_critical=True))
        self.assertEqual("RED", decision.tier)
        self.assertTrue(any("hard cooldown" in action.lower() for action in decision.actions))


class MessagePolicyTests(unittest.TestCase):
    def test_default_template_has_no_forbidden_phrases(self) -> None:
        message = build_incident_message()
        self.assertEqual([], message_policy_violations(message))

    def test_policy_detects_excuse_like_phrasing(self) -> None:
        violations = message_policy_violations("Please understand because I was too tired.")
        self.assertIn("please understand", violations)
        self.assertIn("because i was", violations)


class SignalBridgeTests(unittest.TestCase):
    def test_signal_score_maps_into_expected_range(self) -> None:
        score = score_from_signal(SignalInput(resting_hr_deviation=9.0, hrv_drop_ratio=0.4, sleep_debt_hours=3.0))
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        self.assertGreater(score, 40)


if __name__ == "__main__":
    unittest.main()
