# Fitzy app stack. Applied by CI (.github/workflows/deploy.yml) as fitzy-deployer.
#
# Prerequisites created by infra/bootstrap (deliberately not here, see the comment at
# the top of infra/bootstrap/main.tf): APIs, the state bucket, the Artifact Registry
# repository "fitzy", the service accounts fitzy-runtime / fitzy-deployer, and the
# Secret Manager secrets fitzy-database-url / fitzy-auth-secret with their IAM.
#
# Database: Neon serverless Postgres, created by hand in the Neon console (no Neon
# provider, no Neon API key anywhere). Its connection string is stored once by the
# owner as a version of fitzy-database-url; this stack only references that version.

locals {
  placeholder_image = "us-docker.pkg.dev/cloudrun/container/hello"
  api_image         = var.api_image != "" ? var.api_image : local.placeholder_image
  migrate_image     = var.migrate_image != "" ? var.migrate_image : local.placeholder_image

  runtime_sa_email = "fitzy-runtime@${var.project_id}.iam.gserviceaccount.com"

  database_url_secret = "projects/${var.project_id}/secrets/fitzy-database-url"
  auth_secret_secret  = "projects/${var.project_id}/secrets/fitzy-auth-secret"
}

# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------

# Latest version of the Neon connection string the owner added by hand. Metadata
# only: fetch_secret_data = false means the URL is never read by CI and never lands in
# Terraform state (the deployer only has secretmanager.viewer on this secret).
# Fails with "not found" until the owner has added a version (bootstrap README step 3).
data "google_secret_manager_secret_version" "database_url" {
  secret            = local.database_url_secret
  fetch_secret_data = false
}

# Signing secret for the app's own auth. Generated here, so it is also in Terraform
# state; the state bucket is private (owner + fitzy-deployer only).
resource "random_password" "auth_secret" {
  length  = 64
  special = false
}

resource "google_secret_manager_secret_version" "auth_secret" {
  secret      = local.auth_secret_secret
  secret_data = random_password.auth_secret.result
}

locals {
  # Pinned version numbers (not "latest"): adding a new version of either secret and
  # redeploying rolls out a new revision that uses it.
  secret_env = {
    DATABASE_URL = {
      secret  = "fitzy-database-url"
      version = data.google_secret_manager_secret_version.database_url.version
    }
    AUTH_SECRET = {
      secret  = "fitzy-auth-secret"
      version = google_secret_manager_secret_version.auth_secret.version
    }
  }
}

# ---------------------------------------------------------------------------
# Cloud Run: API service
# ---------------------------------------------------------------------------

resource "google_cloud_run_v2_service" "api" {
  name     = "fitzy-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  # Stateless; allow terraform destroy. The data lives in Neon.
  deletion_protection = false

  template {
    service_account                  = local.runtime_sa_email
    timeout                          = "60s"
    max_instance_request_concurrency = 40

    scaling {
      min_instance_count = 0 # scale to zero: no cost when idle
      max_instance_count = var.max_instances
    }

    containers {
      image = local.api_image

      ports {
        container_port = var.container_port
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true # CPU throttled outside requests (request-based billing)
        startup_cpu_boost = true # faster cold starts; only billed while starting
      }

      env {
        name  = "APP_ENV"
        value = var.app_env
      }

      dynamic "env" {
        for_each = var.owner_email == "" ? {} : { OWNER_EMAIL = var.owner_email }
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.extra_env
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = local.secret_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value.secret
              version = env.value.version
            }
          }
        }
      }
    }
  }
}

# Public endpoint: the app does its own (single-user) authentication.
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ---------------------------------------------------------------------------
# Cloud Run job: Alembic migrations. CI executes it with the new image before the
# service is switched to that image (see .github/workflows/deploy.yml). It reaches
# Neon over the internet (TLS, sslmode=require), like the service.
# ---------------------------------------------------------------------------

resource "google_cloud_run_v2_job" "migrate" {
  name                = "fitzy-migrate"
  location            = var.region
  deletion_protection = false

  template {
    task_count = 1

    template {
      service_account = local.runtime_sa_email
      max_retries     = 0
      timeout         = "600s"

      containers {
        image   = local.migrate_image
        command = var.migrate_command

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }

        env {
          name  = "APP_ENV"
          value = var.app_env
        }

        # AUTH_SECRET too: settings classes often require it at import time.
        dynamic "env" {
          for_each = local.secret_env
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value.secret
                version = env.value.version
              }
            }
          }
        }
      }
    }
  }
}
