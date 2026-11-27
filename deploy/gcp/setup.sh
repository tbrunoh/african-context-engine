#!/usr/bin/env bash
# Stand up ACE on Google Cloud: the site and API, MCP, the snapshot refresh job, a global load balancer with a
# managed certificate and Cloud Armor, durable sessions in Firestore, the spend guard and the weekly model check.
#
#   PROJECT=your-project DOMAIN=ace.example.org bash deploy/gcp/setup.sh
#   BILLING_ACCOUNT defaults to the account linked to the project.
#
# Run it from a checkout of the release you want to deploy, in Cloud Shell or anywhere gcloud is signed in. Every step
# checks what exists first, so running it again is safe. It touches only the project you name.
set -euo pipefail

PROJECT="${PROJECT:?set PROJECT}"
REGION="${REGION:-africa-south1}"            # Johannesburg
SCHEDULER_REGION="${SCHEDULER_REGION:-europe-west1}"  # Cloud Scheduler has no Africa region
DOMAIN="${DOMAIN:?set DOMAIN, for example ace.korext.com}"
BUDGET_USD="${BUDGET_USD:-60}"
BUCKET="${BUCKET:-${PROJECT}-snapshots}"
REPO="${REPO:-ace}"
TAG="${TAG:-$(git describe --tags --always 2>/dev/null || echo manual)}"
COMMIT="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/ace:${TAG}"
NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
gc() { gcloud --project "$PROJECT" "$@"; }
exists() { "$@" >/dev/null 2>&1; }
sa() { echo "$1@${PROJECT}.iam.gserviceaccount.com"; }
step() { printf '\n== %s\n' "$*"; }

# Cloud Run takes traffic only from the load balancer, so Cloud Armor, HSTS and TLS 1.2 cannot be bypassed through
# the run.app address. Set INGRESS=all only to test a deployment before its domain resolves.
INGRESS="${INGRESS:-internal-and-cloud-load-balancing}"
# The site and MCP are public by turning off Cloud Run's invoker IAM check rather than granting allUsers, which an
# organisation with domain restricted sharing refuses.

step "APIs"
gc services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com \
  firestore.googleapis.com secretmanager.googleapis.com compute.googleapis.com cloudscheduler.googleapis.com \
  pubsub.googleapis.com logging.googleapis.com monitoring.googleapis.com billingbudgets.googleapis.com \
  iam.googleapis.com storage.googleapis.com

step "Logs stay in ${REGION}, for 30 days"
exists gc logging buckets describe ace-logs --location="$REGION" || \
  gc logging buckets create ace-logs --location="$REGION" --retention-days=30
gc logging sinks update _Default "logging.googleapis.com/projects/${PROJECT}/locations/${REGION}/buckets/ace-logs" --quiet

step "Service accounts, one per job, each with only what it needs"
for name in ace-web ace-mcp ace-refresh ace-scheduler ace-guard ace-pubsub ace-modelcheck ace-build; do
  # A new project may create only a few accounts a minute, so each creation is spaced out
  exists gc iam service-accounts describe "$(sa $name)" || { gc iam service-accounts create "$name" --display-name "$name"; sleep 15; }
done

step "Artifact Registry"
exists gc artifacts repositories describe "$REPO" --location="$REGION" || \
  gc artifacts repositories create "$REPO" --location="$REGION" --repository-format=docker
gc artifacts repositories set-cleanup-policies "$REPO" --location="$REGION" --policy=- <<'POLICY' >/dev/null
[{"name": "keep-last-ten", "action": {"type": "Keep"}, "mostRecentVersions": {"keepCount": 10}},
 {"name": "delete-older", "action": {"type": "Delete"}, "condition": {"olderThan": "2592000s"}}]
POLICY

step "Firestore in ${REGION}, with profiles expiring 24 hours after their last write"
exists gc firestore databases describe --database='(default)' || \
  gc firestore databases create --location="$REGION" --type=firestore-native
