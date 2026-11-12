#!/bin/sh
set -eu
umask 022
mosquitto_passwd -b -c /tmp/lab-users sensor sensor-demo
mosquitto_passwd -b /tmp/lab-users quality quality-demo
mosquitto_passwd -b /tmp/lab-users gateway gateway-demo
mosquitto_passwd -b /tmp/lab-users auditor auditor-demo
exec mosquitto -c /lab/mosquitto.conf
