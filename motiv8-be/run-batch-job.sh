#!/bin/bash
set -euo pipefail

# ==============================================================================
# /opt/motiv8-be/run-batch-job.sh
#
# Goal:
# - Do NOT redownload code every run
# - Do NOT recreate venv / reinstall deps every run
# - DO refresh environment each run (Secrets Manager -> shell-safe env file)
# - Run batch_generate.py using the prebuilt venv in /opt/motiv8-be
#
# Assumptions:
# - /opt/motiv8-be exists and contains venv/ and batch_generate.py
# - Instance role can read AppSecretsArn from Secrets Manager
# - Optional EC2 tag BatchEmailFilter controls BATCH_EMAIL_FILTER behavior
# - EC2 tag RunBatch=true gates whether the batch actually runs
# ==============================================================================

REGION="${AWS_REGION:-us-east-1}"

APP_SECRETS_ARN="${APP_SECRETS_ARN:-}"
LOG_FILE="/var/log/motiv8-batch.log"
ENV_FILE="/etc/motiv8-batch.env"
APP_DIR="/opt/motiv8-be"
PY="${APP_DIR}/venv/bin/python"
DEPLOY_VERSION_FILE="${APP_DIR}/.deploy-version"
TARGET_VERSION="${BATCH_DEPLOY_VERSION:-}"
CURRENT_VERSION=""
if [ -f "$DEPLOY_VERSION_FILE" ]; then
  CURRENT_VERSION="$(cat "$DEPLOY_VERSION_FILE" || true)"
fi
UPLOADS_BUCKET="${UPLOADS_BUCKET:-}"

mkdir -p "$(dirname "$LOG_FILE")"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "================================================"
echo "motiv8me Batch Job"
echo "Started: $(date -u) (UTC)"
echo "Host: $(hostname)"
echo "Region: $REGION"
echo "================================================"

if [ ! -d "$APP_DIR" ]; then
  echo "ERROR: $APP_DIR does not exist. (UserData should provision it.)"
  exit 1
fi

if [ ! -x "$PY" ]; then
  echo "ERROR: Python venv not found at $PY"
  echo "Expected $APP_DIR/venv to exist with dependencies installed."
  exit 1
fi

cd "$APP_DIR"

# ------------------------------------------------------------------------------
# Refresh code ONLY when BATCH_DEPLOY_VERSION changes
# (UserData does not rerun on stop/start, so this is how we pick up new deploys.)
# ------------------------------------------------------------------------------
if [ -n "$TARGET_VERSION" ] && [ "$CURRENT_VERSION" != "$TARGET_VERSION" ]; then
  echo "Deploy version changed (${CURRENT_VERSION:-<none>} -> $TARGET_VERSION). Updating /opt/motiv8-be from S3..."

  : "${UPLOADS_BUCKET:?UPLOADS_BUCKET must be set (from systemd Environment=)}"

  aws s3 cp \
    "s3://${UPLOADS_BUCKET}/deployment/motiv8-be.tar.gz" \
    /tmp/motiv8-be.tar.gz \
    --region "$REGION"

  # Extract into staging root. Tar contains top-level motiv8-be/, so extract to /opt.
  rm -rf /opt/motiv8-be.new
  mkdir -p /opt/motiv8-be.new
  tar -xzf /tmp/motiv8-be.tar.gz -C /opt/motiv8-be.new
  rm -f /tmp/motiv8-be.tar.gz

  # After extraction, staging path is /opt/motiv8-be.new/motiv8-be
  STAGED="/opt/motiv8-be.new/motiv8-be"
  if [ ! -d "$STAGED" ]; then
    echo "ERROR: expected staged dir $STAGED not found after untar"
    exit 1
  fi

  # Preserve existing venv into staged tree if artifact doesn't include one (it doesn't)
  if [ -d "${APP_DIR}/venv" ] && [ ! -d "${STAGED}/venv" ]; then
    echo "Preserving existing venv into staged tree..."
    cp -a "${APP_DIR}/venv" "${STAGED}/venv"
  fi

  echo "$TARGET_VERSION" > "${STAGED}/.deploy-version"

  echo "Swapping in updated code..."
  mv /opt/motiv8-be "/opt/motiv8-be.old.$(date +%s)" || true
  mv "$STAGED" /opt/motiv8-be
  rm -rf /opt/motiv8-be.new

  echo "Update complete; re-execing from new code..."
  exec /bin/bash "/opt/motiv8-be/run-batch-job.sh"
