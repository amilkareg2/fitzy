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

output "sql_instance" {
  description = "Cloud SQL instance name (for gcloud sql instances patch/describe)."
  value       = google_sql_database_instance.main.name
}

output "sql_connection_name" {
  description = "PROJECT:REGION:INSTANCE, for the Cloud SQL Auth Proxy."
  value       = google_sql_database_instance.main.connection_name
}
