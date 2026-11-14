# Fitzy infrastructure

The API runs on GCP Cloud Run (project `mymancave`, region `europe-west1`). The
database is [Neon](https://neon.com) serverless Postgres 16 with pgvector
(`aws-eu-central-1`, Frankfurt), created by hand in the Neon console. Both scale to
zero, so an idle single-user app costs close to nothing.

| Piece | Who sets it up | State | Creates |
| --- | --- | --- | --- |
| Neon project | You, once, in the Neon console | Neon | Postgres 16 project, database `fitzy` |
| [`bootstrap/`](bootstrap/README.md) | You, once, from Cloud Shell as owner | Local (optionally moved to the bucket) | APIs, state bucket, Artifact Registry, service accounts, the two Secret Manager secrets and their IAM, Workload Identity Federation |
| `main/` | CI on every deploy, as `fitzy-deployer` | `gs://mymancave-fitzy-tfstate/main` | Auth-secret value, Cloud Run service `fitzy-api`, Cloud Run job `fitzy-migrate` |

Order of operations (details in [`bootstrap/README.md`](bootstrap/README.md)):

1. Create the Neon project and copy its **direct** connection string.
2. Run `bootstrap/` from Cloud Shell.
3. Add the connection string as a version of the `fitzy-database-url` secret.
4. Set the four GitHub repository variables.
5. Merge to `main`: CI deploys. From then on, every merge to `main` that touches the
   backend or `infra/main` is deployed.

## Identities and credentials

There are no long-lived credentials in CI: no service-account JSON keys, no GitHub
secrets, no Neon API key. The only long-lived credential is the Neon connection
string, which you put into Secret Manager by hand and only the runtime can read.

```
GitHub Actions (amilkareg2/fitzy, refs/heads/main)
   │  OIDC token (issued per job, expires in minutes)
   ▼
Workload Identity Pool "fitzy-github" / provider "github-oidc"
   │  condition: repository == amilkareg2/fitzy && ref == refs/heads/main
   ▼
fitzy-deployer  (impersonated, short-lived access token)
   ├─ run.admin, serviceUsageConsumer       (project)
   ├─ artifactregistry.writer               (repository "fitzy" only)
   ├─ storage.objectAdmin                   (state bucket only)
   ├─ iam.serviceAccountUser                (fitzy-runtime only)
   ├─ secretmanager.viewer                  (fitzy-database-url: metadata, never the value)
   └─ viewer + secretVersionManager + secretAccessor  (fitzy-auth-secret only)
          │ deploys
          ▼
Cloud Run service fitzy-api / job fitzy-migrate ── run as ──► fitzy-runtime
                                                                └─ secretAccessor ──► fitzy-database-url,
                                                                      (per secret)     fitzy-auth-secret
fitzy-api / fitzy-migrate ──TLS (sslmode=require), public internet──► Neon (aws-eu-central-1)
Users ──HTTPS──► fitzy-api (public; the app does its own auth)
```

Why the runtime SA, the Artifact Registry repo and the secrets live in `bootstrap/`:
creating them and their IAM from CI would need project-wide `iam.serviceAccountAdmin`,
`artifactregistry.admin`, `secretmanager.admin` and project IAM admin on the deployer.
In a shared project that would let CI grant itself anything or read every secret. With
them created by the owner, the deployer only gets narrowly scoped bindings, and it can
never read the database URL.

## Deploy flow (`.github/workflows/deploy.yml`)

`ci.yml` runs the checks; on a push to `main` its last job calls `deploy.yml`
(`workflow_call`) only if nothing failed. This keeps one run per commit with a single
status and deploys exactly the commit that was tested.

1. Authenticate with WIF; check that `fitzy-database-url` has an enabled version.
2. Build `backend/Dockerfile`, push
   `europe-west1-docker.pkg.dev/mymancave/fitzy/api:<git sha>`.
3. `terraform apply` with `migrate_image=<new>` and `api_image=<currently deployed>`:
   converges the stack (creates it on the first run), pins both secrets to their
   current version numbers, and points the migration job at the new image without
   touching the running API.
4. `gcloud run jobs execute fitzy-migrate --wait`: runs `alembic upgrade head` inside
   GCP as `fitzy-runtime`, connecting to Neon with the secret. The connection string
   never reaches the runner.
5. `terraform apply` with `api_image=<new>`: Cloud Run rolls out the new revision.
6. Smoke test `GET /health`.

If migrations fail, step 5 never runs and the old revision keeps serving.

## What the backend image must provide

- `backend/Dockerfile` (build context `backend/`).
- Listens on `$PORT` (Cloud Run sets it to 8080).
- `alembic` on `PATH` and `alembic.ini` in the image's `WORKDIR` (the job runs
  `alembic upgrade head`; override with the `migrate_command` variable).
- Reads `DATABASE_URL`, `AUTH_SECRET`, `APP_ENV`, `OWNER_EMAIL` from the environment.
  `DATABASE_URL` is Neon's string as-is (`postgresql://…?sslmode=require`); the app
  normalizes the scheme to `postgresql+psycopg`.
- The first migration runs `CREATE EXTENSION IF NOT EXISTS vector`.
- Tolerates a sleeping database: Neon suspends compute after 5 minutes idle and the
  first connection wakes it (usually well under a second, but use `pool_pre_ping`
  and a connect timeout of several seconds). Keep the pool small (up to 2 instances
  plus the migration job share the database).

## Cost

Everything is sized to stay within free allowances for one user. Check current pricing
and limits before relying on any number here; these are the published free-tier terms
at the time of writing.

| Item | Cost driver |
| --- | --- |
| **Neon** (Free plan) | Per project: 1 GB storage, 100 CU-hours of compute per month, compute scales to zero after 5 minutes idle (cannot be disabled), 5 GB public network transfer per month. Over the compute or transfer quota, compute is suspended until next month (no charge); over 1 GB, writes fail. Nothing is billed on the Free plan. See [Neon free plan](https://neon.com/docs/introduction/free-tier) |
| Cloud Run | Request-based billing with a monthly free allowance of vCPU-seconds, GiB-seconds and requests (see [Cloud Run pricing](https://cloud.google.com/run/pricing)). Scales to zero, CPU throttled outside requests; one user stays far inside it |
| Cloud Run job | Seconds of compute per deploy, inside the same free allowance |
| Artifact Registry | Storage beyond the free 0.5 GB; the cleanup policy keeps it small |
| Secret Manager | A few active secret versions; within or close to the free allowance. Disable old versions after rotating |
| Network egress | Cloud Run → Neon (GCP Belgium → AWS Frankfurt) is internet egress, billed by GCP beyond its free allowance; tiny for one user |
| GCS state bucket | Kilobytes; effectively free |

Nothing needs stopping when not in use: both Cloud Run and Neon scale to zero on their
own.

## Removing everything

1. `terraform destroy` in `main/` (run locally:
   `terraform init -backend-config="bucket=mymancave-fitzy-tfstate"`, same variables).
2. `terraform destroy` in `bootstrap/` (the state bucket has `force_destroy = false`, so
   empty it first). This deletes both secrets.
3. Delete the Neon project in the Neon console (this deletes the data).

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