if ! gc firestore fields ttls list --format='value(name)' 2>/dev/null | grep -q 'profiles/fields/expires_at'; then
  gc firestore fields ttls update expires_at --collection-group=profiles --enable-ttl --async --quiet
fi
gc projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$(sa ace-web)" --role=roles/datastore.user --condition=None -q >/dev/null

step "Snapshot bucket in ${REGION}"
exists gcloud storage buckets describe "gs://${BUCKET}" || \
  gcloud storage buckets create "gs://${BUCKET}" --project "$PROJECT" --location="$REGION" --uniform-bucket-level-access --public-access-prevention
for name in ace-web ace-mcp; do
  gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" --member="serviceAccount:$(sa $name)" --role=roles/storage.objectViewer >/dev/null
done
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" --member="serviceAccount:$(sa ace-refresh)" --role=roles/storage.objectAdmin >/dev/null

step "Secrets"
if ! exists gc secrets describe ace-pseudonym-salt; then
  python3 -c 'import secrets; print(secrets.token_urlsafe(48), end="")' | gc secrets create ace-pseudonym-salt --data-file=- --replication-policy=user-managed --locations="$REGION"
fi
gc secrets add-iam-policy-binding ace-pseudonym-salt --member="serviceAccount:$(sa ace-web)" --role=roles/secretmanager.secretAccessor >/dev/null
if ! exists gc secrets describe ace-candidate-header; then
  python3 -c 'import secrets; print(secrets.token_urlsafe(24), end="")' | gc secrets create ace-candidate-header --data-file=- --replication-policy=user-managed --locations="$REGION"
fi
GEMINI=""
if exists gc secrets describe ace-gemini-key; then
  GEMINI="yes"
  for name in ace-web ace-modelcheck; do
    gc secrets add-iam-policy-binding ace-gemini-key --member="serviceAccount:$(sa $name)" --role=roles/secretmanager.secretAccessor >/dev/null
  done
fi

step "Build ${IMAGE} (tests, ruff and the quick benchmark run first)"
# The build account deploys revisions (run.developer, no IAM changes), pushes images and writes logs; it reads the
# uploaded source from the Cloud Build bucket only.
for role in roles/run.developer roles/artifactregistry.writer roles/logging.logWriter; do
  gc projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$(sa ace-build)" --role="$role" --condition=None -q >/dev/null
done
SOURCE_BUCKET="${PROJECT}_cloudbuild"
exists gcloud storage buckets describe "gs://${SOURCE_BUCKET}" || \
  gcloud storage buckets create "gs://${SOURCE_BUCKET}" --project "$PROJECT" --location="$REGION" --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets add-iam-policy-binding "gs://${SOURCE_BUCKET}" --member="serviceAccount:$(sa ace-build)" --role=roles/storage.objectViewer >/dev/null
for name in ace-web ace-mcp ace-refresh ace-guard ace-modelcheck; do
  gc iam service-accounts add-iam-policy-binding "$(sa $name)" --member="serviceAccount:$(sa ace-build)" --role=roles/iam.serviceAccountUser >/dev/null
done
gc secrets add-iam-policy-binding ace-candidate-header --member="serviceAccount:$(sa ace-build)" --role=roles/secretmanager.secretAccessor >/dev/null
gcloud builds submit --project "$PROJECT" --region="$REGION" --config deploy/gcp/cloudbuild.yaml \
  --gcs-source-staging-dir "gs://${SOURCE_BUCKET}/source" \
  --service-account "projects/${PROJECT}/serviceAccounts/$(sa ace-build)" \
  --substitutions="_IMAGE=${IMAGE},_COMMIT=${COMMIT},_REGION=${REGION},_DEPLOY=no" .

