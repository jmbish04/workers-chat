#!/bin/bash
# Wrapper to run the chatroom with the project's virtual environment

# Ensure we are in the project root
cd "$(dirname "$0")/.."

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "❌ Error: .venv not found. Please run 'uv sync' first."
    exit 1
fi

# Run the script with the requested arguments
./.venv/bin/python scripts/start_agent_chatroom.py "$@"
