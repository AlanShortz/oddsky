#!/usr/bin/env bash
# Switch on "Continue with GitHub" or "Continue with Google": store the OAuth client's id and secret in
# Secret Manager, then redeploy. Run once per provider:
#   bash infra/hosted/set-oauth.sh github     (or google)
# It asks for the two values; the secret is read without echo and never printed.
#
# Where to get them (callback URLs must match exactly):
#   GitHub: https://github.com/settings/applications/new
#     Homepage URL: https://oddsky.ai   Callback URL: https://oddsky.ai/api/oauth/github/callback
#   Google: https://console.cloud.google.com/auth/clients/create?project=oddsky-sky-br3c3
#     (OAuth consent screen first: External, app name Oddsky, then Publish)
#     Type: Web application   Authorized redirect URI: https://oddsky.ai/api/oauth/google/callback
set -euo pipefail
P=oddsky-sky-br3c3 SA="oddsky-api@oddsky-sky-br3c3.iam.gserviceaccount.com"
prov="${1:?usage: set-oauth.sh github|google}"
read -r -p "$prov client ID: " CID
read -r -s -p "$prov client secret (hidden): " SEC; echo
for kind in id secret; do
  name="oddsky-$prov-client-$kind"; val=$([ "$kind" = id ] && echo -n "$CID" || echo -n "$SEC")
  if gcloud secrets describe "$name" --project "$P" >/dev/null 2>&1; then
    printf %s "$val" | gcloud secrets versions add "$name" --data-file=- --project "$P" >/dev/null
  else
    printf %s "$val" | gcloud secrets create "$name" --data-file=- --project "$P" >/dev/null
  fi
  gcloud secrets add-iam-policy-binding "$name" --member "serviceAccount:$SA" --role roles/secretmanager.secretAccessor --project "$P" >/dev/null
done
echo "stored; redeploying the service"
bash "$(dirname "$0")/deploy.sh"
