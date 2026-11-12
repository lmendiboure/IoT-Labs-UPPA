#!/bin/sh
# Instructor / VM acceptance: actual services and MQTT flows, not unit mocks.
set -eu
cd "$(dirname "$0")/.."
echo 'Checking Compose and building the isolated teaching stack...'
docker compose config -q
docker compose up -d --build
for scenario in vulnerable hardened vulnerable; do
  echo "=== Validating $scenario with real MQTT and HTTP ==="
  ./mode.sh "$scenario"
  ./scripts/doctor.sh
done
echo 'PASS: IT/OT cyber stack validated in vulnerable and hardened modes on this VM.'
echo 'Next: capture one test exchange and inspect the generated PCAP if packet analysis is needed.'
