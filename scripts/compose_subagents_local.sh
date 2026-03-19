#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-dry-run}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HARNESS_DIR="${HARNESS_DIR:-/Users/j.z/code/subagent-harness}"
HARNESS_CLI="$HARNESS_DIR/dist/cli.js"
SRC_DIR="$ROOT_DIR/agents/archetypes"
CURSOR_DST="${CURSOR_DST:-$HOME/.cursor/agents}"
CLAUDE_DST="${CLAUDE_DST:-$HOME/.claude/agents}"
CONFIG_FILE="$ROOT_DIR/subagent.config.json"

if [[ ! -d "$HARNESS_DIR" ]]; then
  echo "subagent-harness not found: $HARNESS_DIR" >&2
  exit 1
fi
if [[ ! -f "$HARNESS_CLI" ]]; then
  echo "subagent-harness CLI not found: $HARNESS_CLI" >&2
  echo "Run: (cd $HARNESS_DIR && pnpm install && pnpm build)" >&2
  exit 1
fi

if [[ "$MODE" != "dry-run" && "$MODE" != "apply" && "$MODE" != "clean" ]]; then
  echo "Usage: $0 [dry-run|apply|clean]" >&2
  exit 2
fi

cat > "$CONFIG_FILE" <<EOF
{
  "src": "$SRC_DIR",
  "pattern": "*.agent.md",
  "targets": [
    { "runtime": "cursor", "dst": "$CURSOR_DST" },
    { "runtime": "claude-code", "dst": "$CLAUDE_DST" }
  ]
}
EOF

cleanup() {
  rm -f "$CONFIG_FILE"
}
trap cleanup EXIT

cd "$ROOT_DIR"
node "$HARNESS_CLI" "--$MODE"

echo "Done. mode=$MODE"
