provider "vault" {
  address = var.vault_address
  skip_tls_verify = true
}

resource "vault_mount" "transform" {
  path = "transform"
  type = "transform"
}

resource "vault_transform_role" "payments" {
  path = vault_mount.transform.path
  name = "payments"
  transformations = [ "creditcard" ]
}

resource "vault_transform_alphabet" "numerics" {
  path      = vault_mount.transform.path
  name      = "numerics"
  alphabet  = "0123456789"
}

resource "vault_transform_template" "ccn" {
  path           = vault_transform_alphabet.numerics.path
  name           = "ccn"
  type           = "regex"
  pattern        = "(\\d{4})[- ](\\d{4})[- ](\\d{4})[- ](\\d{4})"
  alphabet       = "numerics"
  encode_format  = "$1-$2-$3-$4"
  decode_formats = {
    "last-four-digits" = "$4"
  }
}

resource "vault_transform_transformation" "creditcard" {
  path          = vault_mount.transform.path
  name          = "creditcard"
  type          = "fpe"
  template      = "ccn"
  tweak_source  = "internal"
  allowed_roles = ["payments"]
}

resource "vault_mount" "transit" {
  path                      = "transit"
  type                      = "transit"
  description               = "Example description"
  default_lease_ttl_seconds = 3600
  max_lease_ttl_seconds     = 86400
}

resource "vault_transit_secret_backend_key" "key" {
  backend = vault_mount.transit.path
  name    = "my_key"
}