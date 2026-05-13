#!/usr/bin/env bash
# Updates the production Secrets Manager secret with key/value pairs from parameters.json,
# then restarts the webapp on EC2 to pick up the changes.
#
# Usage:
#   ./infrastructure/update-secrets.sh
#
# Prerequisites: aws CLI configured, jq installed, SSH key available for EC2 access.

set -euo pipefail

REGION="us-east-1"
SECRET_ID="production/motiv8/app-secrets"
PARAMS_FILE="infrastructure/parameters.json"

command -v jq >/dev/null 2>&1 || { echo "ERROR: jq is required"; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "ERROR: aws CLI is required"; exit 1; }

echo "Fetching current secret from Secrets Manager..."
CURRENT="$(aws secretsmanager get-secret-value \
  --secret-id "$SECRET_ID" \
  --region "$REGION" \
  --query SecretString \
  --output text)"

# Merge Apple keys from parameters.json into the current secret JSON
get_param() {
  jq -r --arg k "$1" '.[] | select(.ParameterKey==$k) | .ParameterValue' "$PARAMS_FILE"
}

APPLE_CLIENT_ID="$(get_param AppleClientId)"
APPLE_TEAM_ID="$(get_param AppleTeamId)"
APPLE_KEY_ID="$(get_param AppleKeyId)"
APPLE_PRIVATE_KEY="$(get_param ApplePrivateKey)"
APPLE_REDIRECT_URI="https://api.motiv8me.io/auth/apple/callback"

echo "Merging Apple secrets..."
UPDATED="$(echo "$CURRENT" | jq \
  --arg cid "$APPLE_CLIENT_ID" \
  --arg tid "$APPLE_TEAM_ID" \
  --arg kid "$APPLE_KEY_ID" \
  --arg pk  "$APPLE_PRIVATE_KEY" \
  --arg uri "$APPLE_REDIRECT_URI" \
  '. + {
    APPLE_CLIENT_ID: $cid,
    APPLE_TEAM_ID:   $tid,
    APPLE_KEY_ID:    $kid,
    APPLE_PRIVATE_KEY: $pk,
    APPLE_REDIRECT_URI: $uri
  }')"

echo ""
echo "Keys being added/updated:"
diff \
  <(echo "$CURRENT" | jq -S 'keys[]') \
  <(echo "$UPDATED" | jq -S 'keys[]') \
  | grep '^>' | sed 's/^> /  + /' || true

echo ""
echo "Values changing:"
diff \
  <(echo "$CURRENT" | jq -S 'to_entries[] | "\(.key)=\(.value)"') \
  <(echo "$UPDATED"  | jq -S 'to_entries[] | "\(.key)=\(.value)"') \
  | grep '^[<>]' | sed 's/^< /  - /; s/^> /  + /' || true

echo ""
read -r -p "Apply these changes? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "Aborted."
  exit 0
fi

echo "Writing updated secret..."
aws secretsmanager put-secret-value \
  --secret-id "$SECRET_ID" \
  --region "$REGION" \
  --secret-string "$UPDATED"

echo "Secret updated."
echo ""
echo "Next: restart the webapp on EC2 to pick up the new values:"
echo "  ssh -i ~/.ssh/motiv8-keypair.pem ec2-user@api.motiv8me.io 'sudo systemctl restart motiv8-webapp'"
