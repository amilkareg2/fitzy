# One-time bootstrap for Fitzy. Run by a project owner from Cloud Shell.
#
# Creates everything CI needs before it can run infra/main itself:
#   - APIs, the Terraform state bucket
#   - the service accounts (deployer for CI, runtime for Cloud Run)
#   - the Artifact Registry repository CI pushes images to
#   - Workload Identity Federation for GitHub Actions (no JSON keys anywhere)
#
# The runtime service account and the Artifact Registry repository live here, not in
# infra/main, on purpose: creating them from CI would require project-wide
# iam.serviceAccountAdmin / artifactregistry.admin / projectIamAdmin on the deployer,
# which would let CI escalate to any identity in the project. Keeping them here means
# the deployer only gets narrowly scoped roles on resources that already exist.

data "google_project" "this" {
  project_id = var.project_id
}

locals {
  apis = [
    "artifactregistry.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "serviceusage.googleapis.com",
    "sqladmin.googleapis.com",
    "storage.googleapis.com",
    "sts.googleapis.com",
    # Not enabled on purpose:
    # - compute.googleapis.com: not needed for a public-IP Cloud SQL instance reached
    #   through the Cloud SQL connector; enabling it also creates the default compute
    #   service account with the Editor role.
    # - servicenetworking.googleapis.com: only needed for private IP (VPC peering).
  ]

  runtime_sa_id  = "fitzy-runtime"
  deployer_sa_id = "fitzy-deployer"
}

resource "google_project_service" "apis" {
  for_each = toset(local.apis)

  project = var.project_id
  service = each.value

  # Other things in this project may use these APIs; never switch them off on destroy.
  disable_on_destroy = false
}

# ---------------------------------------------------------------------------
# Terraform state bucket for infra/main (and optionally for this stack)
# ---------------------------------------------------------------------------

resource "google_storage_bucket" "tfstate" {
  name     = "${var.project_id}-fitzy-tfstate"
  project  = var.project_id
  location = upper(var.region)

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  # Keep old state versions for recovery, but not forever.
  lifecycle_rule {
    condition {
      num_newer_versions         = 20
      days_since_noncurrent_time = 30
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Service accounts
# ---------------------------------------------------------------------------

resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = local.runtime_sa_id
  display_name = "Fitzy runtime (Cloud Run API + migration job)"

  depends_on = [google_project_service.apis]
}

resource "google_service_account" "deployer" {
  project      = var.project_id
  account_id   = local.deployer_sa_id
  display_name = "Fitzy deployer (GitHub Actions via WIF)"

  depends_on = [google_project_service.apis]
}

# Runtime: connect to Cloud SQL through the Cloud Run Cloud SQL connector.
# cloudsql.client has no per-instance binding, so it is granted on the project.
# Secret access is granted per secret in infra/main (secretAccessor on its secrets only).
resource "google_project_iam_member" "runtime_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = google_service_account.runtime.member
}

# ---------------------------------------------------------------------------
# Deployer roles (least privilege for infra/main + deploys)
# ---------------------------------------------------------------------------

locals {
  deployer_project_roles = {
    # Create/update the Cloud Run service and migration job, execute the job, and set
    # the service's IAM policy (allUsers -> run.invoker). run.developer cannot set IAM.
    run_admin = "roles/run.admin"

    # Create the Cloud SQL instance, database and user. cloudsql.editor cannot manage
    # users. Also covers cloudsql.instances.connect if you ever run the Auth Proxy in CI.
    cloudsql_admin = "roles/cloudsql.admin"

    # Create the app's secrets and versions, and bind secretAccessor on each secret to
    # the runtime SA. Secret-level IAM needs secrets.setIamPolicy, which only admin has.
    secretmanager_admin = "roles/secretmanager.admin"

    # Allows API calls that are attributed/billed to this project (quota project), as
    # gcloud and the Terraform provider do. Read-only otherwise.
    serviceusage_consumer = "roles/serviceusage.serviceUsageConsumer"
  }
}

resource "google_project_iam_member" "deployer" {
  for_each = local.deployer_project_roles

  project = var.project_id
  role    = each.value
  member  = google_service_account.deployer.member
}

# Cloud Run service and job run as fitzy-runtime; deploying them requires actAs on that
# one service account only (not on every SA in the project).
resource "google_service_account_iam_member" "deployer_acts_as_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.deployer.member
}

# Read/write/lock Terraform state, on the state bucket only.
resource "google_storage_bucket_iam_member" "deployer_tfstate" {
  bucket = google_storage_bucket.tfstate.name
  role   = "roles/storage.objectAdmin"
  member = google_service_account.deployer.member
}

# Push images, on the fitzy repository only.
resource "google_artifact_registry_repository_iam_member" "deployer_writer" {
  project    = var.project_id
  location   = google_artifact_registry_repository.fitzy.location
  repository = google_artifact_registry_repository.fitzy.name
  role       = "roles/artifactregistry.writer"
  member     = google_service_account.deployer.member
}

# ---------------------------------------------------------------------------
# Artifact Registry
# ---------------------------------------------------------------------------

resource "google_artifact_registry_repository" "fitzy" {
  project       = var.project_id
  location      = var.region
  repository_id = "fitzy"
  format        = "DOCKER"
  description   = "Fitzy container images"

  # Storage is billed beyond the free tier; keep only recent images.
  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "delete-older-than-30d"
    action = "DELETE"
    condition {
      tag_state  = "ANY"
      older_than = "2592000s"
    }
  }

  cleanup_policies {
    id     = "keep-10-most-recent"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Workload Identity Federation for GitHub Actions
# ---------------------------------------------------------------------------

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "fitzy-github"
  display_name              = "Fitzy GitHub Actions"
  description               = "OIDC tokens from GitHub Actions for ${var.github_repository}"

  depends_on = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_id"    = "assertion.repository_id"
    "attribute.ref"              = "assertion.ref"
    "attribute.event_name"       = "assertion.event_name"
    "attribute.workflow_ref"     = "assertion.workflow_ref"
    "attribute.job_workflow_ref" = "assertion.job_workflow_ref"
  }

  # Tokens from any other repository, or from any other ref of this repository
  # (pull requests, feature branches, tags), are rejected before any IAM check.
  # Deploying is the only thing CI does in GCP; if you later want e.g. a read-only
  # `terraform plan` on PRs, drop the ref clause here and bind a separate read-only SA.
  attribute_condition = join(" && ", compact([
    "assertion.repository == \"${var.github_repository}\"",
    "assertion.ref == \"${var.deploy_ref}\"",
    var.github_repository_id == "" ? "" : "assertion.repository_id == \"${var.github_repository_id}\"",
  ]))

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Defense in depth: even within the pool, only the exact subject
# "repo:<owner>/<repo>:ref:<deploy_ref>" may impersonate the deployer.
resource "google_service_account_iam_member" "deployer_wif" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principal://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/subject/repo:${var.github_repository}:ref:${var.deploy_ref}"
}
