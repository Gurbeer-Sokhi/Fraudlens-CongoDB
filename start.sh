#!/usr/bin/env bash
# Start FraudLens backend and frontend
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Starting FraudLens API..."
cd "$ROOT/backend"
source .venv/bin/activate 2>/dev/null || true
uvicorn app.main:app --reload --port 8000 &
API_PID=$!

sleep 2
echo "Starting FraudLens UI..."
cd "$ROOT/frontend"
npm run dev &
UI_PID=$!

echo ""
echo "API:  http://localhost:8000/docs"
echo "UI:   http://localhost:5173"
echo "Press Ctrl+C to stop"

trap "kill $API_PID $UI_PID 2>/dev/null" EXIT
wait
