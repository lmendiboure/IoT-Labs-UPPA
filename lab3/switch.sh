#!/bin/sh
set -eu
cd "$(dirname "$0")"
case "${1:-}" in
  open) source=00-open.conf ;;
  auth) source=01-auth.conf ;;
  acl) source=02-acl.conf ;;
  tls) source=03-tls.conf ;;
  tls-only) source=04-tls-only.conf ;;
  *) echo "Usage: ./switch.sh open|auth|acl|tls|tls-only" >&2; exit 2 ;;
esac
# Copy content into the bind-mounted file, retaining the same inode.
cat "broker/profiles/$source" > broker/active.conf
printf 'Broker profile: %s\n' "$1"
docker compose restart broker
printf 'The broker was restarted. Reconnect fresh clients before interpreting a trace.\n'
