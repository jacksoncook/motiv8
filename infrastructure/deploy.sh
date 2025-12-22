#!/bin/bash

# Motiv8 AWS Deployment Script
# This script helps deploy the CloudFormation stacks

set -e

REGION="us-east-1"
ENVIRONMENT="production"
MAIN_STACK_NAME="${ENVIRONMENT}-motiv8-main"
EC2_STACK_NAME="${ENVIRONMENT}-motiv8-ec2"

echo "========================================"
echo "Motiv8 AWS Deployment Script"
echo "========================================"
echo ""

# Check if parameters.json exists
if [ ! -f "parameters.json" ]; then
    echo "ERROR: parameters.json not found!"
    echo "Please create parameters.json with your configuration."
    echo "See DEPLOYMENT.md for details."
    exit 1
fi

echo "Step 1: Deploying main infrastructure stack..."
echo "----------------------------------------------"

# Deploy main stack
aws cloudformation create-stack \
    --stack-name "$MAIN_STACK_NAME" \
    --template-body file://cloudformation/main-stack.yaml \
    --parameters file://parameters.json \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION"

echo "Waiting for main stack to complete (this may take 10-15 minutes)..."
aws cloudformation wait stack-create-complete \
    --stack-name "$MAIN_STACK_NAME" \
    --region "$REGION"

echo ""
echo "Main stack deployed successfully!"
echo ""

# Get outputs from main stack
echo "Step 2: Retrieving stack outputs..."
echo "--------------------------------------"

OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name "$MAIN_STACK_NAME" \
    --query 'Stacks[0].Outputs' \
    --region "$REGION" \
    --output json)

# Extract values
VPC_ID=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="VPCId") | .OutputValue')
PUBLIC_SUBNET_1=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="PublicSubnet1") | .OutputValue')
WEBAPP_SG=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="WebAppSecurityGroupId") | .OutputValue')
BATCH_SG=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="BatchSecurityGroupId") | .OutputValue')
INSTANCE_PROFILE=$(echo "$OUTPUTS" | jq -r '.[] | select(.ExportName=="'${ENVIRONMENT}'-Instance-Profile-ARN") | .OutputValue')
APP_SECRETS_ARN=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="AppSecretsArn") | .OutputValue')
UPLOADS_BUCKET=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="UploadsBucketName") | .OutputValue')
BATCH_ROLE_ARN=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="BatchControlRoleArn") | .OutputValue')

# Get KeyPairName from parameters.json
KEY_PAIR_NAME=$(jq -r '.[] | select(.ParameterKey=="KeyPairName") | .ParameterValue' parameters.json)

echo "Creating ec2-parameters.json..."

# Create EC2 parameters file
cat > ec2-parameters.json <<EOF
[
  {
    "ParameterKey": "EnvironmentName",
    "ParameterValue": "$ENVIRONMENT"
  },
  {
    "ParameterKey": "WebAppInstanceType",
    "ParameterValue": "t3.small"
  },
  {
    "ParameterKey": "BatchInstanceType",
    "ParameterValue": "t3.xlarge"
  },
  {
    "ParameterKey": "KeyPairName",
    "ParameterValue": "$KEY_PAIR_NAME"
  },
  {
    "ParameterKey": "VPCId",
    "ParameterValue": "$VPC_ID"
  },
  {
    "ParameterKey": "PublicSubnet1",
    "ParameterValue": "$PUBLIC_SUBNET_1"
  },
  {
    "ParameterKey": "WebAppSecurityGroup",
    "ParameterValue": "$WEBAPP_SG"
  },
  {
    "ParameterKey": "BatchSecurityGroup",
    "ParameterValue": "$BATCH_SG"
  },
  {
    "ParameterKey": "InstanceProfile",
    "ParameterValue": "$INSTANCE_PROFILE"
  },
  {
    "ParameterKey": "AppSecretsArn",
    "ParameterValue": "$APP_SECRETS_ARN"
  },
  {
    "ParameterKey": "UploadsBucket",
    "ParameterValue": "$UPLOADS_BUCKET"
  },
  {
    "ParameterKey": "BatchControlRoleArn",
    "ParameterValue": "$BATCH_ROLE_ARN"
  }
]
EOF

echo "ec2-parameters.json created successfully!"
echo ""

echo "Step 3: Deploying EC2 instances stack..."
echo "----------------------------------------"

# Deploy EC2 stack
aws cloudformation create-stack \
    --stack-name "$EC2_STACK_NAME" \
    --template-body file://cloudformation/ec2-instances.yaml \
    --parameters file://ec2-parameters.json \
    --region "$REGION"

echo "Waiting for EC2 stack to complete (this may take 10-15 minutes)..."
aws cloudformation wait stack-create-complete \
    --stack-name "$EC2_STACK_NAME" \
    --region "$REGION"

echo ""
echo "========================================"
echo "Deployment Complete!"
echo "========================================"
echo ""

# Get EC2 instance details
EC2_OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name "$EC2_STACK_NAME" \
    --query 'Stacks[0].Outputs' \
    --region "$REGION" \
    --output json)

WEBAPP_DNS=$(echo "$EC2_OUTPUTS" | jq -r '.[] | select(.OutputKey=="WebAppPublicDNS") | .OutputValue')
WEBAPP_IP=$(echo "$EC2_OUTPUTS" | jq -r '.[] | select(.OutputKey=="WebAppPublicIP") | .OutputValue')

echo "Web App Instance:"
echo "  Public DNS: $WEBAPP_DNS"
echo "  Public IP: $WEBAPP_IP"
echo "  Access: http://$WEBAPP_IP:8000"
echo ""
echo "Database Endpoint: $(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="DatabaseEndpoint") | .OutputValue')"
echo "Uploads Bucket: $UPLOADS_BUCKET"
echo "Frontend Bucket: $(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="FrontendBucketName") | .OutputValue')"
echo ""
echo "Next Steps:"
echo "1. SSH to web app instance and deploy application code"
echo "2. Run database migrations"
echo "3. Build and upload frontend to S3"
echo "4. Test batch instance manually"
echo ""
echo "See DEPLOYMENT.md for detailed instructions."
