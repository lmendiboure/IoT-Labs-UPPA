#!/bin/sh
# Reinitialize transient broker credentials at EVERY start, including Compose restarts.
# Root is used only to prepare file permissions; Mosquitto drops privileges to its
# dedicated account before handling client traffic.
set -eu
if [ "$(id -u)" -ne 0 ]; then
  echo 'Broker bootstrap must run as root to prepare the password and ACL files.' >&2
  exit 1
fi
umask 077
rm -f /tmp/lab-users /tmp/lab-users.tmp /tmp/active.acl
mosquitto_passwd -b -c /tmp/lab-users sensor sensor-demo
mosquitto_passwd -b /tmp/lab-users quality quality-demo
mosquitto_passwd -b /tmp/lab-users gateway gateway-demo
mosquitto_passwd -b /tmp/lab-users auditor auditor-demo
chown mosquitto:mosquitto /tmp/lab-users
chmod 600 /tmp/lab-users
# The source ACL is a read-only host bind mount. Copy it to a private runtime
# file so the daemon can read it without the world-readable ACL warning.
cp /lab/active.acl /tmp/active.acl
chown mosquitto:mosquitto /tmp/active.acl
chmod 600 /tmp/active.acl
exec mosquitto -c /lab/mosquitto.conf
