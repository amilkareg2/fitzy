variable "project_id" {
  description = "GCP project that hosts Fitzy."
  type        = string
  default     = "mymancave"
}

variable "region" {
  description = "Region for the state bucket, Artifact Registry, Cloud Run and Cloud SQL."
  type        = string
  default     = "europe-west1"
}

variable "github_repository" {
  description = "GitHub repository (owner/name) allowed to deploy through Workload Identity Federation."
  type        = string
  default     = "amilkareg2/fitzy"
}

variable "github_repository_id" {
  description = <<-EOT
    Optional numeric GitHub repository id (gh api repos/OWNER/REPO --jq .id).
    When set, the WIF provider also checks it, so a repository deleted and re-created
    under the same name by someone else could not deploy. Leave empty to skip.
  EOT
  type        = string
  default     = ""
}

variable "deploy_ref" {
  description = "Only workflows running on this git ref may impersonate the deployer."
  type        = string
  default     = "refs/heads/main"
}