LLM_ENV=""
LLM_SECRET=""
if [ -n "$GEMINI" ]; then
  LLM_ENV=",ACE_LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai,ACE_LLM_MODEL=gemini-flash-latest,ACE_LLM_REASONING_EFFORT=${LLM_EFFORT:-low},ACE_LLM_TIMEOUT=2"
  LLM_SECRET=",ACE_LLM_API_KEY=ace-gemini-key:latest"
fi

step "ace-web: the site, the /try phone and the API"
gc run deploy ace-web --image "$IMAGE" --region "$REGION" --service-account "$(sa ace-web)" \
  --execution-environment gen2 --cpu 1 --memory 1Gi --concurrency 8 --min-instances 1 --max-instances 10 \
  --timeout 30 --no-invoker-iam-check --ingress "$INGRESS" \
  --set-env-vars "ACE_PUBLIC=1,ACE_PROFILE_STORE=firestore,ACE_HANDOFFS=count,ACE_FIRESTORE_COUNTS=1,ACE_SNAPSHOT_BASE=/mnt/snapshots,ACE_COMMIT=${COMMIT}${LLM_ENV}" \
  --set-secrets "ACE_PSEUDONYM_SALT=ace-pseudonym-salt:latest${LLM_SECRET}" \
  --add-volume "name=snapshots,type=cloud-storage,bucket=${BUCKET},readonly=true" \
  --add-volume-mount "volume=snapshots,mount-path=/mnt/snapshots" --quiet

step "ace-mcp: MCP over Streamable HTTP at /mcp"
gc run deploy ace-mcp --image "$IMAGE" --region "$REGION" --service-account "$(sa ace-mcp)" \
  --execution-environment gen2 --cpu 1 --memory 1Gi --concurrency 40 --min-instances 0 --max-instances 5 \
  --timeout 30 --no-invoker-iam-check --ingress "$INGRESS" \
  --command ace-mcp --args=--transport=http \
  --set-env-vars "ACE_MCP_ALLOWED_HOSTS=${DOMAIN},ACE_SNAPSHOT_BASE=/mnt/snapshots,ACE_COMMIT=${COMMIT}" \
  --add-volume "name=snapshots,type=cloud-storage,bucket=${BUCKET},readonly=true" \
  --add-volume-mount "volume=snapshots,mount-path=/mnt/snapshots" --quiet

step "ace-refresh: refresh, check and publish snapshot sets"
gc run jobs deploy ace-refresh --image "$IMAGE" --region "$REGION" --service-account "$(sa ace-refresh)" \
  --execution-environment gen2 --cpu 1 --memory 2Gi --task-timeout 3600 --max-retries 0 --parallelism 1 --tasks 1 \
  --command ace --args=refresh,--publish,/mnt/snapshots,--source=open_meteo,--source=cap \
  --add-volume "name=snapshots,type=cloud-storage,bucket=${BUCKET},mount-options=uid=10001;gid=10001" \
  --add-volume-mount "volume=snapshots,mount-path=/mnt/snapshots" --quiet
# The schedules pass each run its own sources, which needs the right to run with overrides
gc run jobs add-iam-policy-binding ace-refresh --region "$REGION" --member="serviceAccount:$(sa ace-scheduler)" --role=roles/run.jobsExecutorWithOverrides >/dev/null
if ! gcloud storage ls "gs://${BUCKET}/manifest.json" >/dev/null 2>&1; then
  echo "Publishing the first snapshot set"
  gc run jobs execute ace-refresh --region "$REGION" --wait
fi

