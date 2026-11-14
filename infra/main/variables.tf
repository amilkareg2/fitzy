variable "project_id" {
  description = "GCP project id (same as in infra/bootstrap)."
  type        = string
}

variable "region" {
  description = "Region for Cloud Run (Neon lives in AWS eu-central-1, set up by hand)."
  type        = string
  default     = "europe-west1"
}

variable "api_image" {
  description = <<-EOT
    Container image for the fitzy-api Cloud Run service. Empty means a public
    placeholder (Google's hello container), so the very first apply works before any
    image has been pushed. CI always passes the image that is currently deployed or
    the new one; if you apply by hand, pass it too or the service reverts to hello.
  EOT
  type        = string
  default     = ""
}

variable "migrate_image" {
  description = "Container image for the fitzy-migrate Cloud Run job. Empty means placeholder."
  type        = string
  default     = ""
}

variable "migrate_command" {
  description = "Entrypoint for the migration job. Runs in the image's WORKDIR (must contain alembic.ini)."
  type        = list(string)
  default     = ["alembic", "upgrade", "head"]
}

variable "container_port" {
  description = "Port the API listens on. Cloud Run also sets PORT to this value."
  type        = number
  default     = 8080
}

variable "max_instances" {
  description = "Upper bound on Cloud Run instances (also caps connections to Neon)."
  type        = number
  default     = 2
}

variable "app_env" {
  description = "Value of APP_ENV in Cloud Run."
  type        = string
  default     = "production"
}

variable "owner_email" {
  description = "OWNER_EMAIL for the app's single-user auth. Optional."
  type        = string
  default     = ""
}

variable "extra_env" {
  description = "Additional non-secret environment variables for the API service."
  type        = map(string)
  default     = {}
}
