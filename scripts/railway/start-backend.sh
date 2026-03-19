#!/bin/sh
set -eu

PORT_TO_USE="${PORT:-8000}"
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT_TO_USE}"
