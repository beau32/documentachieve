// Terraform template for GCP Document Archive with Cloud Storage

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment tag"
  type        = string
  default     = "dev"
}

variable "bucket_name" {
  description = "GCS bucket name"
  type        = string
  default     = "document-archive"
}

variable "create_iceberg_warehouse" {
  description = "Create bucket for Iceberg warehouse"
  type        = bool
  default     = false
}

# Primary bucket for documents
resource "google_storage_bucket" "document_archive" {
  project       = var.project_id
  name          = "${var.bucket_name}-${var.project_id}"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.bucket_key.id
  }

  lifecycle_rule {
    # Standard → Nearline after 30 days
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age = 30
    }
  }

  lifecycle_rule {
    # Nearline → Coldline after 90 days
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
    condition {
      age = 90
    }
  }

  lifecycle_rule {
    # Coldline → Archive after 365 days
    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
    condition {
      age = 365
    }
  }

  lifecycle_rule {
    # Delete old versions after 180 days
    action {
      type = "Delete"
    }
    condition {
      is_live            = false
      age                = 180
      num_newer_versions = 0
    }
  }

  labels = {
    application = "document-archive"
    environment = var.environment
  }
}

# Optional Iceberg warehouse bucket
resource "google_storage_bucket" "iceberg_warehouse" {
  count         = var.create_iceberg_warehouse ? 1 : 0
  project       = var.project_id
  name          = "${var.bucket_name}-iceberg-warehouse-${var.project_id}"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.bucket_key.id
  }

  lifecycle_rule {
    # Clean up old Iceberg metadata after 30 days
    action {
      type = "Delete"
    }
    condition {
      is_live              = false
      age                  = 30
      num_newer_versions   = 0
    }
  }

  labels = {
    application = "iceberg-warehouse"
    environment = var.environment
  }
}

# KMS Key for encryption
resource "google_kms_key_ring" "bucket_key_ring" {
  project  = var.project_id
  name     = "document-archive-keyring"
  location = var.region
}

resource "google_kms_crypto_key" "bucket_key" {
  name            = "document-archive-key"
  key_ring        = google_kms_key_ring.bucket_key_ring.id
  rotation_period = "7776000s"  # 90 days
}

# Service Account for app access
resource "google_service_account" "document_archive" {
  project     = var.project_id
  account_id  = "document-archive-sa"
  description = "Service account for Document Archive application"
}

# IAM role binding - Storage Object Admin on document bucket
resource "google_storage_bucket_iam_member" "archive_bucket_admin" {
  bucket = google_storage_bucket.document_archive.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.document_archive.email}"
}

# IAM role binding - Storage Object Admin on Iceberg bucket (if created)
resource "google_storage_bucket_iam_member" "iceberg_bucket_admin" {
  count  = var.create_iceberg_warehouse ? 1 : 0
  bucket = google_storage_bucket.iceberg_warehouse[0].name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.document_archive.email}"
}

# IAM role binding - KMS user
resource "google_kms_crypto_key_iam_member" "sa_crypto_key_user" {
  crypto_key_id = google_kms_crypto_key.bucket_key.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${google_service_account.document_archive.email}"
}

# Service Account Key (optional - for local development)
resource "google_service_account_key" "document_archive_key" {
  service_account_id = google_service_account.document_archive.name
  public_key_type    = "TYPE_X509_PEM_FILE"
}

# Outputs
output "document_archive_bucket" {
  value       = google_storage_bucket.document_archive.name
  description = "Name of the document archive bucket"
}

output "document_archive_bucket_url" {
  value       = "gs://${google_storage_bucket.document_archive.name}"
  description = "GCS URL for document archive bucket"
}

output "iceberg_warehouse_bucket" {
  value       = var.create_iceberg_warehouse ? google_storage_bucket.iceberg_warehouse[0].name : ""
  description = "Name of the Iceberg warehouse bucket (if created)"
}

output "iceberg_warehouse_bucket_url" {
  value       = var.create_iceberg_warehouse ? "gs://${google_storage_bucket.iceberg_warehouse[0].name}" : ""
  description = "GCS URL for Iceberg warehouse bucket (if created)"
}

output "service_account_email" {
  value       = google_service_account.document_archive.email
  description = "Email of the service account for app access"
}

output "kms_key_name" {
  value       = google_kms_crypto_key.bucket_key.id
  description = "KMS key used for encryption"
}
