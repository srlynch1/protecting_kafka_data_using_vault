#!/usr/bin/env python

import sys
from argparse import ArgumentParser, FileType
from configparser import ConfigParser
from confluent_kafka import Consumer, OFFSET_BEGINNING
import hvac
import urllib3
import json
import base64
from Crypto.Cipher import AES


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
    democonfig=dict(config_parser['large_payload'])

    # Create Consumer instance
    consumer = Consumer(config)

    # Define the path of the directory that contains the source files
    dest_dir = democonfig['destinationdir'] + "/"

    # Set up a callback to handle the '--reset' flag.
    def reset_offset(consumer, partitions):
        if args.reset:
            for p in partitions:
                p.offset = OFFSET_BEGINNING
            consumer.assign(partitions)

    # Subscribe to topic
    topic = democonfig['topic']
    consumer.subscribe([topic], on_assign=reset_offset)

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

                # get encrypted payload and corresponding headers from the topic,
                encrypted_payload= json.loads(msg.value().decode('utf-8'))
                headers=dict(msg.headers())
                print('Data Encryption Key from header: {encryptionkey}'.format(encryptionkey = headers['X-encryptionkey'].decode("utf-8")))
                # decrypt the encryption key using vault transit
                encryptionkey=client.secrets.transit.decrypt_data(name='transit',ciphertext=headers['X-encryptionkey'].decode("utf-8"))['data']['plaintext']
                print('Data Encryption Key after decryption from Vault: {encryptionkey}'.format(encryptionkey=encryptionkey))
                
                # #file contents
                # print(encrypted_payload['ciphertext'])

                #Initiate a new AES decryptor using the data encryption key from header and nonce from payload 
                cipher = AES.new(base64.b64decode(encryptionkey), AES.MODE_GCM,base64.b64decode(encrypted_payload['nonce']))
                
                # Debug code
                # print(base64.b64decode(encrypted_payload['ciphertext']))
                # print(base64.b64decode(encrypted_payload['tag']))
                
                # Decrypt the ciphertext and verify the tag
                plaintext = cipher.decrypt_and_verify(bytes.fromhex(encrypted_payload['ciphertext']), bytes.fromhex(encrypted_payload['tag']))
                
                # Debug code
                # print('decrypted contents in base64: {plaintext}'.format(plaintext=plaintext))
                # print('decrypted contents in plaintext: {plaintext}'.format(plaintext=base64.b64decode(plaintext)))      

                #write contents into file, previx filename with 'receved-':
                with open(dest_dir+'received-'+headers['X-filename'].decode("utf-8"), 'wb') as f:
                # Write the bytes data to the file
                    f.write(base64.b64decode(plaintext))
 
    except KeyboardInterrupt:
        pass
    finally:
        # Leave group and commit final offsets
        consumer.close()
