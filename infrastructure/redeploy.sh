#!/bin/bash
set -e

echo "================================================"
echo "motiv8me Full Deployment Pipeline"
echo "================================================"
echo ""

REGION="us-east-1"
STACK_NAME="motiv8-ec2-instances"
S3_BUCKET="production-motiv8-uploads-901478075158"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_section() {
    echo -e "${YELLOW}$1${NC}"
}

# Step 1: Build and upload code
print_section "Step 1: Building and uploading code to S3..."
echo "----------------------------------------------"

./deploy-code.sh

print_status "Code uploaded to S3"

# Step 2: Get EC2 instance ID
print_section ""
print_section "Step 2: Getting EC2 instance details..."
echo "----------------------------------------------"

INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`WebAppInstanceId`].OutputValue' \
  --output text)

if [ -z "$INSTANCE_ID" ]; then
    echo "ERROR: Could not find EC2 instance ID in stack $STACK_NAME"
    exit 1
fi

print_status "Found instance: $INSTANCE_ID"

# Step 3: Upload redeploy script to S3
print_section ""
print_section "Step 3: Uploading redeploy script..."
echo "----------------------------------------------"

aws s3 cp redeploy-to-ec2.sh \
    "s3://$S3_BUCKET/deployment/redeploy-to-ec2.sh" \
    --region $REGION

print_status "Redeploy script uploaded to S3"

# Step 4: Run redeploy on EC2
print_section ""
print_section "Step 4: Running redeploy on EC2 instance..."
echo "----------------------------------------------"

SSM_COMMAND_ID=$(aws ssm send-command \
  --instance-ids $INSTANCE_ID \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[
    'aws s3 cp s3://$S3_BUCKET/deployment/redeploy-to-ec2.sh /tmp/redeploy-to-ec2.sh --region $REGION',
    'chmod +x /tmp/redeploy-to-ec2.sh',
    'sudo /tmp/redeploy-to-ec2.sh'
  ]" \
  --region $REGION \
  --output text \
  --query 'Command.CommandId')

print_info "Redeploy command sent (ID: $SSM_COMMAND_ID)"
print_info "Waiting for redeploy to complete..."

# Wait for command to complete
aws ssm wait command-executed \
  --command-id $SSM_COMMAND_ID \
  --instance-id $INSTANCE_ID \
  --region $REGION

# Get command output
print_section ""
print_section "Redeploy output:"
echo "================================================"
aws ssm get-command-invocation \
  --command-id $SSM_COMMAND_ID \
  --instance-id $INSTANCE_ID \
  --region $REGION \
  --query 'StandardOutputContent' \
  --output text

echo "================================================"

# Check for errors
COMMAND_STATUS=$(aws ssm get-command-invocation \
  --command-id $SSM_COMMAND_ID \
  --instance-id $INSTANCE_ID \
  --region $REGION \
  --query 'Status' \
  --output text)

if [ "$COMMAND_STATUS" != "Success" ]; then
    echo ""
    echo "⚠ Deployment had issues. Status: $COMMAND_STATUS"
    echo "Error output:"
    aws ssm get-command-invocation \
      --command-id $SSM_COMMAND_ID \
      --instance-id $INSTANCE_ID \
      --region $REGION \
      --query 'StandardErrorContent' \
      --output text
    exit 1
fi

# Final summary
echo ""
echo "================================================"
print_status "Deployment Complete!"
echo "================================================"
echo ""
echo "Your application has been updated at:"
echo "  https://motiv8me.io"
echo ""
echo "To check logs:"
echo "  aws ssm start-session --target $INSTANCE_ID"
echo "  sudo journalctl -u motiv8-backend -f"
echo ""
