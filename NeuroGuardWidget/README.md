# Neuro Guard Widget (macOS Notification Center)

WidgetKit extension that shows Neuro Guard status in the macOS Notification Center sidebar. Matches the web card layout (Matrix-style, tier colors, countdown, event info).

## Prerequisites

- macOS 14.0+
- Xcode 15+
- [XcodeGen](https://github.com/yonaskolb/XcodeGen) (optional): `brew install xcodegen`

## Build

### Option A: Using XcodeGen (recommended)

```bash
cd NeuroGuardWidget
xcodegen generate
open NeuroGuard.xcodeproj
```

Then in Xcode:
1. Select the **NeuroGuard** scheme
2. Product → Run (⌘R)

### Option B: Manual Xcode project

1. Create new project: File → New → Project → macOS → App → "NeuroGuard"
2. Add Widget Extension: File → New → Target → Widget Extension → "NeuroGuardWidget"
3. Add App Group `group.com.neuroguard.shared` to both targets (Signing & Capabilities)
4. Add the Swift files from `NeuroGuard/` and `NeuroGuardWidget/` to the respective targets
5. Set main app entitlements: disable App Sandbox (or add read access to home dir) so it can read `~/.neuro-guard-telemetry.json`

## Data flow

```
guard.py → ~/.neuro-guard-telemetry.json
    → NeuroGuard app (sync every 10s)
    → App Group container (telemetry.json)
    → Widget reads from App Group
```

## Usage

1. Run the Neuro Guard daemon (`guard.py`) so it writes telemetry to `~/.neuro-guard-telemetry.json`
2. Launch the NeuroGuard app (menu bar icon)
3. Click the date/time in the menu bar to open Notification Center
4. Click "Edit Widgets" and add the "Neuro Guard" widget

The widget shows tier, countdown, next critical event, and snooze status. Tapping it opens the full web view at http://127.0.0.1:9877/
