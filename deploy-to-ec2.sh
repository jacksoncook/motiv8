#!/bin/bash
set -e

echo "================================================"
echo "Motiv8 EC2 Deployment Script"
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
echo "Installing Node.js 20.x..."
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo yum install -y nodejs

# Install Python dependencies globally for system Python
echo "Installing Python packages..."
sudo pip3 install --upgrade pip || echo "pip upgrade skipped (already managed by system)"
sudo pip3 install fastapi uvicorn sqlalchemy psycopg2-binary boto3 python-dotenv authlib httpx python-jose[cryptography]

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

# Build frontend
echo "Building frontend..."
cd $APP_DIR/motiv8-fe
npm install
npm run build

# Install backend Python dependencies in virtual environment
echo "Setting up backend virtual environment..."
cd $APP_DIR/motiv8-be
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
# Use lightweight requirements for web server (no ML dependencies)
pip install -r requirements-web.txt

# Configure Nginx
echo "Configuring Nginx..."
sudo tee /etc/nginx/conf.d/motiv8.conf > /dev/null <<'EOF'
# HTTP server - redirect to HTTPS
server {
    listen 80;
    server_name motiv8me.io www.motiv8me.io;

    # Allow Let's Encrypt challenges
    location /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name motiv8me.io www.motiv8me.io;

    # SSL certificates (will be added by certbot)
    # ssl_certificate /etc/letsencrypt/live/motiv8me.io/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/motiv8me.io/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    # Frontend (React app)
    location / {
        root /app/motiv8-fe/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Auth endpoints
    location /auth {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
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
Description=Motiv8 Backend API
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
echo "Next steps:"
echo "1. Wait for DNS to propagate (5-60 minutes)"
echo "2. Verify DNS with: dig $DOMAIN"
echo "3. Once DNS resolves, obtain SSL certificate:"
echo ""
echo "   sudo certbot certonly --webroot \\"
echo "     --webroot-path=/var/www/letsencrypt \\"
echo "     --email jacksoncook73@gmail.com \\"
echo "     --agree-tos \\"
echo "     --no-eff-email \\"
echo "     -d $DOMAIN \\"
echo "     -d www.$DOMAIN"
echo ""
echo "4. Update nginx to use SSL certificate:"
echo "   sudo certbot install --cert-name $DOMAIN --nginx"
echo ""
echo "5. Reload nginx:"
echo "   sudo systemctl reload nginx"
echo ""
echo "Check service status:"
echo "  sudo systemctl status motiv8-backend"
echo "  sudo systemctl status nginx"
echo ""
echo "View logs:"
echo "  sudo journalctl -u motiv8-backend -f"
echo "  sudo journalctl -u nginx -f"
echo "================================================"