step "Schedules: warnings every hour, weather twice a day, market prices every Monday"
schedule() {  # name, cron, comma separated ace refresh arguments
  local uri="https://run.googleapis.com/v2/projects/${PROJECT}/locations/${REGION}/jobs/ace-refresh:run"
  local args; args="$(python3 -c 'import json,sys; print(json.dumps({"overrides":{"containerOverrides":[{"args":sys.argv[1].split(",")}]}}))' "$3")"
  if exists gc scheduler jobs describe "$1" --location "$SCHEDULER_REGION"; then
    gc scheduler jobs update http "$1" --location "$SCHEDULER_REGION" --schedule "$2" --uri "$uri" --message-body "$args" \
      --oauth-service-account-email "$(sa ace-scheduler)" --time-zone UTC --quiet >/dev/null
  else
    gc scheduler jobs create http "$1" --location "$SCHEDULER_REGION" --schedule "$2" --uri "$uri" --http-method POST \
      --message-body "$args" --oauth-service-account-email "$(sa ace-scheduler)" --time-zone UTC --quiet >/dev/null
  fi
}
schedule ace-refresh-warnings "7 * * * *" "refresh,--publish,/mnt/snapshots,--source,cap"
schedule ace-refresh-weather "23 4,16 * * *" "refresh,--publish,/mnt/snapshots,--source,open_meteo"
schedule ace-refresh-prices "41 10 * * 1" "refresh,--publish,/mnt/snapshots,--source,wfp_prices"

step "Global load balancer: managed certificate, HTTP redirect, Cloud Armor, /mcp to ace-mcp"
exists gc compute addresses describe ace-ip --global || gc compute addresses create ace-ip --global --ip-version IPV4
IP="$(gc compute addresses describe ace-ip --global --format='value(address)')"
for svc in ace-web ace-mcp; do
  exists gc compute network-endpoint-groups describe "${svc}-neg" --region "$REGION" || \
    gc compute network-endpoint-groups create "${svc}-neg" --region "$REGION" --network-endpoint-type serverless --cloud-run-service "$svc"
done
exists gc compute network-endpoint-groups describe ace-web-candidate-neg --region "$REGION" || \
  gc compute network-endpoint-groups create ace-web-candidate-neg --region "$REGION" --network-endpoint-type serverless \
    --cloud-run-service ace-web --cloud-run-tag candidate
exists gc compute security-policies describe ace-armor || gc compute security-policies create ace-armor \
  --description "ACE: per address limits, generous because many mobile users share one carrier address"
exists gc compute security-policies rules describe 1000 --security-policy ace-armor || \
  gc compute security-policies rules create 1000 --security-policy ace-armor --expression "true" \
    --action throttle --rate-limit-threshold-count 300 --rate-limit-threshold-interval-sec 60 \
    --conform-action allow --exceed-action deny-429 --enforce-on-key IP
for b in ace-web ace-mcp ace-web-candidate; do
  if ! exists gc compute backend-services describe "${b}-backend" --global; then
    gc compute backend-services create "${b}-backend" --global --load-balancing-scheme EXTERNAL_MANAGED \
      --custom-response-header "Strict-Transport-Security: max-age=31536000; includeSubDomains"
    gc compute backend-services add-backend "${b}-backend" --global --network-endpoint-group "${b}-neg" \
      --network-endpoint-group-region "$REGION"
  fi
  gc compute backend-services update "${b}-backend" --global --security-policy ace-armor --quiet >/dev/null
done
exists gc compute ssl-policies describe ace-tls --global || \
  gc compute ssl-policies create ace-tls --global --profile MODERN --min-tls-version 1.2
CANDIDATE="$(gc secrets versions access latest --secret ace-candidate-header)"
cat > /tmp/ace-urlmap.yaml <<YAML
name: ace-urlmap
defaultService: https://www.googleapis.com/compute/v1/projects/${PROJECT}/global/backendServices/ace-web-backend
hostRules:
- hosts: ['${DOMAIN}']
  pathMatcher: ace
pathMatchers:
- name: ace
  defaultService: https://www.googleapis.com/compute/v1/projects/${PROJECT}/global/backendServices/ace-web-backend
  routeRules:
  - priority: 1
    matchRules:
    - prefixMatch: /mcp
    service: https://www.googleapis.com/compute/v1/projects/${PROJECT}/global/backendServices/ace-mcp-backend
  - priority: 2
    matchRules:
    - prefixMatch: /
      headerMatches:
      - headerName: x-ace-candidate
        exactMatch: '${CANDIDATE}'
    service: https://www.googleapis.com/compute/v1/projects/${PROJECT}/global/backendServices/ace-web-candidate-backend
