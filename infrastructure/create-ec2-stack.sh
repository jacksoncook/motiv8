#!/bin/bash
set -e

echo "================================================"
echo "motiv8me EC2 Instances Stack Creation"
echo "================================================"
echo ""

REGION="us-east-1"
STACK_NAME="motiv8-ec2-instances"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${YELLOW}→${NC} $1"
}

# Check if stack already exists
STACK_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].StackStatus' \
    --output text 2>/dev/null || echo "DOES_NOT_EXIST")

if [ "$STACK_STATUS" != "DOES_NOT_EXIST" ]; then
    echo "Stack $STACK_NAME already exists with status: $STACK_STATUS"
    echo "Please delete it first or use update command."
    exit 1
fi

# Get parameters from existing main stack outputs
print_info "Retrieving parameters from main stack..."

MAIN_STACK_OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name "production-motiv8-main" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs' \
    --output json)

# Extract values
VPC_ID=$(echo "$MAIN_STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="VPCId") | .OutputValue')
PUBLIC_SUBNET_1=$(echo "$MAIN_STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="PublicSubnet1") | .OutputValue')
PUBLIC_SUBNET_2=$(echo "$MAIN_STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="PublicSubnet2") | .OutputValue')
WEBAPP_SG=$(echo "$MAIN_STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="WebAppSecurityGroupId") | .OutputValue')
BATCH_SG=$(echo "$MAIN_STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="BatchSecurityGroupId") | .OutputValue')
INSTANCE_PROFILE=$(echo "$MAIN_STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="InstanceProfileName") | .OutputValue')
APP_SECRETS_ARN=$(echo "$MAIN_STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="AppSecretsArn") | .OutputValue')
UPLOADS_BUCKET=$(echo "$MAIN_STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="UploadsBucketName") | .OutputValue')
BATCH_ROLE_ARN=$(echo "$MAIN_STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="BatchControlRoleArn") | .OutputValue')

# Get Route53 Hosted Zone ID for motiv8me.io
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones --query 'HostedZones[?Name==`motiv8me.io.`].Id' --output text | cut -d'/' -f3)

print_status "Parameters retrieved from main stack"

# Create the stack
print_info "Creating EC2 instances stack..."
echo ""

aws cloudformation create-stack \
    --stack-name "$STACK_NAME" \
    --template-body file://cloudformation/ec2-instances.yaml \
    --parameters \
        ParameterKey=EnvironmentName,ParameterValue=production \
        ParameterKey=WebAppInstanceType,ParameterValue=t3.small \
        ParameterKey=BatchInstanceType,ParameterValue=t3.xlarge \
        ParameterKey=KeyPairName,ParameterValue=motiv8-keypair \
        ParameterKey=VPCId,ParameterValue="$VPC_ID" \
        ParameterKey=PublicSubnet1,ParameterValue="$PUBLIC_SUBNET_1" \
        ParameterKey=PublicSubnet2,ParameterValue="$PUBLIC_SUBNET_2" \
        ParameterKey=HostedZoneId,ParameterValue="$HOSTED_ZONE_ID" \
        ParameterKey=RootDomainName,ParameterValue=motiv8me.io \
        ParameterKey=InstanceProfileName,ParameterValue=production-motiv8-instance-profile \
        ParameterKey=ApiSubdomain,ParameterValue=api \
        ParameterKey=BatchSecurityGroup,ParameterValue="$BATCH_SG" \
        ParameterKey=AppSecretsArn,ParameterValue="$APP_SECRETS_ARN" \
        ParameterKey=UploadsBucket,ParameterValue="$UPLOADS_BUCKET" \
        ParameterKey=BatchControlRoleArn,ParameterValue="$BATCH_ROLE_ARN" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION"

print_status "Stack creation initiated"
echo ""
print_info "Waiting for stack to be created (this may take 20-30 minutes)..."
print_info "WebApp timeout increased to 30 minutes to allow for code download and setup"
echo ""

# Wait for completion
aws cloudformation wait stack-create-complete \
    --stack-name "$STACK_NAME" \
    --region "$REGION"

echo ""
echo "================================================"
print_status "EC2 Instances Stack Created Successfully!"
echo "================================================"
echo ""

# Show outputs
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[].{Key:OutputKey,Value:OutputValue}' \
    --output table

echo ""
print_info "Next steps:"
echo "  1. Check webapp is running: curl http://\$(webapp-ip):8000"
echo "  2. Test batch job: ./run-batch-job.sh"
echo ""
