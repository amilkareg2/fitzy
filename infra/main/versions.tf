terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Bucket is passed at init time (partial configuration) so the project id is not
  # hard-coded here:
  #   terraform init -backend-config="bucket=<project_id>-fitzy-tfstate"
  # The bucket is created by infra/bootstrap.
  backend "gcs" {
    prefix = "main"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
