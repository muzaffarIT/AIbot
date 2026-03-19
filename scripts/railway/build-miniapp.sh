#!/bin/sh
set -eu

cd miniapp
npm ci
npm run build
