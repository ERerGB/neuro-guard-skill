#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
if command -v xcodegen &>/dev/null; then
  xcodegen generate
  echo "Generated NeuroGuard.xcodeproj. Open with: open NeuroGuard.xcodeproj"
else
  echo "XcodeGen not found. Install with: brew install xcodegen"
  echo "Or follow manual steps in README.md"
  exit 1
fi
