---
name: neuro-guard
description: "Manage deep-work hyperarousal and meeting reliability. Use when the user reports sleep loss after intensive coding, risk of missing important meetings, or wants an automated regulation protocol using wearable/body signals. Prioritize fact-first communication, ownership of impact, and actionable recovery plans."
---

# Neuro Guard

Use this skill to turn an unstable high-arousal work pattern into a repeatable protocol.

## Core principles

- Facts first, no excuses.
- Own impact before explaining context.
- Do not manipulate the other party's response.
- Prefer protocol over motivation.

## Execution order

1. Classify the next event risk.
2. Run the correct arousal protocol.
3. Set meeting safety gates.
4. If incident occurs, execute honest recovery script.

Read `references/protocols.md` before taking action.

## Incident communication skeleton

Use this exact structure:

1. State what happened.
2. Own responsibility.
3. Apologize for time impact.
4. Offer concrete recovery options.
5. Accept any outcome.

Example:

> I missed today's meeting. This is my responsibility. I am sorry for wasting your time.
> If you are open to it, I can adapt to any 15-30 minute slot you prefer and send a one-page brief in advance.
> If now is not a fit, I understand.

## Script usage (local MVP)

Use:

```bash
python3 {baseDir}/scripts/neuro_guard.py --next-event-hours 10 --arousal-score 78 --meeting-critical yes
python3 {baseDir}/scripts/neuro_guard.py --next-event-hours 10 --meeting-critical yes --signal-provider mock --signal-json '{"resting_hr_deviation":8,"hrv_drop_ratio":0.35,"sleep_debt_hours":2}'
```

The script outputs:

- risk tier
- required protocol
- communication recommendation
- optional incident message draft
