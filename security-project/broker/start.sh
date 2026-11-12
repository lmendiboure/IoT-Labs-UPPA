#!/bin/sh
set -eu
umask 022
mosquitto_passwd -b -c /tmp/lab-users sensor sensor-demo
mosquitto_passwd -b /tmp/lab-users quality quality-demo
mosquitto_passwd -b /tmp/lab-users gateway gateway-demo
mosquitto_passwd -b /tmp/lab-users auditor auditor-demo
# mosquitto_passwd creates this file as root, while the broker drops to
# UID 1883 (mosquitto) before loading its password database.
# Keep the file private, but readable by the daemon.
chown mosquitto:mosquitto /tmp/lab-users
chmod 600 /tmp/lab-users
exec mosquitto -c /lab/mosquitto.conf
