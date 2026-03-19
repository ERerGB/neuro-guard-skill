#!/bin/bash
# watch-build.sh — Monitor Build macOS NeuroGuard workflow via Wander
# Run from neuro-guard-skill repo. Requires Wander (sibling or WANDER_HOME).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WANDER_DIR="${WANDER_HOME:-$(dirname "$REPO_ROOT")/wander}"

if [[ ! -f "$WANDER_DIR/watch-workflow-bg.sh" ]]; then
  echo "Wander not found at $WANDER_DIR"
  echo "Clone: git clone https://github.com/ERerGB/wander.git"
  echo "Or set WANDER_HOME=/path/to/wander"
  exit 1
fi

cd "$REPO_ROOT"
export WORKFLOW_REGISTRY_FILE="$REPO_ROOT/.workflows.yml"
exec "$WANDER_DIR/watch-workflow-bg.sh" build-macos.yml "$@"
