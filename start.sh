#!/usr/bin/env bash
# Single command to boot LC Trainer: sets up venv/deps/.env on first run,
# then starts the dev server.
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

echo "Starting LC Trainer at http://localhost:8000"
exec uvicorn app.main:app --reload
