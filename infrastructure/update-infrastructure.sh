#!/bin/bash
set -e

echo "================================================"
echo "motiv8me Infrastructure Update Script"
echo "================================================"
echo ""

REGION="us-east-1"
MAIN_STACK_NAME="production-motiv8-main"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if parameters file exists
if [ ! -f "parameters.json" ]; then
    print_error "parameters.json not found!"
    echo "Please create parameters.json in the infrastructure directory."
    exit 1
fi

print_status "Found parameters.json"

# Show current stack status
echo ""
echo "Current Stack Status:"
echo "--------------------"
aws cloudformation describe-stacks \
    --stack-name "$MAIN_STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].{Status:StackStatus,Created:CreationTime,Updated:LastUpdatedTime}' \
    --output table

# Validate template
echo ""
echo "Step 1: Validating CloudFormation template..."
echo "----------------------------------------------"
VALIDATION=$(aws cloudformation validate-template \
    --template-body file://cloudformation/main-stack.yaml \
    --region "$REGION" 2>&1)

if [ $? -eq 0 ]; then
    print_status "Template validation successful"
else
    print_error "Template validation failed:"
    echo "$VALIDATION"
    exit 1
fi

# Show what will be updated
echo ""
echo "Step 2: Creating change set to preview changes..."
echo "--------------------------------------------------"
CHANGE_SET_NAME="update-$(date +%Y%m%d-%H%M%S)"

aws cloudformation create-change-set \
    --stack-name "$MAIN_STACK_NAME" \
    --change-set-name "$CHANGE_SET_NAME" \
    --template-body file://cloudformation/main-stack.yaml \
    --parameters file://parameters.json \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION"

print_status "Change set created: $CHANGE_SET_NAME"
echo "Waiting for change set to be ready..."

aws cloudformation wait change-set-create-complete \
    --stack-name "$MAIN_STACK_NAME" \
    --change-set-name "$CHANGE_SET_NAME" \
    --region "$REGION" 2>&1 || true

# Display changes
echo ""
echo "Proposed Changes:"
echo "-----------------"
aws cloudformation describe-change-set \
    --stack-name "$MAIN_STACK_NAME" \
    --change-set-name "$CHANGE_SET_NAME" \
    --region "$REGION" \
    --query 'Changes[].{Action:ResourceChange.Action,Resource:ResourceChange.LogicalResourceId,Type:ResourceChange.ResourceType,Replacement:ResourceChange.Replacement}' \
    --output table

# Ask for confirmation
echo ""
print_warning "DATABASE PROTECTION: Database has DeletionPolicy: Snapshot"
print_warning "If database needs replacement, a snapshot will be created automatically"
echo ""
read -p "Do you want to execute these changes? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    print_warning "Update cancelled. Cleaning up change set..."
    aws cloudformation delete-change-set \
        --stack-name "$MAIN_STACK_NAME" \
        --change-set-name "$CHANGE_SET_NAME" \
        --region "$REGION"
    exit 0
fi

# Execute the change set
echo ""
echo "Step 3: Executing infrastructure update..."
echo "------------------------------------------"
aws cloudformation execute-change-set \
    --stack-name "$MAIN_STACK_NAME" \
    --change-set-name "$CHANGE_SET_NAME" \
    --region "$REGION"

print_status "Update initiated"
echo "Waiting for stack update to complete (this may take 10-30 minutes)..."
echo ""

# Wait for completion with status updates
aws cloudformation wait stack-update-complete \
    --stack-name "$MAIN_STACK_NAME" \
    --region "$REGION"

if [ $? -eq 0 ]; then
    echo ""
    echo "================================================"
    print_status "Infrastructure update completed successfully!"
    echo "================================================"
    echo ""

    # Show updated stack info
    echo "Updated Stack Information:"
    echo "-------------------------"
    aws cloudformation describe-stacks \
        --stack-name "$MAIN_STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[].{Key:OutputKey,Value:OutputValue}' \
        --output table
else
    echo ""
    print_error "Infrastructure update failed!"
    echo ""
    echo "Check CloudFormation console for details:"
    echo "https://console.aws.amazon.com/cloudformation/home?region=$REGION#/stacks"
    exit 1
fi

echo ""
print_warning "Note: If you updated EC2 instance types, you may need to:"
echo "  1. Update the EC2 instances stack separately"
echo "  2. Redeploy code to the new instances"
echo ""
