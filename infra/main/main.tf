# Fitzy app stack. Applied by CI (.github/workflows/deploy.yml) as fitzy-deployer.
#
# Prerequisites created by infra/bootstrap (deliberately not here, see the comment at
# the top of infra/bootstrap/main.tf): APIs, the state bucket, the Artifact Registry
# repository "fitzy", and the service accounts fitzy-runtime / fitzy-deployer.

locals {
  placeholder_image = "us-docker.pkg.dev/cloudrun/container/hello"
  api_image         = var.api_image != "" ? var.api_image : local.placeholder_image
  migrate_image     = var.migrate_image != "" ? var.migrate_image : local.placeholder_image

  runtime_sa_email = "fitzy-runtime@${var.project_id}.iam.gserviceaccount.com"

  db_name = "fitzy"
  db_user = "fitzy"
}

# ---------------------------------------------------------------------------
# Cloud SQL: Postgres 16, public IP, no authorized networks.
# Cloud Run reaches it through the built-in Cloud SQL connector (unix socket under
# /cloudsql), which authenticates with IAM (roles/cloudsql.client) and encrypts the
# connection. With no authorized networks nothing else can connect directly.
# Private IP would need VPC peering / Serverless VPC access, which costs more.
#
# pgvector: available on Cloud SQL for Postgres without any database flag. The app's
# first Alembic migration runs `CREATE EXTENSION IF NOT EXISTS vector`; the "fitzy"
# user is a cloudsqlsuperuser member, which is allowed to do that.
# ---------------------------------------------------------------------------

resource "google_sql_database_instance" "main" {
  name             = "fitzy-pg"
  database_version = "POSTGRES_16"
  region           = var.region

  # Terraform refuses to destroy it; set to false (and apply) first if you really mean it.
  deletion_protection = true

  settings {
    # Shared-core tiers (db-f1-micro, db-g1-small) require the ENTERPRISE edition.
    # New POSTGRES_16 instances may default to ENTERPRISE_PLUS, so set it explicitly.
    edition           = "ENTERPRISE"
    tier              = var.db_tier
    availability_type = "ZONAL"

    disk_type             = var.db_disk_type
    disk_size             = var.db_disk_size_gb
    disk_autoresize       = true
    disk_autoresize_limit = 50

    # Also protect against deletion from the console / gcloud.
    deletion_protection_enabled = true

    # Stop/start is done with gcloud (see infra/README.md); ignored below so CI does not
    # switch a stopped instance back on.
    activation_policy = "ALWAYS"

    ip_configuration {
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"
      # No authorized_networks blocks on purpose.
    }

    backup_configuration {
      enabled    = true
      start_time = "02:00" # UTC, night in Europe
      # Point-in-time recovery keeps WAL logs and adds storage cost; daily backups are
      # enough for a single-user tracker.
      point_in_time_recovery_enabled = false

      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }

    maintenance_window {
      day          = 7 # Sunday
      hour         = 3 # UTC
      update_track = "stable"
    }
  }

  lifecycle {
    ignore_changes = [settings[0].activation_policy]
  }
}

resource "google_sql_database" "fitzy" {
  name     = local.db_name
  instance = google_sql_database_instance.main.name
}

resource "random_password" "db" {
  length  = 32
  special = false # keeps the DSN free of characters that need URL-encoding
}

resource "google_sql_user" "fitzy" {
  name     = local.db_user
  instance = google_sql_database_instance.main.name
  password = random_password.db.result

  # Postgres refuses to drop a role that owns objects; just forget it on destroy.
  deletion_policy = "ABANDON"
}

# ---------------------------------------------------------------------------
# Secrets. Values are generated here, so they also live in Terraform state; the state
# bucket is private and only the owner and fitzy-deployer can read it.
# ---------------------------------------------------------------------------

resource "random_password" "auth_secret" {
  length  = 64
  special = false
}

locals {
  database_url = "postgresql+psycopg://${local.db_user}:${random_password.db.result}@/${local.db_name}?host=/cloudsql/${google_sql_database_instance.main.connection_name}"

  secrets = {
    database_url = {
      id    = "fitzy-database-url"
      value = local.database_url
    }
    auth_secret = {
      id    = "fitzy-auth-secret"
      value = random_password.auth_secret.result
    }
  }
}

resource "google_secret_manager_secret" "app" {
  for_each = local.secrets

  secret_id = each.value.id

  # Single EU region: data stays in the EU and only one replica is billed.
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

resource "google_secret_manager_secret_version" "app" {
  for_each = local.secrets

  secret      = google_secret_manager_secret.app[each.key].id
  secret_data = each.value.value
}

# The runtime SA can read these secrets and nothing else in Secret Manager.
resource "google_secret_manager_secret_iam_member" "runtime_access" {
  for_each = local.secrets

  secret_id = google_secret_manager_secret.app[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${local.runtime_sa_email}"
}

# ---------------------------------------------------------------------------
# Cloud Run: API service
# ---------------------------------------------------------------------------

resource "google_cloud_run_v2_service" "api" {
  name     = "fitzy-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  # Stateless; allow terraform destroy. The database is the protected part.
  deletion_protection = false

  template {
    service_account                  = local.runtime_sa_email
    timeout                          = "60s"
    max_instance_request_concurrency = 40

    scaling {
      min_instance_count = 0 # scale to zero: no cost when idle
      max_instance_count = var.max_instances
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.main.connection_name]
      }
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

      # Pin secret versions (not "latest") so a rotated secret rolls out a new revision.
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.app["database_url"].secret_id
            version = google_secret_manager_secret_version.app["database_url"].version
          }
        }
      }

      env {
        name = "AUTH_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.app["auth_secret"].secret_id
            version = google_secret_manager_secret_version.app["auth_secret"].version
          }
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.runtime_access,
    google_sql_database.fitzy,
    google_sql_user.fitzy,
  ]
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
# service is switched to that image (see .github/workflows/deploy.yml).
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

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [google_sql_database_instance.main.connection_name]
        }
      }

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

        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.app["database_url"].secret_id
              version = google_secret_manager_secret_version.app["database_url"].version
            }
          }
        }

        # Settings classes often require it at import time even if migrations don't.
        env {
          name = "AUTH_SECRET"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.app["auth_secret"].secret_id
              version = google_secret_manager_secret_version.app["auth_secret"].version
            }
          }
        }

        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.runtime_access,
    google_sql_database.fitzy,
    google_sql_user.fitzy,
  ]
}
