terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # Bootstrap starts with local state (in Cloud Shell's persistent $HOME).
  # Once the state bucket exists you can move this state into it; see README.md.
}

provider "google" {
  project = var.project_id
  region  = var.region
}
