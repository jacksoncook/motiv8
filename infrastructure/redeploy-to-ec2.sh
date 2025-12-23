#!/bin/bash
set -e

echo "================================================"
echo "motiv8me EC2 Redeploy Script"
echo "================================================"
echo "This script updates the frontend and backend on a running EC2 instance"
echo ""

# Configuration
REGION="us-east-1"
S3_BUCKET="production-motiv8-uploads-901478075158"
BACKEND_KEY="deployment/motiv8-be.tar.gz"
FRONTEND_KEY="deployment/motiv8-fe-dist.tar.gz"
APP_DIR="/app"

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

# Step 1: Update frontend
print_section "Step 1: Updating frontend..."
echo "----------------------------------------------"

print_info "Downloading frontend from S3..."
FRONTEND_URL=$(aws s3 presign s3://$S3_BUCKET/$FRONTEND_KEY --expires-in 3600 --region $REGION)
curl -L -o /tmp/motiv8-fe-dist.tar.gz "$FRONTEND_URL"

print_info "Backing up current frontend..."
if [ -d /var/www/motiv8/dist ]; then
    sudo mv /var/www/motiv8/dist /var/www/motiv8/dist.backup.$(date +%Y%m%d_%H%M%S)
fi

print_info "Extracting new frontend..."
sudo mkdir -p /var/www/motiv8/dist
sudo tar -xzf /tmp/motiv8-fe-dist.tar.gz -C /var/www/motiv8/dist
sudo chown -R ec2-user:nginx /var/www/motiv8/dist
sudo chmod -R 755 /var/www/motiv8/dist
sudo rm /tmp/motiv8-fe-dist.tar.gz

print_status "Frontend updated successfully"

# Step 2: Update backend
print_section ""
print_section "Step 2: Updating backend..."
echo "----------------------------------------------"

print_info "Stopping backend service..."
sudo systemctl stop motiv8-backend

print_info "Downloading backend from S3..."
BACKEND_URL=$(aws s3 presign s3://$S3_BUCKET/$BACKEND_KEY --expires-in 3600 --region $REGION)
curl -L -o /tmp/motiv8-be.tar.gz "$BACKEND_URL"

print_info "Backing up current backend..."
if [ -d $APP_DIR/motiv8-be ]; then
    sudo mv $APP_DIR/motiv8-be $APP_DIR/motiv8-be.backup.$(date +%Y%m%d_%H%M%S)
fi

print_info "Extracting new backend..."
sudo tar -xzf /tmp/motiv8-be.tar.gz -C $APP_DIR
sudo chown -R ec2-user:ec2-user $APP_DIR/motiv8-be
sudo rm /tmp/motiv8-be.tar.gz

print_info "Installing backend dependencies..."
cd $APP_DIR/motiv8-be
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-web.txt

print_info "Creating uploads directory..."
mkdir -p $APP_DIR/motiv8-be/uploads
sudo chown -R ec2-user:ec2-user $APP_DIR/motiv8-be/uploads
chmod -R 755 $APP_DIR/motiv8-be/uploads

print_status "Backend updated successfully"

# Step 3: Restart services
print_section ""
print_section "Step 3: Restarting services..."
echo "----------------------------------------------"

print_info "Starting backend service..."
sudo systemctl daemon-reload
sudo systemctl start motiv8-backend

sleep 2

print_info "Reloading nginx..."
sudo systemctl reload nginx

# Step 4: Verify deployment
print_section ""
print_section "Step 4: Verifying deployment..."
echo "----------------------------------------------"

# Check backend service
if sudo systemctl is-active --quiet motiv8-backend; then
    print_status "Backend service is running"
else
    echo "⚠ Backend service is not running!"
    echo "Check logs: sudo journalctl -u motiv8-backend -n 50"
fi

# Check nginx
if sudo systemctl is-active --quiet nginx; then
    print_status "Nginx is running"
else
    echo "⚠ Nginx is not running!"
fi

# Test local API endpoint
print_info "Testing local API endpoint..."
if curl -s http://localhost:8000/api/hello | grep -q "ok"; then
    print_status "Backend API responding correctly"
else
    echo "⚠ Backend API not responding as expected"
fi

# Test frontend
print_info "Testing frontend..."
if curl -s https://motiv8me.io/ | grep -q "motiv8me"; then
    print_status "Frontend serving correctly"
else
    echo "⚠ Frontend not serving as expected"
fi

echo ""
echo "================================================"
print_status "Redeploy complete!"
echo "================================================"
echo ""
echo "Check service status:"
echo "  sudo systemctl status motiv8-backend"
echo "  sudo systemctl status nginx"
echo ""
echo "View logs:"
echo "  sudo journalctl -u motiv8-backend -f"
echo "  sudo journalctl -u nginx -f"
echo ""
