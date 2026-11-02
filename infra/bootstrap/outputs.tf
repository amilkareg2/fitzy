output "workload_identity_provider" {
  description = "Full resource name of the WIF provider -> GitHub variable GCP_WIF_PROVIDER."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "deployer_service_account" {
  description = "Deployer service account email -> GitHub variable GCP_DEPLOY_SA."
  value       = google_service_account.deployer.email
}

output "runtime_service_account" {
  description = "Service account Cloud Run runs as (used by infra/main)."
  value       = google_service_account.runtime.email
}

output "tfstate_bucket" {
  description = "GCS bucket holding Terraform state for infra/main (prefix \"main\")."
  value       = google_storage_bucket.tfstate.name
}

output "database_url_secret" {
  description = "Secret the owner adds the Neon connection string to (README step 3)."
  value       = google_secret_manager_secret.app["database_url"].secret_id
}

output "artifact_registry_repository" {
  description = "Docker repository CI pushes images to."
  value       = "${google_artifact_registry_repository.fitzy.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.fitzy.repository_id}"
}

output "github_variables" {
  description = "Paste these as GitHub repository VARIABLES (Settings > Secrets and variables > Actions > Variables)."
  value = {
    GCP_PROJECT_ID   = var.project_id
    GCP_REGION       = var.region
    GCP_WIF_PROVIDER = google_iam_workload_identity_pool_provider.github.name
    GCP_DEPLOY_SA    = google_service_account.deployer.email
  }
}
