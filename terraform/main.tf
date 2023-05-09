# Configure the Confluent Provider
terraform {
  required_providers {
    confluent = {
      source  = "confluentinc/confluent"
      version = "1.39.0"
    }
  }
}

provider "confluent" {
  # cloud_api_key    = var.confluent_cloud_api_key    # optionally use CONFLUENT_CLOUD_API_KEY env var
  # cloud_api_secret = var.confluent_cloud_api_secret # optionally use CONFLUENT_CLOUD_API_SECRET env var
}

resource "confluent_environment" "development" {
  display_name = "Development"

  lifecycle {
    prevent_destroy = true
  }
}

resource "confluent_kafka_cluster" "demo" {
  display_name = "basic__demo_kafka_cluster"
  availability = "SINGLE_ZONE"
  cloud        = "GCP"
  region       = "australia-southeast1"
  basic {}

  environment {
    id = confluent_environment.development.id
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "confluent_service_account" "app-manager" {
  display_name = "app-manager"
  description  = "Service account to manage Kafka cluster"
}

resource "confluent_role_binding" "app-manager-kafka-cluster-admin" {
  principal   = "User:${confluent_service_account.app-manager.id}"
  role_name   = "CloudClusterAdmin"
  crn_pattern = confluent_kafka_cluster.demo.rbac_crn
}

resource "confluent_api_key" "app-manager-kafka-api-key" {
  display_name = "app-manager-kafka-api-key"
  description  = "Kafka API Key that is owned by 'app-manager' service account"
  owner {
    id          = confluent_service_account.app-manager.id
    api_version = confluent_service_account.app-manager.api_version
    kind        = confluent_service_account.app-manager.kind
  }

  managed_resource {
    id          = confluent_kafka_cluster.demo.id
    api_version = confluent_kafka_cluster.demo.api_version
    kind        = confluent_kafka_cluster.demo.kind

    environment {
      id = confluent_environment.development.id
    }
  }

  # lifecycle {
  #   prevent_destroy = true
  # }
}



resource "confluent_kafka_topic" "purchases" {

  kafka_cluster {
    id = confluent_kafka_cluster.demo.id
  }
  topic_name    = "purchases"
  partitions_count   = 1
  rest_endpoint = confluent_kafka_cluster.demo.rest_endpoint
  credentials {
    key    = confluent_api_key.app-manager-kafka-api-key.id
    secret = confluent_api_key.app-manager-kafka-api-key.secret
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "confluent_kafka_topic" "purchases_encrypted" {

  kafka_cluster {
    id = confluent_kafka_cluster.demo.id
  }
  topic_name    = "purchases_encrypted"
  partitions_count   = 1
  rest_endpoint = confluent_kafka_cluster.demo.rest_endpoint
  credentials {
    key    = confluent_api_key.app-manager-kafka-api-key.id
    secret = confluent_api_key.app-manager-kafka-api-key.secret
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "confluent_kafka_topic" "purchases_large_encrypted" {

  kafka_cluster {
    id = confluent_kafka_cluster.demo.id
  }
  topic_name    = "purchases_large_encrypted"
  partitions_count   = 1
  rest_endpoint = confluent_kafka_cluster.demo.rest_endpoint

  config = {
    "max.message.bytes"                   = "8388608"
  }


  credentials {
    key    = confluent_api_key.app-manager-kafka-api-key.id
    secret = confluent_api_key.app-manager-kafka-api-key.secret
  }

  lifecycle {
    prevent_destroy = true
  }
}