else
  echo "Deploy version unchanged (${CURRENT_VERSION:-<none>}). Using existing code."
fi

# --- Instance ID ---
if command -v ec2-metadata >/dev/null 2>&1; then
  INSTANCE_ID="$(ec2-metadata --instance-id | awk '{print $2}')"
else
  # fallback
  INSTANCE_ID="$(curl -fsS http://169.254.169.254/latest/meta-data/instance-id)"
fi
echo "Instance ID: $INSTANCE_ID"

# --- Gate: only run when RunBatch=true ---
RUNBATCH="$(aws ec2 describe-tags \
  --region "$REGION" \
  --filters "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=RunBatch" \
  --query 'Tags[0].Value' \
  --output text 2>/dev/null || echo "None")"

if [ "$RUNBATCH" != "true" ]; then
  echo "RunBatch tag not set to true (value: ${RUNBATCH:-<empty>}). Skipping batch run."
  echo "================================================"
  exit 0
fi

echo "RunBatch=true detected. Proceeding with batch run."

# --- Read BatchEmailFilter from EC2 tags if present ---
BATCH_EMAIL="$(aws ec2 describe-tags \
  --region "$REGION" \
  --filters "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=BatchEmailFilter" \
  --query 'Tags[0].Value' \
  --output text 2>/dev/null || echo "None")"

if [ "$BATCH_EMAIL" != "None" ] && [ -n "$BATCH_EMAIL" ]; then
  echo "Email filter detected: $BATCH_EMAIL"
  export BATCH_EMAIL_FILTER="$BATCH_EMAIL"
else
  echo "No email filter set - processing all users"
  unset BATCH_EMAIL_FILTER
fi

# --- Fetch secrets fresh each run ---
if [ -z "$APP_SECRETS_ARN" ]; then
  echo "ERROR: APP_SECRETS_ARN is not set."
  echo "Set it in the systemd unit Environment= or export it before running."
  exit 1
fi

echo "Fetching secrets from Secrets Manager..."
SECRETS_JSON="$(aws secretsmanager get-secret-value \
  --secret-id "$APP_SECRETS_ARN" \
  --region "$REGION" \
  --query SecretString \
  --output text)"

echo "Writing shell-safe env to $ENV_FILE ..."
ENV_FILE="$ENV_FILE" SECRETS_JSON="$SECRETS_JSON" python3 - <<'PY'
import json, os, shlex
from pathlib import Path

env_file = Path(os.environ["ENV_FILE"])
secrets = json.loads(os.environ["SECRETS_JSON"])

lines = []
for k, v in secrets.items():
    lines.append(f"{k}={shlex.quote(str(v))}")

env_file.write_text("\n".join(lines) + "\n")
PY

chmod 600 "$ENV_FILE"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

echo "Env loaded. DB_HOST=${DB_HOST:-<unset>} DB_NAME=${DB_NAME:-<unset>} AWS_REGION=${AWS_REGION:-<unset>}"

echo "Verifying SQLAlchemy engine target..."
"$PY" - <<'PY'
from database import engine
print("engine.url =", engine.url)
PY

echo "Running batch_generate.py..."
"$PY" batch_generate.py

echo "Batch job completed successfully at $(date -u) (UTC)"
echo "================================================"

# --- Clear RunBatch tag so restarts won't re-run the batch ---
echo "Clearing RunBatch tag..."
aws ec2 delete-tags \
  --region "$REGION" \
  --resources "$INSTANCE_ID" \
  --tags Key=RunBatch,Value=true 2>/dev/null || true

echo "Shutting down instance in 5 minutes..."
sleep 300
sudo shutdown -h now
