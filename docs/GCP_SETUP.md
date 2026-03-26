# 🚀 GCP Cloud Run Setup Guide

## Overview

This guide walks you through setting up the CI/CD pipeline to deploy the **Monday.com BI Agent** to **Google Cloud Run** using the GitHub Actions workflow.

**GCP Project:** `project-tai-aiinterviewer`  
**Region:** `asia-south1` (Mumbai)  
**Service:** `monday-bi-agent`

---

## Prerequisites

- Google Cloud CLI (`gcloud`) installed
- Owner/Editor access to `project-tai-aiinterviewer`
- GitHub repo admin access

---

## Step 1: Enable Required GCP APIs

```bash
gcloud config set project project-tai-aiinterviewer

gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com
```

## Step 2: Create a Service Account

```bash
# Create the service account
gcloud iam service-accounts create github-actions-deployer \
  --display-name="GitHub Actions Cloud Run Deployer" \
  --project=project-tai-aiinterviewer

# Grant necessary roles
SA_EMAIL="github-actions-deployer@project-tai-aiinterviewer.iam.gserviceaccount.com"

# Cloud Run Admin (deploy services)
gcloud projects add-iam-policy-binding project-tai-aiinterviewer \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin"

# Artifact Registry Writer (push Docker images)
gcloud projects add-iam-policy-binding project-tai-aiinterviewer \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.writer"

# Service Account User (act as the Cloud Run service account)
gcloud projects add-iam-policy-binding project-tai-aiinterviewer \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser"

# Secret Manager Accessor (read secrets at deploy time)
gcloud projects add-iam-policy-binding project-tai-aiinterviewer \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"
```

## Step 3: Set Up Workload Identity Federation (Keyless Auth)

This eliminates the need for service account JSON keys — much more secure!

```bash
# Create a Workload Identity Pool
gcloud iam workload-identity-pools create "github-pool" \
  --location="global" \
  --display-name="GitHub Actions Pool" \
  --project=project-tai-aiinterviewer

# Create a Provider for GitHub
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --project=project-tai-aiinterviewer

# Allow the GitHub repo to impersonate the service account
gcloud iam service-accounts add-iam-policy-binding \
  "${SA_EMAIL}" \
  --project=project-tai-aiinterviewer \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe project-tai-aiinterviewer --format='value(projectNumber)')/locations/global/workloadIdentityPools/github-pool/attribute.repository/gauravbhoi-design/agentic_chatbot"
```

### Get the Workload Identity Provider resource name:

```bash
gcloud iam workload-identity-pools providers describe github-provider \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --project=project-tai-aiinterviewer \
  --format="value(name)"
```

This will output something like:
```
projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider
```

## Step 4: Store Application Secrets in GCP Secret Manager

```bash
# Monday.com API Key
echo -n "your-monday-api-key" | gcloud secrets create MONDAY_API_KEY \
  --data-file=- \
  --replication-policy="automatic" \
  --project=project-tai-aiinterviewer

# OpenAI API Key
echo -n "your-openai-api-key" | gcloud secrets create OPENAI_API_KEY \
  --data-file=- \
  --replication-policy="automatic" \
  --project=project-tai-aiinterviewer

# Board IDs
echo -n "your-deals-board-id" | gcloud secrets create DEALS_BOARD_ID \
  --data-file=- \
  --replication-policy="automatic" \
  --project=project-tai-aiinterviewer

echo -n "your-workorders-board-id" | gcloud secrets create WORKORDERS_BOARD_ID \
  --data-file=- \
  --replication-policy="automatic" \
  --project=project-tai-aiinterviewer
```

### Grant Cloud Run's compute service account access to secrets:

```bash
PROJECT_NUMBER=$(gcloud projects describe project-tai-aiinterviewer --format='value(projectNumber)')
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for SECRET in MONDAY_API_KEY OPENAI_API_KEY DEALS_BOARD_ID WORKORDERS_BOARD_ID; do
  gcloud secrets add-iam-policy-binding ${SECRET} \
    --member="serviceAccount:${COMPUTE_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --project=project-tai-aiinterviewer
done
```

## Step 5: Configure GitHub Repository Secrets

Go to your repository → **Settings** → **Secrets and variables** → **Actions** and add:

| Secret Name | Value |
|-------------|-------|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | The full provider resource name from Step 3 (e.g., `projects/123456/locations/global/workloadIdentityPools/github-pool/providers/github-provider`) |
| `GCP_SERVICE_ACCOUNT` | `github-actions-deployer@project-tai-aiinterviewer.iam.gserviceaccount.com` |

## Step 6: Trigger the Pipeline

Push to `main` or create a pull request:

```bash
git add .
git commit -m "feat: trigger first CI/CD deployment"
git push origin main
```

The pipeline will:
1. ✅ Run lint & security checks
2. 🐳 Build multi-stage Docker image
3. 📤 Push to Artifact Registry
4. 🚀 Deploy to Cloud Run
5. 🏥 Verify with health check

---

## Monitoring & Troubleshooting

### View Cloud Run logs:
```bash
gcloud run services logs read monday-bi-agent \
  --region=asia-south1 \
  --project=project-tai-aiinterviewer \
  --limit=50
```

### Check service status:
```bash
gcloud run services describe monday-bi-agent \
  --region=asia-south1 \
  --project=project-tai-aiinterviewer
```

### View revision details:
```bash
gcloud run revisions list \
  --service=monday-bi-agent \
  --region=asia-south1 \
  --project=project-tai-aiinterviewer
```

### Update a secret:
```bash
echo -n "new-value" | gcloud secrets versions add MONDAY_API_KEY --data-file=-
# Then redeploy to pick up the new secret version
```

---

## Architecture Diagram

```
┌─────────────┐     push/PR     ┌──────────────────────┐
│   GitHub     │ ──────────────► │  GitHub Actions      │
│   Repo       │                 │                      │
└─────────────┘                 │  1. Lint & Security   │
                                │  2. Docker Build      │
                                │  3. Push to AR        │
                                │  4. Deploy Cloud Run  │
                                │  5. Health Check      │
                                └──────────┬───────────┘
                                           │
                        ┌──────────────────┼──────────────────┐
                        ▼                  ▼                  ▼
              ┌─────────────────┐ ┌────────────────┐ ┌───────────────┐
              │ Artifact        │ │ Cloud Run      │ │ Secret        │
              │ Registry        │ │ (asia-south1)  │ │ Manager       │
              │                 │ │                │ │               │
              │ Docker images   │ │ monday-bi-     │ │ MONDAY_API_KEY│
              │ tagged by       │ │ agent          │ │ OPENAI_API_KEY│
              │ commit SHA      │ │ 0-5 instances  │ │ BOARD_IDS     │
              └─────────────────┘ └────────────────┘ └───────────────┘
```

## Cost Estimate

With Cloud Run's pay-per-use model:
- **Min instances: 0** → No cost when idle
- **Max instances: 5** → Scales for traffic
- **1 vCPU + 1 GB RAM** per instance
- **Estimated: $5-15/month** for light usage (< 1000 requests/day)
