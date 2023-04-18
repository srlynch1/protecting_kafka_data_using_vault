#!/usr/bin/env python

import sys
from argparse import ArgumentParser, FileType
from configparser import ConfigParser
from confluent_kafka import Consumer, OFFSET_BEGINNING
from confluent_kafka import Producer
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

    # Create Consumer instance
    consumer = Consumer(config)

    # Set up a callback to handle the '--reset' flag.
    def reset_offset(consumer, partitions):
        if args.reset:
            for p in partitions:
                p.offset = OFFSET_BEGINNING
            consumer.assign(partitions)


    #load config for per-field endryption demo
    democonfig=dict(config_parser['encryptor'])

    # Subscribe to topic
    sourcetopic = democonfig['sourcetopic']
    targettopic = democonfig['targettopic']

    consumer.subscribe([sourcetopic], on_assign=reset_offset)
    producer = Producer(config)
    # Optional per-message delivery callback (triggered by poll() or flush())
    # when a message has been successfully delivered or permanently
    # failed delivery (after retries).
    def delivery_callback(err, msg):
        if err:
            print('ERROR: Message failed delivery: {}'.format(err))
        else:
            print("Produced event to topic {topic}: key = {key:12} value = {value:12}".format(
                topic=msg.topic(), key=msg.key().decode('utf-8'), value=msg.value().decode('utf-8')))

    # disable TLS verification
    urllib3.disable_warnings()

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
                original_payload= json.loads(msg.value().decode('utf-8'))
                # print(msg.value().decode('utf-8'))

                credit_card_encode_response = client.secrets.transform.encode(
                    role_name="payments",
                    value=original_payload["credit_card"],
                    transformation="creditcard")
                
                address = original_payload["Address"]
                address_bytes = address.encode('ascii')
                address_base64=base64.b64encode(address_bytes)

                address_encrypt_data_response = client.secrets.transit.encrypt_data(
                    name='transit',
                    plaintext=str(address_base64, "utf-8"),
                )
                
                encrypted_payload = {
                    "Name": original_payload["Name"],
                    "Address": address_encrypt_data_response['data']['ciphertext'],
                    "credit_card": credit_card_encode_response['data']['encoded_value']
                }

                print(json.dumps(encrypted_payload))

                producer.produce(targettopic, json.dumps(encrypted_payload))

                
    except KeyboardInterrupt:
        pass
    finally:
        # Leave group and commit final offsets
        consumer.close()

