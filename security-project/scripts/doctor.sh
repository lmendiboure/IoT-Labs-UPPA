#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
command -v docker >/dev/null || { echo 'FAIL: docker missing' >&2; exit 1; }
docker compose version
printf '\nChecking Compose configuration...\n'
docker compose config -q
printf '\nStarting checks in the workstation...\n'
docker compose exec -T workstation python /diagnostics/test_security.py
printf '\nChecking actual traffic and web-to-OT behavior...\n'
MODE=$(cat control/mode.txt)
docker compose exec -T workstation python /diagnostics/smoke.py --expect "$MODE"
if [ "$MODE" = "vulnerable" ]; then
  docker compose exec -T workstation python /diagnostics/acl_probe.py --expect allowed
else
  docker compose exec -T workstation python /diagnostics/acl_probe.py --expect blocked
fi
