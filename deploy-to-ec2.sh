#!/bin/bash
set -e

echo "================================================"
echo "motiv8me EC2 Deployment Script"
echo "================================================"

# Configuration
REPO_URL="https://github.com/jacksoncook/motiv8.git"
APP_DIR="/app"
DOMAIN="motiv8me.io"

# Clean up disk space
echo "Cleaning up disk space..."
sudo yum clean all
sudo rm -rf /tmp/*
sudo journalctl --vacuum-time=1d

# Update system
echo "Updating system packages..."
sudo yum update -y

# Install required packages
echo "Installing packages..."
sudo yum install -y git python3 python3-pip nginx certbot python3-certbot-nginx

# Install Node.js 20.x (Vite requires 20.19+)
echo "Upgrading to Node.js 20.x..."
# Remove old nodejs if present
sudo yum remove -y nodejs nodejs-npm
# Install Node.js 20 from nodesource
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo yum install -y nodejs

# Clone repository
echo "Cloning repository..."
if [ -d "$APP_DIR/.git" ]; then
    echo "Repository already exists, pulling latest..."
    cd $APP_DIR
    sudo git pull origin main
else
    echo "Cloning fresh repository..."
    sudo rm -rf $APP_DIR
    sudo git clone $REPO_URL $APP_DIR
fi

cd $APP_DIR

# Get secrets from AWS Secrets Manager (already has .env from UserData)
echo ".env file already created by CloudFormation UserData"

# Get AWS region and S3 bucket from CloudFormation
echo "Getting S3 bucket from CloudFormation..."
S3_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name production-motiv8-main \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`UploadsBucketName`].OutputValue' \
  --output text 2>/dev/null || echo "production-motiv8-uploads-901478075158")

# Deploy frontend from S3
echo "Deploying frontend from S3..."
mkdir -p /var/www/motiv8
sudo mkdir -p /var/www/motiv8

# Download and extract frontend
echo "Downloading frontend from S3..."
curl -L -o /tmp/motiv8-fe-dist.tar.gz \
  "$(aws s3 presign s3://$S3_BUCKET/deployment/motiv8-fe-dist.tar.gz --expires-in 3600 --region us-east-1)"

echo "Extracting frontend..."
sudo tar -xzf /tmp/motiv8-fe-dist.tar.gz -C /var/www/motiv8/
sudo rm /tmp/motiv8-fe-dist.tar.gz

echo "Setting frontend permissions..."
sudo chown -R ec2-user:nginx /var/www/motiv8/dist
sudo chmod -R 755 /var/www/motiv8/dist

# Install backend Python dependencies in virtual environment
echo "Setting up backend virtual environment..."
cd $APP_DIR/motiv8-be
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
# Use lightweight requirements for web server (no ML dependencies)
pip install -r requirements-web.txt

# Create uploads directory with correct permissions
echo "Setting up uploads directory..."
mkdir -p $APP_DIR/motiv8-be/uploads
sudo chown -R ec2-user:ec2-user $APP_DIR/motiv8-be/uploads
chmod -R 755 $APP_DIR/motiv8-be/uploads

# Configure Nginx
echo "Configuring Nginx..."
sudo tee /etc/nginx/conf.d/default.conf > /dev/null <<'EOF'
# HTTP server - redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name motiv8me.io www.motiv8me.io;

    # Allow Let's Encrypt challenges
    location /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name motiv8me.io www.motiv8me.io;

    # SSL certificates managed by certbot
    ssl_certificate /etc/letsencrypt/live/motiv8me.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/motiv8me.io/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # API routes - proxy to backend
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Auth routes - proxy to backend
    location /auth/ {
        proxy_pass http://localhost:8000/auth/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files for frontend
    location / {
        root /var/www/motiv8/dist;
        try_files $uri $uri/ /index.html;
        index index.html;
    }
}
EOF

# Create Let's Encrypt directory
sudo mkdir -p /var/www/letsencrypt

# Start and enable Nginx
echo "Starting Nginx..."
sudo systemctl enable nginx
sudo systemctl restart nginx

# Create systemd service for backend
echo "Creating backend systemd service..."
sudo tee /etc/systemd/system/motiv8-backend.service > /dev/null <<EOF
[Unit]
Description=motiv8me Backend API
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=$APP_DIR/motiv8-be
Environment="PATH=$APP_DIR/motiv8-be/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/motiv8-be/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Start backend service
echo "Starting backend service..."
sudo systemctl daemon-reload
sudo systemctl enable motiv8-backend
sudo systemctl restart motiv8-backend

# Wait for DNS propagation
echo ""
echo "================================================"
echo "Deployment Complete!"
echo "================================================"
echo ""
echo "If SSL certificates don't exist yet:"
echo "1. Wait for DNS to propagate (5-60 minutes)"
echo "2. Verify DNS with: dig $DOMAIN"
echo "3. Temporarily comment out SSL certificate lines in nginx config"
echo "4. Obtain SSL certificate:"
echo ""
echo "   sudo certbot certonly --webroot \\"
echo "     --webroot-path=/var/www/letsencrypt \\"
echo "     --email jacksoncook73@gmail.com \\"
echo "     --agree-tos \\"
echo "     --no-eff-email \\"
echo "     -d $DOMAIN \\"
echo "     -d www.$DOMAIN"
echo ""
echo "5. Uncomment SSL certificate lines in /etc/nginx/conf.d/motiv8.conf"
echo "6. Reload nginx: sudo systemctl reload nginx"
echo ""
echo "Check service status:"
echo "  sudo systemctl status motiv8-backend"
echo "  sudo systemctl status nginx"
echo ""
echo "View logs:"
echo "  sudo journalctl -u motiv8-backend -f"
echo "  sudo journalctl -u nginx -f"
echo "================================================"
