#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
cp broker/acl.vulnerable broker/active.acl
printf 'vulnerable\n' > control/mode.txt
docker compose down --remove-orphans
rm -f captures/mqtt.pcap
printf 'Reset complete. docker compose up -d --build\n'
