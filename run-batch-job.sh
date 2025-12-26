#!/bin/bash
set -euo pipefail

# ==============================================================================
# /app/batch/run-batch.sh  (REPLACEMENT)
#
# Goal:
# - Do NOT redownload code every run
# - Do NOT recreate venv / reinstall deps every run
# - DO refresh environment each run (Secrets Manager -> systemd/shell-safe env)
# - Run batch_generate.py using the prebuilt venv in /opt/motiv8-be
# - Shut down after completion (optional, kept to match your current behavior)
#
# Assumptions:
# - /opt/motiv8-be exists and contains:
#     - batch_generate.py
#     - venv/ with dependencies installed
# - Instance role can read AppSecretsArn from Secrets Manager
# ==============================================================================

REGION="us-east-1"

# If you want this script to be completely self-contained, hardcode the secret ARN:
# APP_SECRETS_ARN="arn:aws:secretsmanager:us-east-1:901478075158:secret:production/motiv8/app-secrets-9kdThl"
#
# Otherwise, it can be passed in via environment (recommended if you run under systemd):
APP_SECRETS_ARN="${APP_SECRETS_ARN:-}"

LOG_FILE="/var/log/motiv8-batch.log"
ENV_FILE="/etc/motiv8-batch.env"
APP_DIR="/opt/motiv8-be"
PY="${APP_DIR}/venv/bin/python"

# Log everything to file + console
mkdir -p "$(dirname "$LOG_FILE")"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "================================================"
echo "motiv8me Batch Job"
echo "Started: $(date -u) (UTC)"
echo "Host: $(hostname)"
echo "================================================"

# Sanity checks
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

# Get instance ID and read email filter tag if present
INSTANCE_ID=$(ec2-metadata --instance-id | cut -d " " -f 2)
echo "Instance ID: $INSTANCE_ID"

# Check for BatchEmailFilter tag
BATCH_EMAIL=$(aws ec2 describe-tags \
  --region "$REGION" \
  --filters "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=BatchEmailFilter" \
  --query 'Tags[0].Value' \
  --output text 2>/dev/null || echo "None")

if [ "$BATCH_EMAIL" != "None" ] && [ -n "$BATCH_EMAIL" ]; then
  echo "Email filter detected: $BATCH_EMAIL"
  export BATCH_EMAIL_FILTER="$BATCH_EMAIL"
else
  echo "No email filter set - processing all users"
  unset BATCH_EMAIL_FILTER
fi

# Fetch secrets fresh each run (so no stale DB config can linger)
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

# Write a shell-safe env file with proper quoting (spaces, special chars, etc.)
echo "Writing shell-safe env to $ENV_FILE ..."
python3 - <<'PY'
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

# Load env for this process (so python sees it)
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# Helpful debug (doesn't print passwords; only host/db name if present)
echo "Env loaded. DB_HOST=${DB_HOST:-<unset>} DB_NAME=${DB_NAME:-<unset>} AWS_REGION=${AWS_REGION:-<unset>}"

# Extra guardrail: show which DB SQLAlchemy is pointing at (masks password)
echo "Verifying SQLAlchemy engine target..."
"$PY" - <<'PY'
from database import engine
print("engine.url =", engine.url)
PY

echo "Running batch_generate.py..."
"$PY" batch_generate.py

echo "Batch job completed successfully at $(date -u) (UTC)"
echo "================================================"

# Optional: shutdown behavior (kept to match your current design)
echo "Shutting down instance in 5 minutes..."
sleep 300
sudo shutdown -h now
