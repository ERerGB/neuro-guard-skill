# Neuro Guard Protocols

## 1) Input model (MVP)

Use three inputs:

- `next_event_hours`: hours until next critical meeting.
- `arousal_score`: 0-100 subjective score (manual mode) or derived score from signal provider.
- `meeting_critical`: `yes` or `no`.

Signal provider bridge (phase 3):

- `resting_hr_deviation`
- `hrv_drop_ratio`
- `sleep_debt_hours`

These map to a single `arousal_score` so the decision core stays unchanged.

## 2) Risk classification

Apply minimum-complexity rules:

- `RED`:
  - `meeting_critical=yes` and `next_event_hours <= 12` and `arousal_score >= 70`
- `YELLOW`:
  - `meeting_critical=yes` and `next_event_hours <= 18` and `arousal_score >= 50`
  - or `meeting_critical=no` and `arousal_score >= 75`
- `GREEN`:
  - all other cases

## 3) Protocol actions

### GREEN

- Finish current task.
- Set one alarm.
- No extra intervention required.

### YELLOW

- Stop feature coding in 30 minutes.
- Run 15-minute cooldown:
  - write shutdown notes,
  - remove active stimuli,
  - no new architecture decisions.
- Set two alarms.

### RED

- Immediate coding stop.
- Execute 25-minute hard cooldown:
  - close IDE and communication apps,
  - warm shower or breathing routine,
  - no caffeine.
- Set two alarms + one backup notification path.
- Send pre-commitment message to trusted contact if available.

## 4) Incident recovery protocol

If meeting is missed:

1. Respond immediately once aware.
2. Use fact-first ownership format:
   - what happened
   - responsibility
   - apology
   - recovery options
   - acceptance of any decision
3. No defensive context in first message.
4. Deliver follow-up artifact (one-page brief or agenda) before rescheduled call.

Disallowed wording in first response:

- "please understand"
- "because I was ..."
- "it was not my fault"
- any self-justifying sentence that shifts focus from impact to excuses

## 5) Automation expansion (post-MVP)

After manual workflow is stable:

1. Replace manual `arousal_score` with wearable signals:
   - resting heart rate deviation,
   - HRV trend,
   - sleep debt.
2. Add event ingestion from calendar.
3. Add optional delivery automation (for example caffeine timing) with safety constraints.

## 6) Non-goals

- This protocol does not diagnose medical conditions.
- This protocol does not replace professional healthcare.
