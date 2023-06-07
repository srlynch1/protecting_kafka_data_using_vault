# Protecting data before sending to Kafka

## What is Kafka

Kafka is a distributed streaming platform that is used for building real-time data pipelines and streaming applications

It uses a publish-subscribe messaging model where data is produced by producers and consumed by consumers. Producers write data to Kafka topics, and consumers read data from those topics.

## Risk of data leaking

In order to make sure data is sent to consumers , the data is cached at Kafka. This creates a risk of leaking. The risk is considered acceptable when Kafka infrastructure runs on-premises. The risk increases when Kafka infrustructure runs on public cloud. It further increases when using a SaaS Kafka.

Ideally the team running the Kafka platform should not be responsible for this risk. Instead, producers shoud be encouraged to encrypt data before it is sent to Kafka.

## Complications

So it is now Kafka producers and consumers responsiblity to encrypt and decrypt the data. This is not easy.

In order to do data encrypt and decrypt operations, applications need a shared Data Encryption Key, and single use only [nonce or IV](https://www.oreilly.com/library/view/secure-programming-cookbook/0596003943/ch04s09.html) between encryptor and decryptor, if they are shared without protection, then data is at risk of leaking. Protection means many things, including frequent rotation and encryption in transit and at rest.

The Encryption Algorithm is also an important factor to consider. Producers and consumers need to share the same arlgorithm and mode. Not all languages have mature encryption libraries accross all arlgorisms and modes.

With those difficulties and limitations, letting application teams do encryption and decryption by themselves is costly in the long run.

## Solutions

HashiCorp Vault supports many ways of encryption, including [Transit](https://developer.hashicorp.com/vault/docs/secrets/transit), [Format Preserving Encryption](https://developer.hashicorp.com/vault/docs/secrets/transform#format-preserving-encryption), and [Tokenisation](https://developer.hashicorp.com/vault/docs/secrets/transform#tokenization). Each one is suited for different use cases.

Vault transit secret engine can be considered a general purpose Encryption as a Service that is easily accessible via API calls. Applications can send plaintext data to a Vault end point for encryption, or ciphertext for decryption, without the need to access the DEK or encryption arlgorithm and mode.

Format Preserving Encryption operates in a similar fashion and is designed to encrypt the data while keeping data format intact.

## demo setup
The demo code that follows allows you to setup Kafka Producers using Vault for Encryption as a Service. The examples provided show both transit encrption and format preserving encrption and demonstrate that without much trouble applications teams can leverage Vault as their EaaS provider consistently on any cloud, or with any platform.


### pre-requisites
* Vault Enterprise with ADP license

### setup confluent

Go to [confluent](https://confluent.cloud/) and sign-up a free account. During the registraiton process, make sure select "developer" as your job role. Developers get access to free trial without exipry as long as only one Kafka cluster is used.

Once logged in, create a Cloud API key with global access, and setup enviroment variables:

```bash
export CONFLUENT_CLOUD_API_SECRET=<your secret>
export CONFLUENT_CLOUD_API_KEY=<your key>
```

Get into the terraform subdirectory and do the terraform dance:

```bash
terraform init
terraform plan
terraform apply 
```

The terraform code will setup the confluent enviroment/cluster/topics that are necessary for the demo.

You can find the cluster URL from confluent_kafka_cluster.demo resource, and API key and secret from confluent_api_key.app-manager-kafka-api-key. You need those information later.

### setup Python enviroment

[Install python3, pip and virtual enviroment manager](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/), then setup all dependencies:

```bash
python3 -m pip install -r requirements.txt
```

### setup demos

Rename getting_started.ini.orig to getting_started.ini and update the URL to Kafka cluster, API key and API secrets.

## Demo cases

### demo 1, Confluent admin can see messages on topic

Login to (confluent.cloud), open the 'purchase' topic, and click 'messages' tab to view messages on the topic.

Run producer.py in a terminal to generate some traffic, message should appear in the browser. This is to show that the contents of the payload is visible to admins.

`python3 producer.py`

### demo 2, content can be encrypted

* Open the 'purchases_encrypted' topic and select 'messages' tab to observ messages.
In confluent cloud this is under > Environments > Developement > BASIC_DEMO_KAFKA_CLUSTER

* Update encryptor.py script, line 61 with your vault address and token

`client = hvac.Client(url='https://nginx', token='s.sxns9tOHTlbY9E0ECc5beMhY', verify=False)`

* Run encryptor.py in a terminal `python3 encryptor.py` .pyto consume messages from 'purchases' topic, encrypt, then send to 'purchases_encrypted' topic. Encrypted messages should apprear in the browser. This is to show that Vault can be used to do per-field encryption.

* Login to Vault, and rotate the transit encryption key.

Run producer.py in another terminal and observe that the encrypted messages would use the new version automatically.

Run consumer_from_encrypted.py in another terminal and observe that it can consume messages, decrypt, then print to the terminal. You would observe even though the encrypted messages were encrypted by two different versions, the consumer can still decrypt without difficulty.

You would also observe that the credit card numbers have been encrypted while preserving their formats. This enables complex logic between different topics.

### demo 3, large payload

In the last two demo cases, all payloads are sent to Vault for both encryption and decryption operations. In the case of large payloads, this is not nessisarily the best way - large payloads increases network traffic and cause delays between producer and consumers, this also creates lots of CPU intensive operations on Vault nodes, putting presure on the centralised Vault platform. 

Doing encryption/decryption operations at the application node using Data Encryption Key generated by Vault can avoid expensive network and CPU operations. To ensure security, every operation will have a new DEK, which is also encrypted/transfered with the encrypted payload, only client with right authentication/authorization is able to decrypt the DEK, then use it to decrypt the payload.

Open 'purchases_large_encrypted' topic and observ messages.

Run consumer_file_transfer.py from one terminal.

Create two folders with name 'source' and 'destination', then copy some files into source directory.

Run producer_file_transfer.py to scan files in source folder, generate one use only DEK, encryupt the file contents locally, then send to 'purchases_large_encrypted' topic.

The consumer will consume the message, get encrypted DEK from http header, call vault to decrypt the DEK, then decrypt the file contents locally, then save it into destination folder.

In the browser, you should be able to see encrypted messages, encrypted DEK as http header as well as the filename as http header.

## Beyond Kafka

Kafka is one of the most popular streaming platform, but it is not the only one. The concept demostrated here is applicable to any streaming platform, including [AWS Kinesis](https://aws.amazon.com/kinesis/), [AWS SQS](https://aws.amazon.com/sqs/), [AWS SNS](https://aws.amazon.com/sns/), [Google Cloud Pub/Sub](https://cloud.google.com/pubsub), [Microsoft Azure Event Hubs](https://azure.microsoft.com/en-us/products/event-hubs/) as well as  [Apache Spark Streaming](https://www.databricks.com/glossary/what-is-spark-streaming).
