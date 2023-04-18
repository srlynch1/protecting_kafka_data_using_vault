#!/usr/bin/env python

import sys
from argparse import ArgumentParser, FileType
from configparser import ConfigParser
from confluent_kafka import Consumer, OFFSET_BEGINNING
import hvac
import urllib3
import json
import base64

if __name__ == '__main__':
    # Parse the command line.
    parser = ArgumentParser()
    parser.add_argument('--config_file', type=FileType('r'), default='getting_started.ini')
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()

    # Parse the configuration.
    # See https://github.com/edenhill/librdkafka/blob/master/CONFIGURATION.md
    config_parser = ConfigParser()
    config_parser.read_file(args.config_file)
    config = dict(config_parser['default'])
    config.update(config_parser['consumer'])

    #load config for per-field endryption demo
    democonfig=dict(config_parser['encryptor'])

    # Create Consumer instance
    consumer = Consumer(config)

    # Set up a callback to handle the '--reset' flag.
    def reset_offset(consumer, partitions):
        if args.reset:
            for p in partitions:
                p.offset = OFFSET_BEGINNING
            consumer.assign(partitions)

    # Subscribe to topic
    topic = democonfig['targettopic']
    consumer.subscribe([topic], on_assign=reset_offset)

    # disable TLS verification
    urllib3.disable_warnings()
    print("kafka topic set to {topic}".format(topic=topic))
    # create a client object and authenticate to the Vault server using a token
    client = hvac.Client(url='https://nginx', token='s.sxns9tOHTlbY9E0ECc5beMhY', verify=False)

    # Poll for new messages from Kafka and print them.
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                # Initial message consumption may take up to
                # `session.timeout.ms` for the consumer group to
                # rebalance and start consuming
                print("Waiting...")
            elif msg.error():
                print("ERROR: %s".format(msg.error()))
            else:

                # Extract the (optional) key and value, and print.
                encrypted_payload= json.loads(msg.value().decode('utf-8'))
                # print(msg.value().decode('utf-8'))

                credit_card_decode_response = client.secrets.transform.decode(
                    role_name="payments",
                    value=encrypted_payload["credit_card"],
                    transformation="creditcard")
                
                address = encrypted_payload["Address"]

                address_decrypt_data_response = client.secrets.transit.decrypt_data(
                    name='transit',
                    ciphertext=address,
                )
                
                decrypted_payload = {
                    "Name": encrypted_payload["Name"],
                    "Address": base64.b64decode(str(address_decrypt_data_response['data']['plaintext'])).decode("utf-8"),
                    "credit_card": credit_card_decode_response['data']['decoded_value']
                }

                print(json.dumps(decrypted_payload))

    except KeyboardInterrupt:
        pass
    finally:
        # Leave group and commit final offsets
        consumer.close()
