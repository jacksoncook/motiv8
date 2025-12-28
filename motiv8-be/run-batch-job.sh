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
# ==============================================================================

REGION="${AWS_REGION:-us-east-1}"

APP_SECRETS_ARN="${APP_SECRETS_ARN:-}"
LOG_FILE="/var/log/motiv8-batch.log"
ENV_FILE="/etc/motiv8-batch.env"
APP_DIR="/opt/motiv8-be"
PY="${APP_DIR}/venv/bin/python"
DEPLOY_VERSION_FILE="${APP_DIR}/.deploy-version"
TARGET_VERSION="${BATCH_DEPLOY_VERSION:-}"
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
  echo "Deploy version changed ($CURRENT_VERSION -> $TARGET_VERSION). Updating /opt/motiv8-be from S3..."

  : "${UPLOADS_BUCKET:?UPLOADS_BUCKET must be set (from systemd Environment=)}"

  aws s3 cp \
    "s3://${UPLOADS_BUCKET}/deployment/motiv8-be.tar.gz" \
    /tmp/motiv8-be.tar.gz \
    --region "$REGION"

  # Extract into a fresh directory, then swap atomically.
  rm -rf /opt/motiv8-be.new
  mkdir -p /opt/motiv8-be.new
  tar -xzf /tmp/motiv8-be.tar.gz -C /opt
  rm -f /tmp/motiv8-be.tar.gz

  # IMPORTANT:
  # Your tar currently extracts to /opt/motiv8-be (based on your UserData).
  # So ensure venv persists by moving the existing venv over if needed.
  if [ -d "${APP_DIR}/venv" ] && [ ! -d "/opt/motiv8-be/venv" ]; then
    echo "Preserving existing venv..."
    mv "${APP_DIR}/venv" "/opt/motiv8-be/venv"
  fi

  echo "$TARGET_VERSION" > "/opt/motiv8-be/.deploy-version"
  echo "Update complete; re-execing from new code..."
  exec /bin/bash "/opt/motiv8-be/run-batch-job.sh"
else
  echo "Deploy version unchanged ($CURRENT_VERSION). Using existing code."
fi

# --- Read BatchEmailFilter from EC2 tags if present ---
if command -v ec2-metadata >/dev/null 2>&1; then
  INSTANCE_ID="$(ec2-metadata --instance-id | awk '{print $2}')"
else
  # fallback
  INSTANCE_ID="$(curl -fsS http://169.254.169.254/latest/meta-data/instance-id)"
fi
echo "Instance ID: $INSTANCE_ID"

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

echo "Shutting down instance in 5 minutes..."
sleep 300
sudo shutdown -h now
