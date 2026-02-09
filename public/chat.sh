#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "❌ Error: python3 is required to run the chat client."
  exit 1
fi

if [ $# -lt 1 ] || [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  echo "Usage: $0 \"Agent Name\" [--room ROOM] [--url BASE_URL]"
  echo "Example: $0 \"Investigator-Unit-01\" --room incident-bridge"
  exit 1
fi

"$PYTHON_BIN" "$SCRIPT_DIR/start_agent_chatroom.py" "$@"
