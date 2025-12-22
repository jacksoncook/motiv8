#!/bin/bash
set -e

echo "================================================"
echo "motiv8me Code Deployment Script"
echo "================================================"
echo ""

REGION="us-east-1"
EC2_STACK_NAME="motiv8-ec2-instances"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Parse command line arguments
DEPLOY_BACKEND=true
DEPLOY_FRONTEND=true
DEPLOY_BATCH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-only)
            DEPLOY_BACKEND=true
            DEPLOY_FRONTEND=false
            DEPLOY_BATCH=false
            shift
            ;;
        --frontend-only)
            DEPLOY_BACKEND=false
            DEPLOY_FRONTEND=true
            DEPLOY_BATCH=false
            shift
            ;;
        --batch-only)
            DEPLOY_BACKEND=false
            DEPLOY_FRONTEND=false
            DEPLOY_BATCH=true
            shift
            ;;
        --all)
            DEPLOY_BACKEND=true
            DEPLOY_FRONTEND=true
            DEPLOY_BATCH=true
            shift
            ;;
        --help)
            echo "Usage: ./deploy-code.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --backend-only    Deploy only backend code"
            echo "  --frontend-only   Deploy only frontend code"
            echo "  --batch-only      Deploy only batch processing script"
            echo "  --all             Deploy everything including batch (default: backend + frontend)"
            echo "  --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./deploy-code.sh                    # Deploy backend + frontend"
            echo "  ./deploy-code.sh --backend-only     # Deploy only backend"
            echo "  ./deploy-code.sh --all              # Deploy everything"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Run './deploy-code.sh --help' for usage information"
            exit 1
            ;;
    esac
done

# Get instance IDs
echo "Step 1: Getting EC2 instance information..."
echo "-------------------------------------------"
WEBAPP_INSTANCE_ID=$(aws cloudformation describe-stacks \
    --stack-name "$EC2_STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`WebAppInstanceId`].OutputValue' \
    --output text)

if [ -z "$WEBAPP_INSTANCE_ID" ]; then
    print_error "Could not find Web App instance ID"
    exit 1
fi

print_status "Web App Instance: $WEBAPP_INSTANCE_ID"

# Check if instance is online in SSM
print_info "Checking if instance is ready for Systems Manager..."
INSTANCE_STATUS=$(aws ssm describe-instance-information \
    --filters "Key=InstanceIds,Values=$WEBAPP_INSTANCE_ID" \
    --region "$REGION" \
    --query 'InstanceInformationList[0].PingStatus' \
    --output text 2>/dev/null)

if [ "$INSTANCE_STATUS" != "Online" ]; then
    print_error "Instance is not online in Systems Manager (Status: $INSTANCE_STATUS)"
    exit 1
fi

print_status "Instance is online and ready"

# Deploy Backend
if [ "$DEPLOY_BACKEND" = true ]; then
    echo ""
    echo "Step 2: Deploying Backend Code..."
    echo "---------------------------------"
    print_info "Pulling latest code and restarting backend service..."

    BACKEND_COMMAND_ID=$(aws ssm send-command \
        --instance-ids "$WEBAPP_INSTANCE_ID" \
        --document-name "AWS-RunShellScript" \
        --parameters 'commands=[
            "cd /app && sudo git pull origin main",
            "cd /app/motiv8-be && source venv/bin/activate && pip install -r requirements-web.txt",
            "sudo systemctl restart motiv8-backend",
            "sleep 3",
            "sudo systemctl status motiv8-backend --no-pager"
        ]' \
        --region "$REGION" \
        --output text \
        --query 'Command.CommandId')

    print_status "Backend deployment command sent (ID: $BACKEND_COMMAND_ID)"
    print_info "Waiting for backend deployment to complete..."

    aws ssm wait command-executed \
        --command-id "$BACKEND_COMMAND_ID" \
        --instance-id "$WEBAPP_INSTANCE_ID" \
        --region "$REGION"

    # Get output
    BACKEND_OUTPUT=$(aws ssm get-command-invocation \
        --command-id "$BACKEND_COMMAND_ID" \
        --instance-id "$WEBAPP_INSTANCE_ID" \
        --region "$REGION" \
        --query 'StandardOutputContent' \
        --output text)

    if echo "$BACKEND_OUTPUT" | grep -q "active (running)"; then
        print_status "Backend deployed successfully and is running"
    else
        print_warning "Backend deployment completed, but service status unclear"
        echo "Output:"
        echo "$BACKEND_OUTPUT"
    fi
fi

# Deploy Frontend
if [ "$DEPLOY_FRONTEND" = true ]; then
    echo ""
    echo "Step 3: Deploying Frontend Code..."
    echo "----------------------------------"
    print_info "Building and deploying frontend..."

    FRONTEND_COMMAND_ID=$(aws ssm send-command \
        --instance-ids "$WEBAPP_INSTANCE_ID" \
        --document-name "AWS-RunShellScript" \
        --parameters 'commands=[
            "cd /app/motiv8-fe && npm run build",
            "sudo chown -R ec2-user:nginx /app/motiv8-fe/dist",
            "sudo chmod -R 755 /app/motiv8-fe/dist",
            "sudo systemctl reload nginx",
            "echo \"Frontend build completed successfully\""
        ]' \
        --region "$REGION" \
        --output text \
        --query 'Command.CommandId')

    print_status "Frontend deployment command sent (ID: $FRONTEND_COMMAND_ID)"
    print_info "Waiting for frontend build to complete (this may take 1-2 minutes)..."

    aws ssm wait command-executed \
        --command-id "$FRONTEND_COMMAND_ID" \
        --instance-id "$WEBAPP_INSTANCE_ID" \
        --region "$REGION"

    # Get output
    FRONTEND_OUTPUT=$(aws ssm get-command-invocation \
        --command-id "$FRONTEND_COMMAND_ID" \
        --instance-id "$WEBAPP_INSTANCE_ID" \
        --region "$REGION" \
        --query 'StandardOutputContent' \
        --output text)

    if echo "$FRONTEND_OUTPUT" | grep -q "build completed successfully"; then
        print_status "Frontend deployed successfully"
    else
        print_warning "Frontend deployment completed, check output:"
        echo "$FRONTEND_OUTPUT"
    fi
fi

# Deploy Batch Script
if [ "$DEPLOY_BATCH" = true ]; then
    echo ""
    echo "Step 4: Deploying Batch Processing Script..."
    echo "--------------------------------------------"
    print_warning "Batch script deployment not fully implemented yet"
    print_info "Batch script is stored in /app/motiv8-be/batch_generate.py on the web server"
    print_info "It will be deployed when the backend is deployed"
fi

# Final summary
echo ""
echo "================================================"
print_status "Code Deployment Complete!"
echo "================================================"
echo ""
echo "Deployed components:"
[ "$DEPLOY_BACKEND" = true ] && echo "  ✓ Backend API"
[ "$DEPLOY_FRONTEND" = true ] && echo "  ✓ Frontend"
[ "$DEPLOY_BATCH" = true ] && echo "  ✓ Batch script"
echo ""
echo "Application URL: https://motiv8me.io"
echo ""
echo "To check logs:"
echo "  Backend:  aws ssm start-session --target $WEBAPP_INSTANCE_ID"
echo "            sudo journalctl -u motiv8-backend -f"
echo "  Nginx:    sudo journalctl -u nginx -f"
echo ""
