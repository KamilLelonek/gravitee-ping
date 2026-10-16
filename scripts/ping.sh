#!/bin/sh
# Fails unless GET /ping through the gateway returns exactly "pong".
set -eu
cd "$(dirname "$0")/.."

body=$(curl --silent --show-error --fail --max-time 5 --cacert .certs/ca.crt https://localhost/ping)
if [ "$body" != "pong" ]; then
  printf "expected 'pong', got '%s'\n" "$body" >&2
  exit 1
fi
echo "$body"
