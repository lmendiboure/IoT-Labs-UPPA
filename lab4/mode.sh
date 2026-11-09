#!/bin/sh
set -eu
case "${1:-}" in
  raw|edge) mode="$1" ;;
  *) echo "Usage: ./mode.sh raw|edge" >&2; exit 2 ;;
esac
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# Atomic update. The forwarding container reads this file for each publication.
printf '%s\n' "$mode" > "$root/control/.mode.tmp"
mv "$root/control/.mode.tmp" "$root/control/mode.txt"
echo "Uplink forwarding mode: $mode (effective for NEW messages)"
