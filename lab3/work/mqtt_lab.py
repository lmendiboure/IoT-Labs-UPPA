"""Common CLI utilities used by the Lab 3 client scripts (not a security mechanism)."""
import argparse
import ssl

import paho.mqtt.client as mqtt

USERS = {
    'ac1': 'ac1-demo',
    'quality': 'quality-demo',
    'visitor': 'visitor-demo',
    'maintenance': 'maintenance-demo',
}

def connection_args(parser):
    parser.add_argument('--user', default='visitor', choices=sorted(USERS))
    parser.add_argument('--anonymous', action='store_true', help='do not send username or password')
    parser.add_argument('--wrong-password', action='store_true')
    parser.add_argument('--tls', action='store_true', help='connect to broker:8883 using the demo CA')
    return parser

def new_client(client_id, args, *, mqtt5=True):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id,
                         protocol=mqtt.MQTTv5 if mqtt5 else mqtt.MQTTv311)
    if not args.anonymous:
        pw = 'incorrect' if args.wrong_password else USERS[args.user]
        client.username_pw_set(args.user, pw)
    if args.tls:
        client.tls_set(ca_certs='/work/ca.crt', cert_reqs=ssl.CERT_REQUIRED,
                       tls_version=ssl.PROTOCOL_TLS_CLIENT)
        # Never disable check_hostname or accept self-signed server certs without a trusted CA.
    return client

def target(args):
    return ('broker', 8883) if args.tls else ('relay', 1884)
