#!/bin/bash
set -e

echo "================================================"
echo "motiv8me Batch Job Manual Trigger"
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
DRY_RUN=false
SHOW_OUTPUT=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --quiet)
            SHOW_OUTPUT=false
            shift
            ;;
        --help)
            echo "Usage: ./run-batch-job.sh [OPTIONS]"
            echo ""
            echo "Manually triggers the batch image generation and email job."
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would happen without actually running"
            echo "  --quiet      Don't show detailed output"
            echo "  --help       Show this help message"
            echo ""
            echo "What this script does:"
            echo "  1. Finds users with workout days set for today"
            echo "  2. Extracts face embeddings (if not already done)"
            echo "  3. Generates motivational images"
            echo "  4. Sends email to each user"
            echo ""
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Run './run-batch-job.sh --help' for usage information"
            exit 1
            ;;
    esac
done

# Get batch instance ID
echo "Step 1: Getting batch instance information..."
echo "----------------------------------------------"
BATCH_INSTANCE_ID=$(aws cloudformation describe-stacks \
    --stack-name "$EC2_STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`BatchInstanceId`].OutputValue' \
    --output text)

if [ -z "$BATCH_INSTANCE_ID" ]; then
    print_error "Could not find Batch instance ID"
    exit 1
fi

print_status "Batch Instance: $BATCH_INSTANCE_ID"

# Check if instance is running
print_info "Checking instance state..."
INSTANCE_STATE=$(aws ec2 describe-instances \
    --instance-ids "$BATCH_INSTANCE_ID" \
    --region "$REGION" \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text)

if [ "$INSTANCE_STATE" = "stopped" ]; then
    print_warning "Batch instance is stopped. Starting it now..."
    aws ec2 start-instances --instance-ids "$BATCH_INSTANCE_ID" --region "$REGION" > /dev/null
    print_info "Waiting for instance to start (this may take 1-2 minutes)..."
    aws ec2 wait instance-running --instance-ids "$BATCH_INSTANCE_ID" --region "$REGION"
    print_status "Instance started successfully"

    # Wait a bit more for SSM agent to be ready
    print_info "Waiting for Systems Manager agent to be ready..."
    sleep 30
elif [ "$INSTANCE_STATE" != "running" ]; then
    print_error "Instance is in unexpected state: $INSTANCE_STATE"
    exit 1
else
    print_status "Instance is already running"
fi

# Check if instance is online in SSM
print_info "Checking Systems Manager connectivity..."
MAX_WAIT=60
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    INSTANCE_STATUS=$(aws ssm describe-instance-information \
        --filters "Key=InstanceIds,Values=$BATCH_INSTANCE_ID" \
        --region "$REGION" \
        --query 'InstanceInformationList[0].PingStatus' \
        --output text 2>/dev/null)

    if [ "$INSTANCE_STATUS" = "Online" ]; then
        print_status "Instance is online and ready"
        break
    fi

    sleep 5
    WAIT_COUNT=$((WAIT_COUNT + 5))
done

if [ "$INSTANCE_STATUS" != "Online" ]; then
    print_error "Instance did not become ready in time (Status: $INSTANCE_STATUS)"
    exit 1
fi

if [ "$DRY_RUN" = true ]; then
    echo ""
    print_warning "DRY RUN MODE - Would execute batch job but not actually running"
    echo ""
    echo "The batch job would:"
    echo "  1. Find all users with today as a workout day"
    echo "  2. Extract face embeddings for users without embeddings"
    echo "  3. Generate motivational images for each user"
    echo "  4. Send motivational emails with generated images"
    echo ""
    exit 0
fi

# Run the batch job
echo ""
echo "Step 2: Running Batch Job..."
echo "----------------------------"
print_warning "This will process all users with today set as a workout day"
print_info "The job includes: face extraction, image generation, and email sending"
echo ""
read -p "Do you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    print_warning "Batch job cancelled"
    exit 0
fi

print_info "Starting batch job..."
echo ""

# Create the batch command
BATCH_COMMAND_ID=$(aws ssm send-command \
    --instance-ids "$BATCH_INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=[
        "cd /app/batch",
        "echo \"=== Batch Job Started at $(date) ===\"",
        "echo \"\"",
        "# Run the batch job",
        "/app/batch/run-batch.sh || echo \"Batch job failed with exit code $?\"",
        "echo \"\"",
        "echo \"=== Batch Job Completed at $(date) ===\"",
        "echo \"\"",
        "echo \"Instance will shut down in 5 minutes...\"",
        "sleep 300",
        "sudo shutdown -h now"
    ]' \
    --timeout-seconds 3600 \
    --region "$REGION" \
    --output text \
    --query 'Command.CommandId')

print_status "Batch job command sent (ID: $BATCH_COMMAND_ID)"
print_info "This may take 10-30 minutes depending on number of users..."

if [ "$SHOW_OUTPUT" = true ]; then
    echo ""
    print_info "Waiting for batch job to complete (streaming output)..."
    echo "================================================"
    echo ""

    # Wait for command to complete
    aws ssm wait command-executed \
        --command-id "$BATCH_COMMAND_ID" \
        --instance-id "$BATCH_INSTANCE_ID" \
        --region "$REGION"

    # Get the full output
    echo ""
    echo "Batch Job Output:"
    echo "================================================"
    aws ssm get-command-invocation \
        --command-id "$BATCH_COMMAND_ID" \
        --instance-id "$BATCH_INSTANCE_ID" \
        --region "$REGION" \
        --query 'StandardOutputContent' \
        --output text

    # Check for errors
    ERROR_OUTPUT=$(aws ssm get-command-invocation \
        --command-id "$BATCH_COMMAND_ID" \
        --instance-id "$BATCH_INSTANCE_ID" \
        --region "$REGION" \
        --query 'StandardErrorContent' \
        --output text)

    if [ -n "$ERROR_OUTPUT" ] && [ "$ERROR_OUTPUT" != "None" ]; then
        echo ""
        echo "Errors/Warnings:"
        echo "================================================"
        echo "$ERROR_OUTPUT"
    fi

    echo "================================================"
else
    print_info "Job running in background. Command ID: $BATCH_COMMAND_ID"
    print_info "Check status with:"
    echo "  aws ssm get-command-invocation --command-id $BATCH_COMMAND_ID --instance-id $BATCH_INSTANCE_ID"
fi

# Get command status
COMMAND_STATUS=$(aws ssm get-command-invocation \
    --command-id "$BATCH_COMMAND_ID" \
    --instance-id "$BATCH_INSTANCE_ID" \
    --region "$REGION" \
    --query 'Status' \
    --output text)

echo ""
echo "================================================"
if [ "$COMMAND_STATUS" = "Success" ]; then
    print_status "Batch job completed successfully!"
    print_info "Instance will automatically shut down in 5 minutes"
else
    print_warning "Batch job completed with status: $COMMAND_STATUS"
    print_info "Instance will automatically shut down in 5 minutes"
fi
echo "================================================"
echo ""
echo "To view full logs later:"
echo "  aws ssm get-command-invocation \\"
echo "    --command-id $BATCH_COMMAND_ID \\"
echo "    --instance-id $BATCH_INSTANCE_ID"
echo ""
echo "Note: The batch instance will automatically stop after completion."
echo ""
