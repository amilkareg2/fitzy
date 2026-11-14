output "api_url" {
  description = "Public URL of the fitzy-api Cloud Run service."
  value       = google_cloud_run_v2_service.api.uri
}

output "api_image" {
  description = "Image the API service currently runs (CI reads this to keep it during the pre-migration apply)."
  value       = local.api_image
}

output "migrate_job" {
  description = "Name of the Cloud Run job that runs Alembic migrations."
  value       = google_cloud_run_v2_job.migrate.name
}

output "database_url_version" {
  description = "Version of fitzy-database-url the service and job are pinned to."
  value       = data.google_secret_manager_secret_version.database_url.version
}
