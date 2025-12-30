#!/usr/bin/env bash
set -euo pipefail

# Deploy FE+BE artifacts and trigger a CFN stack update that:
# - republishes FE to FrontendBucket + invalidates CloudFront (via FrontendPublishVersion)
# - replaces WebAppInstance so it pulls latest BE tarball (via ApiDeployVersion)

REGION="us-east-1"
MAIN_STACK="production-motiv8-main"
EC2_STACK="motiv8-ec2-instances"          # change if yours differs
TEMPLATE_PATH="infrastructure/cloudformation/ec2-instances.yaml"

FE_DIR="motiv8-fe"
BE_DIR="motiv8-be"
KEYPAIR="motiv8-keypair"

# Optional overrides
ROOT_DOMAIN="motiv8me.io"
API_SUBDOMAIN="api"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --region) REGION="$2"; shift 2;;
    --main-stack) MAIN_STACK="$2"; shift 2;;
    --stack) EC2_STACK="$2"; shift 2;;
    --template) TEMPLATE_PATH="$2"; shift 2;;
    --keypair) KEYPAIR="$2"; shift 2;;
    --root-domain) ROOT_DOMAIN="$2"; shift 2;;
    --api-subdomain) API_SUBDOMAIN="$2"; shift 2;;
    -h|--help)
      echo "Usage:"
      echo "  ./deploy-all.sh [--stack name] [--main-stack name] [--region region]"
      echo ""
      echo "Defaults:"
      echo "  FE_DIR=motiv8-fe"
      echo "  BE_DIR=motiv8-be"
      echo "  REGION=us-east-1"
      echo "  MAIN_STACK=production-motiv8-main"
      echo "  EC2_STACK=motiv8-ec2-instances"
      exit 0
      ;;
    *)
      echo "Unknown arg: $1"
      exit 1
      ;;
  esac
done

command -v jq >/dev/null 2>&1 || { echo "ERROR: jq is required"; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "ERROR: aws cli is required"; exit 1; }

# --- Compute deploy versions ---
# Prefer git SHA if available, else timestamp
if git -C "$BE_DIR" rev-parse --short HEAD >/dev/null 2>&1; then
  VER="$(git -C "$BE_DIR" rev-parse --short HEAD)"
else
  VER="$(date +%Y%m%d%H%M%S)"
fi
FRONTEND_VER="fe-${VER}"
API_VER="api-${VER}"
BATCH_VER="batch-${VER}"

echo "Deploy version:"
echo "  FrontendPublishVersion=$FRONTEND_VER"
echo "  ApiDeployVersion=$API_VER"
echo "  BatchDeployVersion=$BATCH_VER"

# --- Pull required infra params from MAIN_STACK outputs ---
echo "Reading outputs from main stack: $MAIN_STACK"
MAIN_STACK_OUTPUTS="$(aws cloudformation describe-stacks \
  --stack-name "$MAIN_STACK" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs' \
  --output json)"

get_out() {
  local key="$1"
  echo "$MAIN_STACK_OUTPUTS" | jq -r --arg K "$key" '.[] | select(.OutputKey==$K) | .OutputValue' | head -n 1
}

VPC_ID="$(get_out VPCId)"
PUBLIC_SUBNET_1="$(get_out PublicSubnet1)"
PUBLIC_SUBNET_2="$(get_out PublicSubnet2)"
BATCH_SG="$(get_out BatchSecurityGroupId)"
INSTANCE_PROFILE_ARN="$(get_out InstanceProfileArn)"
INSTANCE_PROFILE_NAME="${INSTANCE_PROFILE_ARN##*/}"
APP_SECRETS_ARN="$(get_out AppSecretsArn)"
UPLOADS_BUCKET="$(get_out UploadsBucketName)"
BATCH_ROLE_ARN="$(get_out BatchControlRoleArn)"

