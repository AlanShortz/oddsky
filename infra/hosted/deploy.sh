#!/usr/bin/env bash
# Build and deploy the hosted observatory to Cloud Run (project oddsky-sky-br3c3, us-central1).
# The image is built remotely by Cloud Build, so nothing heavy runs on this machine.
#   bash infra/hosted/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
P=oddsky-sky-br3c3 R=us-central1
IMG="$R-docker.pkg.dev/$P/oddsky/api:$(date -u +%Y%m%d-%H%M%S)"
cp infra/hosted/Dockerfile Dockerfile.cloudbuild
trap 'rm -f Dockerfile.cloudbuild' EXIT
gcloud builds submit --project "$P" --region "$R" --config /dev/stdin . <<YAML
steps:
- name: gcr.io/cloud-builders/docker
  args: [build, -f, Dockerfile.cloudbuild, -t, "$IMG", .]
images: ["$IMG"]
options: { machineType: E2_HIGHCPU_8 }
YAML
gcloud run deploy oddsky-api --project "$P" --region "$R" --image "$IMG" \
  --service-account "oddsky-api@$P.iam.gserviceaccount.com" --allow-unauthenticated \
  --cpu 1 --memory 2Gi --concurrency 20 --timeout 900 --min-instances 1 --max-instances 3 --cpu-boost \
  --set-env-vars "ODDSKY_DB=firestore,ODDSKY_BUCKET=$P-data,GOOGLE_CLOUD_PROJECT=$P,ODDSKY_RP_ID=oddsky.ai,ODDSKY_ORIGINS=https://oddsky.ai;https://www.oddsky.ai" \
  --set-secrets "ODDSKY_ADMIN_TOKEN=oddsky-admin-token:latest"
