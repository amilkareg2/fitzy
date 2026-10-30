# Fitzy infrastructure

Two Terraform stacks on GCP (project `mymancave`, region `europe-west1`):

| Stack | Who runs it | State | Creates |
| --- | --- | --- | --- |
| [`bootstrap/`](bootstrap/README.md) | You, once, from Cloud Shell as owner | Local (optionally moved to the bucket) | APIs, state bucket, Artifact Registry, service accounts, Workload Identity Federation |
| `main/` | CI on every deploy, as `fitzy-deployer` | `gs://mymancave-fitzy-tfstate/main` | Cloud SQL Postgres 16, Secret Manager secrets, Cloud Run service `fitzy-api`, Cloud Run job `fitzy-migrate` |

Bootstrap once, then forget about it: every merge to `main` that touches the backend
or `infra/main` is deployed by GitHub Actions.

## Identities

There are no long-lived credentials anywhere: no service-account JSON keys, no GitHub
secrets.

```
GitHub Actions (amilkareg2/fitzy, refs/heads/main)
   │  OIDC token (issued per job, expires in minutes)
   ▼
Workload Identity Pool "fitzy-github" / provider "github-oidc"
   │  condition: repository == amilkareg2/fitzy && ref == refs/heads/main
   ▼
fitzy-deployer  (impersonated, short-lived access token)
   ├─ run.admin, cloudsql.admin, secretmanager.admin, serviceUsageConsumer  (project)
   ├─ artifactregistry.writer   (repository "fitzy" only)
   ├─ storage.objectAdmin       (state bucket only)
   └─ iam.serviceAccountUser    (fitzy-runtime only)
          │ deploys
          ▼
Cloud Run service fitzy-api / job fitzy-migrate ── run as ──► fitzy-runtime
                                                                ├─ cloudsql.client ──► Cloud SQL fitzy-pg
                                                                │     (unix socket /cloudsql/..., public IP,
                                                                │      no authorized networks)
                                                                └─ secretAccessor ───► fitzy-database-url,
                                                                      (per secret)      fitzy-auth-secret
Users ──HTTPS──► fitzy-api (public; the app does its own auth)
```

Why the runtime SA and the Artifact Registry repo live in `bootstrap/`: creating them
from CI would need project-wide `iam.serviceAccountAdmin`, `artifactregistry.admin`
and project IAM admin on the deployer, which would let CI grant itself anything. With
them created by the owner, the deployer only gets narrowly scoped bindings.

## Deploy flow (`.github/workflows/deploy.yml`)

`ci.yml` runs the checks; on a push to `main` its last job calls `deploy.yml`
(`workflow_call`) only if nothing failed. This keeps one run per commit with a single
status, deploys exactly the commit that was tested, and avoids `workflow_run`'s
quirks (it always runs the default branch's workflow file and shows up as a separate,
detached run).

1. Authenticate with WIF, build `backend/Dockerfile`, push
   `europe-west1-docker.pkg.dev/mymancave/fitzy/api:<git sha>`.
2. `terraform apply` with `migrate_image=<new>` and `api_image=<currently deployed>`:
   converges infrastructure (and creates it all on the first run) and points the
   migration job at the new image, without touching the running API.
3. `gcloud run jobs execute fitzy-migrate --wait`: runs `alembic upgrade head` inside
   GCP as `fitzy-runtime` through the Cloud SQL socket. The DB password never reaches
   the runner, and nothing needs the Cloud SQL Auth Proxy.
4. `terraform apply` with `api_image=<new>`: Cloud Run rolls out the new revision.
5. Smoke test `GET /health`.

If migrations fail, step 4 never runs and the old revision keeps serving.

## What the backend image must provide

- `backend/Dockerfile` (build context `backend/`).
- Listens on `$PORT` (Cloud Run sets it to 8080).
- `alembic` on `PATH` and `alembic.ini` in the image's `WORKDIR` (the job runs
  `alembic upgrade head`; override with the `migrate_command` variable).
- Reads `DATABASE_URL`, `AUTH_SECRET`, `APP_ENV`, `OWNER_EMAIL` from the environment.
  `DATABASE_URL` looks like
  `postgresql+psycopg://fitzy:…@/fitzy?host=/cloudsql/mymancave:europe-west1:fitzy-pg`.
- The first migration runs `CREATE EXTENSION IF NOT EXISTS vector` (pgvector is
  available on Cloud SQL without flags).
- A small connection pool: `db-f1-micro` allows only ~25 connections, and there can be
  up to 2 instances plus the migration job.

## Cost

Single user, so almost everything sits in free tiers or scales to zero. Check current
pricing on the GCP pricing pages; rough picture:

| Item | Cost driver |
| --- | --- |
| **Cloud SQL `db-f1-micro`** | **The main cost.** Billed per hour while running, whether used or not, plus 10 GB SSD storage and backup storage. Expect roughly ten US dollars a month at the time of writing; check current pricing |
| Cloud Run | Request-based billing, scales to zero, CPU throttled when idle. A single user stays well within the monthly free tier |
| Artifact Registry | Storage beyond the free 0.5 GB; the cleanup policy keeps it small |
| Secret Manager | A few cents per active secret version per month |
| GCS state bucket | Kilobytes; effectively free |
| Cloud Run job | Seconds of compute per deploy |

### Stopping the database when not in use

```bash
# Stop (compute billing stops; storage and backups are still billed)
gcloud sql instances patch fitzy-pg --activation-policy=NEVER --project mymancave

# Start again
gcloud sql instances patch fitzy-pg --activation-policy=ALWAYS --project mymancave
```

Terraform ignores `activation_policy`, so CI will not switch it back on, but deploys
fail at the migration step while it is stopped, and the API returns errors.

### Removing everything

`deletion_protection` is on for the database (in Terraform and in GCP). To really
delete it: set `deletion_protection = false` and `deletion_protection_enabled = false`
in `main/main.tf`, apply, then `terraform destroy` in `main/` (run locally with
`-backend-config="bucket=mymancave-fitzy-tfstate"` and the same variables), then
`terraform destroy` in `bootstrap/` (the state bucket has `force_destroy = false`, so
empty it first).

## Running `main/` by hand

Not needed normally. From Cloud Shell as owner:

```bash
cd infra/main
terraform init -backend-config="bucket=mymancave-fitzy-tfstate"
cp terraform.tfvars.example terraform.tfvars   # git-ignored; set api_image/migrate_image
terraform plan
```

Always pass the currently deployed `api_image` (`terraform output -raw api_image`),
otherwise the service is switched back to the placeholder image.
