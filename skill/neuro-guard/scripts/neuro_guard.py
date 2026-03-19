#!/usr/bin/env python3
"""Neuro Guard decision helper.

This script keeps one decision core and allows multiple signal inputs:
1) Manual input (phase 1)
2) Mock wearable metrics (phase 3 bridge)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GuardInput:
    next_event_hours: int
    arousal_score: int
    meeting_critical: bool


@dataclass(frozen=True)
class GuardDecision:
    tier: str
    actions: list[str]
    communication_hint: str


@dataclass(frozen=True)
class SignalInput:
    resting_hr_deviation: float
    hrv_drop_ratio: float
    sleep_debt_hours: float


class SignalProvider(Protocol):
    """Provider contract for physiological signals."""

    def read(self) -> SignalInput:
        """Return normalized physiological metrics."""


@dataclass(frozen=True)
class MockSignalProvider:
    resting_hr_deviation: float
    hrv_drop_ratio: float
    sleep_debt_hours: float

    def read(self) -> SignalInput:
        return SignalInput(
            resting_hr_deviation=self.resting_hr_deviation,
            hrv_drop_ratio=self.hrv_drop_ratio,
            sleep_debt_hours=self.sleep_debt_hours,
        )


def score_from_signal(signal: SignalInput) -> int:
    """Map wearable-like metrics to 0-100 arousal score."""
    # Weighted additive model keeps behavior transparent and tunable.
    score = (
        min(signal.resting_hr_deviation, 30.0) * 1.8
        + min(signal.hrv_drop_ratio, 0.8) * 50.0
        + min(signal.sleep_debt_hours, 8.0) * 6.0
    )
    return max(0, min(100, int(round(score))))


def classify_risk(data: GuardInput) -> str:
    if data.meeting_critical and data.next_event_hours <= 12 and data.arousal_score >= 70:
        return "RED"

    if (
        (data.meeting_critical and data.next_event_hours <= 18 and data.arousal_score >= 50)
        or (not data.meeting_critical and data.arousal_score >= 75)
    ):
        return "YELLOW"

    return "GREEN"


def build_decision(data: GuardInput) -> GuardDecision:
    tier = classify_risk(data)

    if tier == "GREEN":
        return GuardDecision(
            tier=tier,
            actions=[
                "Finish current task block.",
                "Set one alarm.",
                "No additional intervention needed.",
            ],
            communication_hint="No external communication required.",
        )

    if tier == "YELLOW":
        return GuardDecision(
            tier=tier,
            actions=[
                "Stop feature coding in 30 minutes.",
                "Run 15-minute cooldown routine.",
                "Set two alarms.",
            ],
            communication_hint="If risk grows, proactively send a short schedule confirmation.",
        )

    return GuardDecision(
        tier=tier,
        actions=[
            "Stop coding now.",
            "Run 25-minute hard cooldown routine.",
            "Set two alarms and one backup notification path.",
        ],
        communication_hint=(
            "If any delay risk exists, send a fact-first pre-commitment note: "
            "'I may be at risk of delay; I will confirm by <time>'."
        ),
    )


def build_incident_message(
    counterpart: str = "there",
    follow_up_artifact: str = "a one-page brief",
) -> str:
    return (
        f"I missed today's meeting, {counterpart}. This is my responsibility.\n"
        "I am sorry for wasting your time.\n"
        f"If you are open to it, I can adapt to your preferred 15-30 minute slot and send {follow_up_artifact} before the call.\n"
        "If now is not a fit, I understand."
    )


def message_policy_violations(message: str) -> list[str]:
    forbidden_phrases = [
        "because i was",
        "please understand",
        "i was too tired",
        "i worked all night",
        "it was not my fault",
    ]
    lowered = message.lower()
    return [phrase for phrase in forbidden_phrases if phrase in lowered]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Neuro Guard decision helper")
    parser.add_argument("--next-event-hours", type=int, required=True, help="Hours until next important event")
    parser.add_argument("--arousal-score", type=int, help="Arousal score from 0 to 100 (manual mode)")
    parser.add_argument("--signal-provider", choices=["manual", "mock"], default="manual")
    parser.add_argument(
        "--signal-json",
        type=str,
        help='Signal payload for mock mode, e.g. \'{"resting_hr_deviation":8,"hrv_drop_ratio":0.3,"sleep_debt_hours":2}\'',
    )
    parser.add_argument(
        "--meeting-critical",
        type=str,
        choices=["yes", "no"],
        required=True,
        help="Whether next event is critical",
    )
    parser.add_argument("--draft-incident-message", action="store_true", help="Print fact-first recovery message draft")
    return parser.parse_args()


def validate_inputs(data: GuardInput) -> None:
    if data.next_event_hours < 0:
        raise ValueError("next_event_hours must be >= 0")
    if not 0 <= data.arousal_score <= 100:
        raise ValueError("arousal_score must be between 0 and 100")


def parse_signal_json(raw: str) -> SignalInput:
    payload = json.loads(raw)
    return SignalInput(
        resting_hr_deviation=float(payload["resting_hr_deviation"]),
        hrv_drop_ratio=float(payload["hrv_drop_ratio"]),
        sleep_debt_hours=float(payload["sleep_debt_hours"]),
    )


def resolve_arousal_score(args: argparse.Namespace) -> int:
    if args.signal_provider == "manual":
        if args.arousal_score is None:
            raise ValueError("--arousal-score is required when --signal-provider=manual")
        return int(args.arousal_score)

    if not args.signal_json:
        raise ValueError("--signal-json is required when --signal-provider=mock")
    provider = MockSignalProvider(**parse_signal_json(args.signal_json).__dict__)
    signal = provider.read()
    return score_from_signal(signal)


def print_decision(decision: GuardDecision, arousal_score: int) -> None:
    print(f"Arousal score: {arousal_score}")
    print(f"Risk tier: {decision.tier}")
    print("Actions:")
    for index, action in enumerate(decision.actions, start=1):
        print(f"{index}. {action}")
    print(f"Communication hint: {decision.communication_hint}")


def main() -> None:
    args = parse_args()
    arousal_score = resolve_arousal_score(args)
    data = GuardInput(
        next_event_hours=args.next_event_hours,
        arousal_score=arousal_score,
        meeting_critical=args.meeting_critical == "yes",
    )
    validate_inputs(data)
    decision = build_decision(data)
    print_decision(decision, arousal_score)
    if args.draft_incident_message:
        message = build_incident_message()
        print("\nIncident message draft:")
        print(message)
        violations = message_policy_violations(message)
        if violations:
            print(f"\nPolicy warning: forbidden phrasing detected: {violations}")


if __name__ == "__main__":
    main()
