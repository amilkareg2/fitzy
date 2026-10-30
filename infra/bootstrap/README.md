# Bootstrap (run once)

Creates what CI needs before it can deploy anything. Run it yourself, once, from
[Google Cloud Shell](https://shell.cloud.google.com), which is already authenticated
as you (project owner) and has Terraform installed.

What it creates in project `mymancave`, region `europe-west1`:

| Resource | Purpose |
| --- | --- |
| APIs: run, sqladmin, artifactregistry, secretmanager, iam, iamcredentials, sts, cloudresourcemanager, serviceusage, storage | Needed by the app stack and by keyless auth |
| Bucket `mymancave-fitzy-tfstate` | Terraform state for `infra/main` (versioned, uniform access, public access blocked) |
| Artifact Registry `fitzy` (Docker) | Images pushed by CI; cleanup keeps the 10 newest, deletes others after 30 days |
| SA `fitzy-runtime` | Identity of the Cloud Run service and migration job (`cloudsql.client`; secret access is granted per secret by `infra/main`) |
| SA `fitzy-deployer` | Identity CI impersonates; roles are listed and justified in `main.tf` |
| WIF pool `fitzy-github` + provider `github-oidc` | Accepts GitHub OIDC tokens only from `amilkareg2/fitzy` on `refs/heads/main` |

No service-account keys are created, and none should ever be.

## Steps

```bash
# 1. In Cloud Shell
gcloud config set project mymancave
git clone https://github.com/amilkareg2/fitzy.git
cd fitzy/infra/bootstrap

# 2. Optional but recommended: also pin the repository's numeric id, so a repo
#    re-created under the same name could not deploy.
#    (Cloud Shell has no gh by default; the public API works without auth.)
REPO_ID=$(curl -s https://api.github.com/repos/amilkareg2/fitzy | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
echo "github_repository_id = \"$REPO_ID\"" > terraform.tfvars   # git-ignored

# 3. Create everything
terraform init
terraform apply

# 4. Print the values for GitHub
terraform output github_variables
```

If `apply` fails on the first try with "API not enabled" or "permission denied" right
after enabling APIs, wait a minute and run `terraform apply` again (API enablement
and IAM changes take a little while to propagate).

## Configure GitHub

In the repository: **Settings > Secrets and variables > Actions > Variables** (the
*Variables* tab, not *Secrets*: none of these values are sensitive; they are
identifiers, and access is enforced by the WIF condition, not by secrecy).

| Variable | Value |
| --- | --- |
| `GCP_PROJECT_ID` | `mymancave` |
| `GCP_REGION` | `europe-west1` |
| `GCP_WIF_PROVIDER` | output `workload_identity_provider`, e.g. `projects/123456789/locations/global/workloadIdentityPools/fitzy-github/providers/github-oidc` |
| `GCP_DEPLOY_SA` | output `deployer_service_account`, i.e. `fitzy-deployer@mymancave.iam.gserviceaccount.com` |
| `FITZY_OWNER_EMAIL` (optional) | the owner email the app expects in `OWNER_EMAIL` |

Or with the GitHub CLI from your machine:

```bash
gh variable set GCP_PROJECT_ID   --repo amilkareg2/fitzy --body mymancave
gh variable set GCP_REGION       --repo amilkareg2/fitzy --body europe-west1
gh variable set GCP_WIF_PROVIDER --repo amilkareg2/fitzy --body "<workload_identity_provider>"
gh variable set GCP_DEPLOY_SA    --repo amilkareg2/fitzy --body "<deployer_service_account>"
```

The next push to `main` that touches `backend/`, `data/`, `infra/main/` or
`deploy.yml` deploys. The first deploy creates Cloud SQL and takes 10-15 minutes.
You can also start it from **Actions > Deploy > Run workflow** on `main`.

## Commit the provider lock files

Lock files pin provider checksums for every platform CI and you use. Generate them
in Cloud Shell and commit them (in a PR):

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
resources itself, by design. Destroying this stack revokes CI's access; destroy
`infra/main` first if you want everything gone (see `../README.md`).