YAML
gc compute url-maps import ace-urlmap --global --source /tmp/ace-urlmap.yaml --quiet
rm -f /tmp/ace-urlmap.yaml
exists gc compute ssl-certificates describe ace-cert --global || \
  gc compute ssl-certificates create ace-cert --global --domains "$DOMAIN"
exists gc compute target-https-proxies describe ace-https --global || \
  gc compute target-https-proxies create ace-https --global --url-map ace-urlmap --ssl-certificates ace-cert
gc compute target-https-proxies update ace-https --global --ssl-policy ace-tls --quiet >/dev/null
exists gc compute forwarding-rules describe ace-https-rule --global || \
  gc compute forwarding-rules create ace-https-rule --global --load-balancing-scheme EXTERNAL_MANAGED \
    --address ace-ip --target-https-proxy ace-https --ports 443
if ! exists gc compute url-maps describe ace-redirect --global; then
  cat > /tmp/ace-redirect.yaml <<YAML
name: ace-redirect
defaultUrlRedirect:
  httpsRedirect: true
  redirectResponseCode: MOVED_PERMANENTLY_DEFAULT
YAML
  gc compute url-maps import ace-redirect --global --source /tmp/ace-redirect.yaml --quiet
  rm -f /tmp/ace-redirect.yaml
fi
exists gc compute target-http-proxies describe ace-http --global || \
  gc compute target-http-proxies create ace-http --global --url-map ace-redirect
exists gc compute forwarding-rules describe ace-http-rule --global || \
  gc compute forwarding-rules create ace-http-rule --global --load-balancing-scheme EXTERNAL_MANAGED \
    --address ace-ip --target-http-proxy ace-http --ports 80

step "Spend guard: Gemini off at 90% of \$${BUDGET_USD}, the demo paused at 100%"
exists gc pubsub topics describe ace-budget || gc pubsub topics create ace-budget
gc run deploy ace-guard --image "$IMAGE" --region "$REGION" --service-account "$(sa ace-guard)" \
  --cpu 1 --memory 512Mi --min-instances 0 --max-instances 1 --no-allow-unauthenticated --ingress internal \
  --command gunicorn --args=--bind=:8080,--workers=1,ace_engine.ops.guard:app \
  --set-env-vars "^@^ACE_GUARD_PROJECT=${PROJECT}@ACE_GUARD_REGION=${REGION}@ACE_GUARD_SERVICES=ace-web,ace-mcp@ACE_GUARD_MIN_INSTANCES=ace-web=1" --quiet
for svc in ace-web ace-mcp; do
  gc run services add-iam-policy-binding "$svc" --region "$REGION" --member="serviceAccount:$(sa ace-guard)" --role=roles/run.developer >/dev/null
  gc iam service-accounts add-iam-policy-binding "$(sa $svc)" --member="serviceAccount:$(sa ace-guard)" --role=roles/iam.serviceAccountUser >/dev/null
done
gc run services add-iam-policy-binding ace-guard --region "$REGION" --member="serviceAccount:$(sa ace-pubsub)" --role=roles/run.invoker >/dev/null
gc iam service-accounts add-iam-policy-binding "$(sa ace-pubsub)" \
  --member="serviceAccount:service-${NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com" --role=roles/iam.serviceAccountTokenCreator >/dev/null
GUARD_URL="$(gc run services describe ace-guard --region "$REGION" --format='value(status.url)')"
exists gc pubsub subscriptions describe ace-budget-guard || gc pubsub subscriptions create ace-budget-guard \
  --topic ace-budget --push-endpoint "$GUARD_URL" --push-auth-service-account "$(sa ace-pubsub)" --ack-deadline 60
