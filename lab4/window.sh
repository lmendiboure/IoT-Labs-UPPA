#!/bin/sh
set -eu
case "${1:-}" in
  5|10|20) n="$1" ;;
  *) echo "Usage: ./window.sh 5|10|20" >&2; exit 2 ;;
esac
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
printf '%s\n' "$n" > "$root/control/.window.tmp"
mv "$root/control/.window.tmp" "$root/control/window_size.txt"
echo "Edge summary window for NEW runs: $n samples"
