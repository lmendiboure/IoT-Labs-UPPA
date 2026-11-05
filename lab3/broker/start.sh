#!/bin/sh
set -eu
# Training-only identities. Credentials are deliberately public in this lab.
# Do not use them outside this isolated demonstration.
umask 022
mosquitto_passwd -c -b /tmp/lab3-passwords ac1 ac1-demo
mosquitto_passwd -b /tmp/lab3-passwords quality quality-demo
mosquitto_passwd -b /tmp/lab3-passwords visitor visitor-demo
mosquitto_passwd -b /tmp/lab3-passwords maintenance maintenance-demo
chmod 644 /tmp/lab3-passwords
exec mosquitto -c /mosquitto/config/active.conf
