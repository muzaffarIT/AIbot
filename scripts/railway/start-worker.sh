#!/bin/sh
set -eu

exec python -m celery -A worker.main.celery_app worker -l info
