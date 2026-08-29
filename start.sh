#!/usr/bin/env bash
# Terminal mode: sets up venv/deps/.env on first run, then launches the
# TUI directly in this terminal. No browser, no server to babysit. For the
# web UI instead, use ./web.sh.
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "Creating virtualenv..."
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example, edit it if your key file lives elsewhere."
fi

python3 -m app.tui
