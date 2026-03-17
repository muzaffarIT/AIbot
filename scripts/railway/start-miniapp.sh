#!/bin/sh
set -eu

PORT_TO_USE="${PORT:-3000}"
cd miniapp
exec npm run start -- --hostname 0.0.0.0 --port "${PORT_TO_USE}"
