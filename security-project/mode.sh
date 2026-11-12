#!/bin/sh
set -eu
cd "$(dirname "$0")"
case "${1:-}" in
  vulnerable|hardened) ;;
  *) echo 'Usage: ./mode.sh vulnerable|hardened' >&2; exit 2 ;;
esac
cp "broker/acl.$1" broker/active.acl
printf '%s\n' "$1" > control/mode.txt
docker compose restart broker gateway
printf 'Now: %s. Check service with docker compose exec workstation python /diagnostics/smoke.py --expect %s\n' "$1" "$1"