# Get RDS security group from the database (not exported from main stack)
echo "Looking up RDS security group..."
RDS_SG="$(aws rds describe-db-instances \
  --db-instance-identifier production-motiv8-db \
  --region "$REGION" \
  --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' \
  --output text 2>/dev/null || echo "")"

# Sanity checks
for v in VPC_ID PUBLIC_SUBNET_1 PUBLIC_SUBNET_2 BATCH_SG INSTANCE_PROFILE_NAME APP_SECRETS_ARN UPLOADS_BUCKET BATCH_ROLE_ARN RDS_SG; do
  if [[ -z "${!v}" || "${!v}" == "null" ]]; then
    echo "ERROR: Missing main-stack output for $v"
    echo "MAIN_STACK_OUTPUTS keys were:"
    echo "$MAIN_STACK_OUTPUTS" | jq -r '.[].OutputKey' | sort
    exit 1
  fi
done

# Hosted zone for root domain
HOSTED_ZONE_ID="$(aws route53 list-hosted-zones \
  --region "$REGION" \
  --query "HostedZones[?Name=='${ROOT_DOMAIN}.'].Id" \
  --output text | head -n 1 | cut -d'/' -f3)"

if [[ -z "$HOSTED_ZONE_ID" || "$HOSTED_ZONE_ID" == "None" ]]; then
  echo "ERROR: Could not find Route53 hosted zone for ${ROOT_DOMAIN}."
  exit 1
fi

echo "Derived params:"
echo "  VPCId=$VPC_ID"
echo "  PublicSubnet1=$PUBLIC_SUBNET_1"
echo "  PublicSubnet2=$PUBLIC_SUBNET_2"
echo "  BatchSecurityGroup=$BATCH_SG"
echo "  RdsSecurityGroup=$RDS_SG"
echo "  InstanceProfileName=$INSTANCE_PROFILE_NAME"
echo "  AppSecretsArn=$APP_SECRETS_ARN"
echo "  UploadsBucket=$UPLOADS_BUCKET"
echo "  BatchControlRoleArn=$BATCH_ROLE_ARN"
echo "  HostedZoneId=$HOSTED_ZONE_ID"

# --- Build + upload artifacts ---
echo "Building + uploading artifacts to s3://${UPLOADS_BUCKET}/deployment/..."
./infrastructure/deploy-artifacts.sh \
  --bucket "$UPLOADS_BUCKET" \
  --region "$REGION" \
  --fe-dir "$FE_DIR" \
  --be-dir "$BE_DIR"

# --- Update stack (republish FE + replace API instance) ---
echo "Updating stack: $EC2_STACK"
aws cloudformation deploy \
  --region "$REGION" \
  --stack-name "$EC2_STACK" \
  --template-file "$TEMPLATE_PATH" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    EnvironmentName=production \
    WebAppInstanceType=t3.small \
    BatchInstanceType=t3.xlarge \
    KeyPairName="$KEYPAIR" \
    VPCId="$VPC_ID" \
    PublicSubnet1="$PUBLIC_SUBNET_1" \
    PublicSubnet2="$PUBLIC_SUBNET_2" \
    HostedZoneId="$HOSTED_ZONE_ID" \
    RootDomainName="$ROOT_DOMAIN" \
    ApiSubdomain="$API_SUBDOMAIN" \
    InstanceProfileName="$INSTANCE_PROFILE_NAME" \
    BatchSecurityGroup="$BATCH_SG" \
    RdsSecurityGroup="$RDS_SG" \
    AppSecretsArn="$APP_SECRETS_ARN" \
    UploadsBucket="$UPLOADS_BUCKET" \
    BatchControlRoleArn="$BATCH_ROLE_ARN" \
    FrontendPublishVersion="$FRONTEND_VER" \
    ApiDeployVersion="$API_VER" \
    BatchDeployVersion="$BATCH_VER"

echo "Done."
echo "Frontend: https://${ROOT_DOMAIN}"
echo "API:      https://${API_SUBDOMAIN}.${ROOT_DOMAIN}/health"

