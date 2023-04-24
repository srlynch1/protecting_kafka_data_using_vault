# Protecting data before sending to Kafka

## What is Kafka

Kafka is a distributed streaming platform that is used for building real-time data pipelines and streaming applications

It uses a publish-subscribe messaging model where data is produced by producers and consumed by consumers. Producers write data to Kafka topics, and consumers read data from those topics.

## Risk of data leaking

In order to make sure data is send to consumers , the data is cached at Kafka. This creates a risk of leaking. The risk is considered acceptable when Kafka Infrastructure runs on-prem. The risk increases when Kafka infrustructure runs on public cloud. It further incfreases when using a SaaS Kafka.

Ideally the team running Kafka should not be responsible for this risk, if the data going through has been encrypted before it is send to Kafka.

## Complications

So it is now Kafka producers and consume's responsiblity to encrypt and decrypt the data. This is not easy.

In order to do data encrypt and decrypt operations, applications need a shared Data Encryption Key, and once use only nonce or IV[https://www.oreilly.com/library/view/secure-programming-cookbook/0596003943/ch04s09.html] between encryptor and decryptor, if they are shared without protection, then data is at risk of leaking. Protection means many things, including frequent rotation and encryption in transit and at rest.

Encryption Arlgorism is also an important fact to consider. Providers and consumers need to share the same arlgorism and mode. Not all languages have mature encryption libraries accross all arlgorisms and modes. 

With those difficaulties and limitations, letting application do encryption and decryption by themselves is costly in the long run.

## Solutions

Vault transit secret engine can be considered an Encryption as a Service that is easily accessible via API calls. Vault client can send plaintext to end point for encryption, or ciphertext for decryption, without the need to access the DEK or encryption arlgorism and mode.

## demo setup

### setup confluent

### setup Python enviroment

## demo cases

### Demo1, Confluent admin can see messages on topic

### Demo2, Contents can be encryopted

### Demo3, large contents