BILLING_ACCOUNT="${BILLING_ACCOUNT:-$(gcloud billing projects describe "$PROJECT" --format='value(billingAccountName)' 2>/dev/null | sed 's#^billingAccounts/##')}"
if [ -n "${BILLING_ACCOUNT:-}" ]; then
  BUDGET="$(gcloud billing budgets list --billing-account "$BILLING_ACCOUNT" --filter="displayName='ACE monthly cap'" --format='value(name)' | head -1)"
  if [ -z "$BUDGET" ]; then
    # Publishing budget alerts to Pub/Sub grants Google's billing alert account on the topic, which an organisation
    # with domain restricted sharing refuses. The budget then sends email alerts only, and the guard waits for an
    # exception; cap Gemini with a daily request quota in the meantime (see README).
    if ! gcloud billing budgets create --billing-account "$BILLING_ACCOUNT" --display-name "ACE monthly cap" \
      --budget-amount "${BUDGET_USD}USD" --filter-projects "projects/${PROJECT}" \
      --threshold-rule percent=0.9 --threshold-rule percent=1.0 \
      --notifications-rule-pubsub-topic "projects/${PROJECT}/topics/ace-budget"; then
      echo "The budget could not publish to Pub/Sub, so it sends email alerts only and the spend guard is idle."
      gcloud billing budgets create --billing-account "$BILLING_ACCOUNT" --display-name "ACE monthly cap" \
        --budget-amount "${BUDGET_USD}USD" --filter-projects "projects/${PROJECT}" \
        --threshold-rule percent=0.9 --threshold-rule percent=1.0
    fi
  fi
else
  echo "BILLING_ACCOUNT not set: create the ACE monthly cap budget with its Pub/Sub topic by hand (see README)."
fi

if [ -n "$GEMINI" ]; then
  step "Weekly model check"
  gc run jobs deploy ace-modelcheck --image "$IMAGE" --region "$REGION" --service-account "$(sa ace-modelcheck)" \
    --task-timeout 600 --max-retries 0 --command python --args=-m,ace_engine.ops.model_check \
    --set-env-vars "ACE_GUARD_PROJECT=${PROJECT},ACE_GUARD_REGION=${REGION},ACE_LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai,ACE_LLM_REASONING_EFFORT=${LLM_EFFORT:-low}" \
    --set-secrets "ACE_LLM_API_KEY=ace-gemini-key:latest" --quiet
  gc run services add-iam-policy-binding ace-web --region "$REGION" --member="serviceAccount:$(sa ace-modelcheck)" --role=roles/run.developer >/dev/null
  gc iam service-accounts add-iam-policy-binding "$(sa ace-web)" --member="serviceAccount:$(sa ace-modelcheck)" --role=roles/iam.serviceAccountUser >/dev/null
  gc run jobs add-iam-policy-binding ace-modelcheck --region "$REGION" --member="serviceAccount:$(sa ace-scheduler)" --role=roles/run.invoker >/dev/null
  uri="https://run.googleapis.com/v2/projects/${PROJECT}/locations/${REGION}/jobs/ace-modelcheck:run"
  exists gc scheduler jobs describe ace-modelcheck --location "$SCHEDULER_REGION" || \
    gc scheduler jobs create http ace-modelcheck --location "$SCHEDULER_REGION" --schedule "13 6 * * 2" --uri "$uri" \
      --http-method POST --oauth-service-account-email "$(sa ace-scheduler)" --time-zone UTC --quiet >/dev/null
fi

step "Done"
cat <<DONE
ace-web:  $(gc run services describe ace-web --region "$REGION" --format='value(status.url)')
ace-mcp:  $(gc run services describe ace-mcp --region "$REGION" --format='value(status.url)')

Point ${DOMAIN} at the load balancer:   A   ${IP}
The managed certificate becomes active within about an hour of the record resolving. Cloud Run already takes
traffic only from the load balancer. Then run
  python3 deploy/gcp/smoke.py https://${DOMAIN}
DONE
