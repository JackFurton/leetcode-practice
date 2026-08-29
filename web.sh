#!/usr/bin/env bash
# Web mode: sets up venv/deps/.env on first run, starts the dev server,
# waits for it to be ready, opens Chrome. For the terminal-only mode, use
# ./start.sh instead.
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

uvicorn app.main:app --reload &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null' EXIT

echo "Waiting for server (first run seeds the problem catalog, can take ~30s)..."
for i in $(seq 1 60); do
  if curl -s -o /dev/null http://localhost:8000/; then
    break
  fi
  sleep 1
done

open -a "Google Chrome" http://localhost:8000 2>/dev/null || open http://localhost:8000 2>/dev/null || true

wait $SERVER_PID
