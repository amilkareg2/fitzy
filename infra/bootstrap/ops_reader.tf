# ---------------------------------------------------------------------------
# Read-only diagnostics identity (fitzy-reader), used from the private repo
# var.ops_repository so an agent can read logs and service state without holding
# any credential. It can look, never change: every role below is a viewer role.
# ---------------------------------------------------------------------------

resource "google_service_account" "reader" {
  project      = var.project_id
  account_id   = "fitzy-reader"
  display_name = "Fitzy read-only diagnostics (GitHub Actions, ${var.ops_repository})"
}

# A separate provider, so the ops repo's tokens and the app repo's tokens are judged
# by separate conditions. Ops tokens can never reach fitzy-deployer: its binding
# names attribute.repository = var.github_repository.
resource "google_iam_workload_identity_pool_provider" "github_ops" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc-ops"
  display_name                       = "GitHub OIDC (ops)"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  attribute_condition = join(" && ", [
    "assertion.repository == \"${var.ops_repository}\"",
    "assertion.ref == \"${var.deploy_ref}\"",
  ])

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "reader_wif" {
  service_account_id = google_service_account.reader.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.ops_repository}"
}

locals {
  reader_project_roles = [
    # Describe Cloud Run services, revisions, jobs and executions (no changes, no invocations).
    "roles/run.viewer",
    # Lets gcloud bill API calls to this project (quota), a requirement for SA callers.
    "roles/serviceusage.serviceUsageConsumer",
  ]
}

resource "google_project_iam_member" "reader" {
  for_each = toset(local.reader_project_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.reader.email}"
}

# Logs: the project is shared, so the reader does not get roles/logging.viewer (every log
# in the project). It reads a log view limited to Cloud Run services and jobs instead.
# Log view filters only support resource.type, LOG_ID() and SOURCE(), so other Cloud Run
# workloads in this project would be visible too; there are none today.
resource "google_logging_log_view" "fitzy" {
  name        = "fitzy-cloud-run"
  bucket      = "projects/${var.project_id}/locations/global/buckets/_Default"
  description = "Cloud Run service and job logs, for fitzy-reader diagnostics."
  filter      = "resource.type = \"cloud_run_revision\" OR resource.type = \"cloud_run_job\""
}

resource "google_project_iam_member" "reader_log_view" {
  project = var.project_id
  role    = "roles/logging.viewAccessor"
  member  = "serviceAccount:${google_service_account.reader.email}"

  condition {
    title      = "fitzy-cloud-run log view only"
    expression = "resource.name == \"${google_logging_log_view.fitzy.id}\""
  }
}

# Secret metadata only (does a version exist, is it enabled), never the values:
# secretmanager.viewer has no secretmanager.versions.access permission.
resource "google_secret_manager_secret_iam_member" "reader" {
  for_each = google_secret_manager_secret.app

  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.viewer"
  member    = "serviceAccount:${google_service_account.reader.email}"
}

resource "google_artifact_registry_repository_iam_member" "reader" {
  project    = var.project_id
  location   = google_artifact_registry_repository.fitzy.location
  repository = google_artifact_registry_repository.fitzy.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.reader.email}"
}
