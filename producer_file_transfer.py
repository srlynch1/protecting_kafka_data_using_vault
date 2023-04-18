#!/usr/bin/env python

import sys
import random
import json
from random import choice
from argparse import ArgumentParser, FileType
from configparser import ConfigParser
from confluent_kafka import Producer
import hvac
import urllib3
import base64
from Crypto.Cipher import AES
import os

if __name__ == '__main__':
    # Parse the command line.
    parser = ArgumentParser()
    parser.add_argument('--config_file', type=FileType('r'), default='getting_started.ini')
    args = parser.parse_args()

    # Parse the configuration.
    # See https://github.com/edenhill/librdkafka/blob/master/CONFIGURATION.md
    config_parser = ConfigParser()
    config_parser.read_file(args.config_file)
    config = dict(config_parser['default'])

    democonfig=dict(config_parser['large_payload'])

    # Create Producer instance
    producer = Producer(config)

    # Produce data by selecting random values from these lists.
    topic = democonfig['topic']

    # disable TLS verification
    urllib3.disable_warnings()

    # create a client object and authenticate to the Vault server using a token
    client = hvac.Client(url='https://nginx', token='s.sxns9tOHTlbY9E0ECc5beMhY', verify=False)

    # Define the path of the directory that contains the source files
    source_dir = democonfig['sourcedir'] + "/"

    # Loop through all files in the directory
    for filename in os.listdir(source_dir):
        # Check if the file is a regular file (not a directory)
        if os.path.isfile(os.path.join(source_dir, filename)):
            # Open the file and read its contents
            with open(os.path.join(source_dir, filename), 'rb') as f:
                file_contents = f.read()
            #encode file contents into base64
            file_contents_base64= base64.b64encode(file_contents)

            # get datakey from transit
            gen_key_response = client.secrets.transit.generate_data_key(
            name='transit',
            key_type='plaintext',
            )
            ciphertext = gen_key_response['data']['ciphertext']
            plaintext= gen_key_response['data']['plaintext']
            print('Generated data key ciphertext is: {cipher}'.format(cipher=ciphertext))
            # print('Generated data key plaintext is: {plaintext}'.format(plaintext=plaintext))

            #get nonce from transit
            gen_bytes_response = client.secrets.transit.generate_random_bytes(n_bytes=32)
            nonce = gen_bytes_response['data']['random_bytes']

            print('Generated nonce for encryption operation is: {nonce}'.format(nonce=nonce))

            #initiate a new AES encryptor with key and nonce from Vault, encrypt file contents.
            encryptor = AES.new(base64.b64decode(plaintext), AES.MODE_GCM,base64.b64decode(nonce))
            encrypted_contents,tag = encryptor.encrypt_and_digest(file_contents_base64)

            # Pack the encrypted data and the tag into a JSON object
            data = json.dumps({
                'ciphertext': encrypted_contents.hex(),
                'tag': tag.hex(),
                'nonce': nonce,
            })

            # Pack the ciphertext of the key and filename into HTTP headers. As the key has been encrypted by Vault, it can't be used without decryption.
            headers = [
                ('X-encryptionkey', ciphertext),
                ('X-filename',filename),
            ]

            #Produce a kafka msg to the topic
            producer.produce(topic, value=data.encode('utf-8'), headers=headers )


    # filename="82E91B88-92DE-49F7-B5AC-4406354FCA7A_1_102_o.jpeg"

    # with open(filename, "rb") as f:
    #     file_contents=f.read()
    
    # # print('file contents: {file_contents}.'.format(file_contents=file_contents))

    # #encode file contents into base64
    # file_contents_base64= base64.b64encode(file_contents)

    # # print('file contents in base 64: {file_contents_base64}.'.format(file_contents_base64=file_contents_base64))

    # #initiate a new AES encryptor with key and nonce from Vault, encrypt file contents.
    # encryptor = AES.new(base64.b64decode(plaintext), AES.MODE_GCM,base64.b64decode(nonce))
    # encrypted_contents,tag = encryptor.encrypt_and_digest(file_contents_base64)

    # # Pack the encrypted data and the tag into a JSON object
    # data = json.dumps({
    #     'ciphertext': encrypted_contents.hex(),
    #     'tag': tag.hex(),
    #     'nonce': nonce,
    # })

    # # Pack the ciphertext of the key and filename into HTTP headers. As the key has been encrypted by Vault, it can't be used without decryption.
    # headers = [
    #     ('X-encryptionkey', ciphertext),
    #     ('X-filename',filename),
    # ]
    # # debug code
    # # decryptor  = AES.new(base64.b64decode(plaintext), AES.MODE_GCM,base64.b64decode(nonce))
    # # decrypted_contents = decryptor.decrypt(encrypted_contents)
    # # print('decrypted file contents in base 64: {decrypted_contents}.'.format(decrypted_contents=decrypted_contents))
    # # print('decrypted file contents in original: {decrypted_contents}.'.format(decrypted_contents=base64.b64decode(decrypted_contents)))

    # producer.produce(topic, value=data.encode('utf-8'), headers=headers )

    # Block until the messages are sent.
    producer.poll(10000)
    producer.flush()
