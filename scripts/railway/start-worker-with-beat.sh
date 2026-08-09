#!/usr/bin/env bash
# Start the Celery worker and the celery-beat scheduler together in one
# container, so the daily broadcasts actually fire on schedule.
#
# Why this exists: the previous startCommand ran `celery worker -B`, which
# embeds beat inside the worker. Embedded beat is documented as
# "NOT for production" — with --concurrency=4 and restarts it silently stops
# firing the schedule, which is exactly why no daily reminder went out. The
# robust fix is two real processes: a worker and a separate beat.
#
# Railway runs this from the service dir (/app/worker), so we cd to the
# repo root first — that's where the `worker` and `backend` packages live
# and where the existing `PYTHONPATH=..` startCommand assumed it was run from.

set -euo pipefail

cd "$(dirname "$0")/.."

export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"

echo "[start-worker] cwd=$(pwd) PYTHONPATH=$PYTHONPATH"
echo "[start-worker] launching celery beat (scheduler) in background..."
python -m celery -A worker.main.celery_app beat -l info \
  --schedule /tmp/celerybeat-schedule \
  --pidfile /tmp/celerybeat.pid \
  >> /tmp/celerybeat.log 2>&1 &
BEAT_PID=$!
echo "[start-worker] celery beat started (pid=$BEAT_PID)"

# Cleanup both processes on shutdown (Railway sends SIGTERM on redeploy).
cleanup() {
  echo "[start-worker] SIGTERM received, shutting down beat (pid=$BEAT_PID)..."
  kill "$BEAT_PID" 2>/dev/null || true
  wait "$BEAT_PID" 2>/dev/null || true
}
trap cleanup TERM INT

echo "[start-worker] launching celery worker (foreground)..."
# `exec` so the worker becomes PID 1 and Railway's signal reaches it directly.
exec python -m celery -A worker.main.celery_app worker -l info --concurrency=4

