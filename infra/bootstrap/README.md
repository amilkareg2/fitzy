# Bootstrap (run once)

Everything CI needs before it can deploy, set up by you once. The database is
[Neon](https://neon.com) serverless Postgres, created by hand in the Neon console; there
is no Neon Terraform provider and no Neon API key anywhere. GCP resources are created
with Terraform from [Google Cloud Shell](https://shell.cloud.google.com), which is
already authenticated as you (project owner) and has Terraform installed.

What `terraform apply` here creates in project `mymancave`, region `europe-west1`:

| Resource | Purpose |
| --- | --- |
| APIs: run, artifactregistry, secretmanager, iam, iamcredentials, sts, cloudresourcemanager, serviceusage, storage | Needed by the app stack and by keyless auth |
| Bucket `mymancave-fitzy-tfstate` | Terraform state for `infra/main` (versioned, uniform access, public access blocked) |
| Artifact Registry `fitzy` (Docker) | Images pushed by CI; cleanup keeps the 10 newest, deletes others after 30 days |
| Secret `fitzy-database-url` (empty) | Neon connection string; you add the value in step 3 |
| Secret `fitzy-auth-secret` (empty) | App signing secret; CI generates and stores the value |
| SA `fitzy-runtime` | Identity of the Cloud Run service and migration job; can read exactly the two secrets above, nothing else |
| SA `fitzy-deployer` | Identity CI impersonates; roles are listed and justified in `main.tf` |
| WIF pool `fitzy-github` + provider `github-oidc` | Accepts GitHub OIDC tokens only from `amilkareg2/fitzy` on `refs/heads/main` |

No service-account keys are created, and none should ever be.

## Order of operations

1. Create the Neon project (Neon console).
2. Run this bootstrap (Cloud Shell).
3. Add the database URL as a secret version (Cloud Shell).
4. Set the four GitHub repository variables (GitHub UI).
5. Merge to `main`: CI deploys.

### 1. Create the Neon project

In the [Neon console](https://console.neon.tech): **New project**

- Name: `fitzy`
- Postgres version: **16**
- Region: **AWS Europe Central 1 (Frankfurt)**, `aws-eu-central-1` (closest to Cloud Run in `europe-west1`)
- Database name: `fitzy` (if the form doesn't ask, add it afterwards under **Databases**)

Then open **Connect** on the project dashboard, select the `fitzy` database, and
**turn connection pooling off** so you get the **direct** connection string (the host
must not contain `-pooler`). It looks like:

```
postgresql://<role>:<password>@ep-<name>-<id>.eu-central-1.aws.neon.tech/fitzy?sslmode=require
```

Copy it as Neon shows it (`postgresql://` scheme, `sslmode=require`); the backend
switches the scheme to `postgresql+psycopg` itself. Keep the tab open for step 3; do
not paste it anywhere else (chat, notes, the repo).

pgvector needs no setup: the app's first Alembic migration runs
`CREATE EXTENSION IF NOT EXISTS vector`, which the Neon owner role is allowed to do.

### 2. Run the bootstrap

```bash
# In Cloud Shell
gcloud config set project mymancave
git clone https://github.com/amilkareg2/fitzy.git
cd fitzy/infra/bootstrap

# Optional but recommended: also pin the repository's numeric id, so a repository
# re-created under the same name by someone else could never deploy.
REPO_ID=$(curl -s https://api.github.com/repos/amilkareg2/fitzy | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
echo "github_repository_id = \"$REPO_ID\"" > terraform.tfvars   # git-ignored

terraform init
terraform apply
```

If `apply` fails with "API not enabled" or "permission denied" right after enabling
the APIs, wait a minute and run `terraform apply` again (API enablement and IAM
changes take a little while to propagate).

### 3. Add the database URL to Secret Manager

Still in Cloud Shell. `read -s` keeps the value off the screen and out of shell
history; paste the Neon string when prompted and press Enter:

```bash
read -rs -p "Neon direct connection string: " NEON_URL; echo
printf '%s' "$NEON_URL" | gcloud secrets versions add fitzy-database-url --data-file=-
unset NEON_URL

# Check that a version exists (prints metadata only, not the value)
gcloud secrets versions list fitzy-database-url
```

`printf '%s'` avoids a trailing newline in the secret.

**Rotating later** (e.g. after resetting the Neon password): add a new version the same
way, then redeploy (**Actions → Deploy → Run workflow** on `main`). Each deploy pins
the service to the latest version; running revisions keep the one they started with.
Then disable the old version: `gcloud secrets versions disable <N> --secret fitzy-database-url`.

### 4. Set the GitHub repository variables

These are **variables, not secrets**: none of them is sensitive. They are identifiers;
access is enforced by Workload Identity Federation (only this repository's `main`
branch can use them), not by keeping them hidden.

In GitHub, open the repository, then **Settings → Secrets and variables → Actions →
Variables** tab → **New repository variable**, and add each row (name exactly as
written, value from the command in the last column, run in Cloud Shell inside
`fitzy/infra/bootstrap`):

| Name | What it is | Value |
| --- | --- | --- |
| `GCP_PROJECT_ID` | The GCP project Fitzy runs in | `mymancave` |
| `GCP_REGION` | Where Cloud Run and the image registry live | `europe-west1` |
| `GCP_WIF_PROVIDER` | The "door" GitHub Actions uses to log in to GCP without a key | output of `terraform output -raw workload_identity_provider` (looks like `projects/123456789012/locations/global/workloadIdentityPools/fitzy-github/providers/github-oidc`) |
| `GCP_DEPLOY_SA` | The GCP identity CI acts as when deploying | output of `terraform output -raw deployer_service_account` (`fitzy-deployer@mymancave.iam.gserviceaccount.com`) |

Optional fifth variable: `FITZY_OWNER_EMAIL`, the email the app uses as `OWNER_EMAIL`.

`terraform output github_variables` prints all four at once. If you have the GitHub
CLI on your own machine, the equivalent is:

```bash
gh variable set GCP_PROJECT_ID   --repo amilkareg2/fitzy --body mymancave
gh variable set GCP_REGION       --repo amilkareg2/fitzy --body europe-west1
gh variable set GCP_WIF_PROVIDER --repo amilkareg2/fitzy --body "<terraform output -raw workload_identity_provider>"
gh variable set GCP_DEPLOY_SA    --repo amilkareg2/fitzy --body "<terraform output -raw deployer_service_account>"
```

### 5. Merge to `main`

The next push to `main` that touches `backend/`, `data/`, `infra/main/` or
`deploy.yml` deploys, after CI passes. You can also start it from **Actions → Deploy →
Run workflow** on `main`. The deploy fails early with a clear message if step 3 was
skipped.

## Commit the provider lock files

Lock files pin provider checksums for every platform CI and you use. Generate them in
Cloud Shell and commit them (in a PR):

```bash
cd ~/fitzy
for d in infra/bootstrap infra/main; do
  terraform -chdir=$d init -backend=false
  terraform -chdir=$d providers lock -platform=linux_amd64 -platform=darwin_arm64
done
git add infra/*/.terraform.lock.hcl
```

## Optional: move this stack's state into the bucket

Bootstrap state starts on Cloud Shell's disk (`terraform.tfstate`, git-ignored). Cloud
Shell home directories are deleted after a long period of inactivity, so move it:

```bash
cat > backend.tf <<'EOF'
terraform {
  backend "gcs" {
    bucket = "mymancave-fitzy-tfstate"
    prefix = "bootstrap"
  }
}
EOF
terraform init -migrate-state
```

## Changing or removing

Re-run `terraform apply` here after editing. The deployer cannot change any of these
resources itself, by design. Destroying this stack revokes CI's access and deletes the
secrets (including the database URL); destroy `infra/main` first if you want
everything gone (see `../README.md`). The Neon project is deleted in the Neon console.
