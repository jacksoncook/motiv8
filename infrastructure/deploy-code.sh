#!/bin/bash
set -e

echo "================================================"
echo "motiv8me Code Deployment to S3"
echo "================================================"
echo ""

REGION="us-east-1"
S3_BUCKET="production-motiv8-uploads-901478075158"
BACKEND_KEY="deployment/motiv8-be.tar.gz"
FRONTEND_KEY="deployment/motiv8-fe-dist.tar.gz"
BACKEND_SOURCE_DIR="/Users/jcook/motiv8/motiv8-be"
FRONTEND_SOURCE_DIR="/Users/jcook/motiv8/motiv8-fe"

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

# Step 1: Build and package frontend
print_section "Step 1: Building and packaging frontend..."
echo "----------------------------------------------"
cd "$FRONTEND_SOURCE_DIR"

print_info "Installing dependencies..."
npm install

print_info "Building frontend..."
npm run build

print_info "Creating tarball..."
cd dist
tar -czf /tmp/motiv8-fe-dist.tar.gz .
cd ..

FRONTEND_SIZE=$(du -h /tmp/motiv8-fe-dist.tar.gz | cut -f1)
print_status "Frontend package created: /tmp/motiv8-fe-dist.tar.gz ($FRONTEND_SIZE)"

# Step 2: Package backend code
print_section ""
print_section "Step 2: Packaging backend code..."
echo "----------------------------------------------"
cd "$BACKEND_SOURCE_DIR/.."

print_info "Creating tarball..."
tar -czf /tmp/motiv8-be.tar.gz \
    --exclude='motiv8-be/.venv' \
    --exclude='motiv8-be/__pycache__' \
    --exclude='motiv8-be/*.pyc' \
    --exclude='motiv8-be/.env' \
    --exclude='motiv8-be/.git' \
    --exclude='motiv8-be/node_modules' \
    --exclude='motiv8-be/*.db' \
    --exclude='motiv8-be/uploads/*' \
    motiv8-be/

BACKEND_SIZE=$(du -h /tmp/motiv8-be.tar.gz | cut -f1)
print_status "Backend package created: /tmp/motiv8-be.tar.gz ($BACKEND_SIZE)"

# Step 3: Upload to S3
print_section ""
print_section "Step 3: Uploading to S3..."
echo "----------------------------------------------"

print_info "Uploading frontend to s3://$S3_BUCKET/$FRONTEND_KEY"
aws s3 cp /tmp/motiv8-fe-dist.tar.gz \
    "s3://$S3_BUCKET/$FRONTEND_KEY" \
    --region "$REGION"
print_status "Frontend uploaded successfully"

print_info "Uploading backend to s3://$S3_BUCKET/$BACKEND_KEY"
aws s3 cp /tmp/motiv8-be.tar.gz \
    "s3://$S3_BUCKET/$BACKEND_KEY" \
    --region "$REGION"
print_status "Backend uploaded successfully"

# Step 4: Verify uploads
print_section ""
print_section "Step 4: Verifying uploads..."
echo "----------------------------------------------"
FRONTEND_S3_SIZE=$(aws s3 ls "s3://$S3_BUCKET/$FRONTEND_KEY" --region "$REGION" | awk '{print $3}')
print_status "Frontend verified in S3 (Size: $FRONTEND_S3_SIZE bytes)"

BACKEND_S3_SIZE=$(aws s3 ls "s3://$S3_BUCKET/$BACKEND_KEY" --region "$REGION" | awk '{print $3}')
print_status "Backend verified in S3 (Size: $BACKEND_S3_SIZE bytes)"

# Cleanup
rm /tmp/motiv8-fe-dist.tar.gz
rm /tmp/motiv8-be.tar.gz
print_info "Cleaned up temporary files"

echo ""
echo "================================================"
print_status "Deployment packages ready!"
echo "================================================"
echo ""
echo "Frontend S3 Location: s3://$S3_BUCKET/$FRONTEND_KEY"
echo "Backend S3 Location:  s3://$S3_BUCKET/$BACKEND_KEY"
echo ""
echo "Next step: Run redeploy script on EC2 instances"
echo ""
