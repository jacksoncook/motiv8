# Domain Setup Guide for Motiv8

This guide explains how to configure a custom domain for your Motiv8 application deployment.

## Prerequisites

- AWS account with Route 53 access
- Domain purchased (can be through Route 53 or external registrar)
- Deployed CloudFormation stacks (main-stack and ec2-instances)
- Google Cloud Console access for OAuth configuration

## Overview

Setting up a custom domain requires updates in several places:
1. **DNS Configuration** - Route 53 for domain routing
2. **SSL/HTTPS** - Let's Encrypt for secure connections
3. **Google OAuth** - Allowlist your domain
4. **Environment Variables** - Update domain references
5. **CORS Configuration** - Update backend allowed origins
6. **Frontend Build** - Set production API URL

## Step 1: Purchase and Configure Domain

### Option A: Purchase through Route 53

1. **Purchase Domain**:
   ```bash
   # Via AWS Console
   Go to Route 53 → Registered domains → Register domain
   Search for your domain (e.g., motiv8me.io)
   Complete purchase ($12-50/year depending on TLD)
   ```

2. **Create Hosted Zone** (automatic if purchased through Route 53):
   ```bash
   # Verify hosted zone exists
   aws route53 list-hosted-zones
   ```

### Option B: Use External Registrar (GoDaddy, Namecheap, etc.)

1. **Purchase domain** from your preferred registrar

2. **Create Route 53 Hosted Zone**:
   ```bash
   aws route53 create-hosted-zone \
     --name motiv8me.io \
     --caller-reference $(date +%s)
   ```

3. **Update nameservers** at your registrar:
   - Get Route 53 nameservers from hosted zone
   - Update NS records at your registrar to point to Route 53

## Step 2: Create DNS Records

Once your domain is in Route 53, create A records pointing to your EC2 instance.

### Get Your EC2 Public IP

```bash
# From CloudFormation outputs
aws cloudformation describe-stacks \
  --stack-name motiv8-ec2-instances \
  --query 'Stacks[0].Outputs[?OutputKey==`WebAppPublicIP`].OutputValue' \
  --output text
```

### Create A Record for Root Domain

```bash
# Get your hosted zone ID
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones \
  --query 'HostedZones[?Name==`motiv8me.io.`].Id' \
  --output text | cut -d'/' -f3)

# Get your EC2 public IP
WEB_APP_IP=$(aws cloudformation describe-stacks \
  --stack-name motiv8-ec2-instances \
  --query 'Stacks[0].Outputs[?OutputKey==`WebAppPublicIP`].OutputValue' \
  --output text)

# Create A record for root domain (motiv8me.io)
cat > /tmp/create-a-record.json <<EOF
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "motiv8me.io",
      "Type": "A",
      "TTL": 300,
      "ResourceRecords": [{"Value": "${WEB_APP_IP}"}]
    }
  }]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id ${HOSTED_ZONE_ID} \
  --change-batch file:///tmp/create-a-record.json
```

### Create A Record for www Subdomain

```bash
# Create A record for www.motiv8me.io
cat > /tmp/create-www-record.json <<EOF
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "www.motiv8me.io",
      "Type": "A",
      "TTL": 300,
      "ResourceRecords": [{"Value": "${WEB_APP_IP}"}]
    }
  }]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id ${HOSTED_ZONE_ID} \
  --change-batch file:///tmp/create-www-record.json
```

### Verify DNS Propagation

```bash
# Check DNS resolution
dig motiv8me.io
dig www.motiv8me.io

# Or use nslookup
nslookup motiv8me.io
```

DNS propagation can take 5-60 minutes.

## Step 3: Configure SSL/HTTPS with Let's Encrypt

Once your domain resolves to your EC2 instance, set up SSL.

### SSH to Your EC2 Instance

```bash
# Get instance ID
WEB_APP_INSTANCE=$(aws cloudformation describe-stacks \
  --stack-name motiv8-ec2-instances \
  --query 'Stacks[0].Outputs[?OutputKey==`WebAppInstanceId`].OutputValue' \
  --output text)

# SSH to instance
aws ec2 get-console-output --instance-id ${WEB_APP_INSTANCE}
# Or use Session Manager if configured
```

### Install Certbot

```bash
sudo yum install -y certbot python3-certbot-nginx
```

### Install and Configure Nginx

```bash
# Install nginx
sudo yum install -y nginx

# Create nginx config
sudo tee /etc/nginx/conf.d/motiv8.conf > /dev/null <<'EOF'
# Redirect HTTP to HTTPS
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

# HTTPS server (will be configured after getting SSL cert)
server {
    listen 443 ssl http2;
    server_name motiv8me.io www.motiv8me.io;

    # SSL certificates (certbot will add these)
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

# Start nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Obtain SSL Certificate

```bash
# Get SSL certificate
sudo certbot certonly \
  --webroot \
  --webroot-path=/var/www/letsencrypt \
  --email jacksoncook73@gmail.com \
  --agree-tos \
  --no-eff-email \
  -d motiv8me.io \
  -d www.motiv8me.io

# Update nginx config with SSL certificate paths
sudo certbot install \
  --cert-name motiv8me.io \
  --nginx

# Or manually uncomment the SSL lines in /etc/nginx/conf.d/motiv8.conf
sudo sed -i 's/# ssl_certificate/ssl_certificate/g' /etc/nginx/conf.d/motiv8.conf

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### Set Up Auto-Renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Certbot automatically creates a renewal cron job
# Verify it exists
sudo cat /etc/cron.d/certbot
```

## Step 4: Update Google OAuth Configuration

Your Google OAuth app needs to know about your new domain.

### Update Authorized Redirect URIs

1. **Go to Google Cloud Console**:
   - Navigate to https://console.cloud.google.com
   - Select your project

2. **Open OAuth Consent Screen**:
   - Go to "APIs & Services" → "OAuth consent screen"
   - Add authorized domain: `motiv8me.io`

3. **Update OAuth 2.0 Client**:
   - Go to "APIs & Services" → "Credentials"
   - Click your OAuth 2.0 Client ID
   - Under "Authorized JavaScript origins", add:
     ```
     https://motiv8me.io
     https://www.motiv8me.io
     ```
   - Under "Authorized redirect URIs", add:
     ```
     https://motiv8me.io/auth/callback
     https://www.motiv8me.io/auth/callback
     ```
   - Click "Save"

### Update Google Redirect URI Environment Variable

```bash
# Update parameters.json with new domain
cd /Users/jcook/motiv8/infrastructure

# Edit parameters.json
nano parameters.json
```

Update the `GoogleRedirectUri` parameter:
```json
{
  "ParameterKey": "GoogleRedirectUri",
  "ParameterValue": "https://motiv8me.io/auth/callback"
}
```

## Step 5: Update Environment Variables

Several environment variables need to reference your domain.

### Update CloudFormation Parameters

Edit `/Users/jcook/motiv8/infrastructure/parameters.json`:

```json
[
  {
    "ParameterKey": "FrontendUrl",
    "ParameterValue": "https://motiv8me.io"
  },
  {
    "ParameterKey": "GoogleRedirectUri",
    "ParameterValue": "https://motiv8me.io/auth/callback"
  }
]
```

### Redeploy CloudFormation Stack

```bash
cd /Users/jcook/motiv8/infrastructure

# Update main stack (this updates Secrets Manager)
aws cloudformation update-stack \
  --stack-name motiv8-main-infrastructure \
  --template-body file://cloudformation/main-stack.yaml \
  --parameters file://parameters.json \
  --capabilities CAPABILITY_NAMED_IAM

# Wait for completion
aws cloudformation wait stack-update-complete \
  --stack-name motiv8-main-infrastructure
```

### Update EC2 Environment Variables

SSH to your EC2 instance and update the `.env` file:

```bash
# SSH to EC2
ssh ec2-user@motiv8me.io

# Update .env file
sudo nano /app/.env
```

Update these variables:
```bash
FRONTEND_URL=https://motiv8me.io
GOOGLE_REDIRECT_URI=https://motiv8me.io/auth/callback
```

Restart the backend:
```bash
cd /app/motiv8-be
sudo systemctl restart motiv8-backend
# Or if using docker-compose:
# sudo docker-compose restart
```

## Step 6: Update Backend CORS Configuration

Update the backend to allow your domain.

Edit `/Users/jcook/motiv8/motiv8-be/main.py`:

```python
# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Local development
        "https://motiv8me.io",      # Production domain
        "https://www.motiv8me.io"   # Production www subdomain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Commit and push changes:
```bash
cd /Users/jcook/motiv8/motiv8-be
git add main.py
git commit -m "Update CORS for production domain"
git push origin main
```

Then pull on EC2 and restart:
```bash
# On EC2
cd /app/motiv8-be
git pull origin main
sudo systemctl restart motiv8-backend
```

## Step 7: Build and Deploy Frontend

Build the frontend for production with the correct API URL.

### Update Frontend API Configuration

Edit `/Users/jcook/motiv8/motiv8-fe/src/config.ts` (create if doesn't exist):

```typescript
export const API_BASE_URL = import.meta.env.PROD
  ? 'https://motiv8me.io'  // Production
  : 'http://localhost:8000';  // Development
```

Update API calls to use this config:
```typescript
import { API_BASE_URL } from './config';

// In your API calls
const response = await axios.get(`${API_BASE_URL}/api/config`);
```

Or update `src/contexts/AuthContext.tsx` and other files directly:

```typescript
const API_BASE_URL = import.meta.env.PROD
  ? 'https://motiv8me.io'
  : 'http://localhost:8000';
```

### Build Frontend

```bash
cd /Users/jcook/motiv8/motiv8-fe

# Build for production
npm run build

# This creates optimized files in dist/
```

### Deploy Frontend to EC2

```bash
# Copy build to EC2
rsync -avz --delete dist/ ec2-user@motiv8me.io:/tmp/frontend-build/

# On EC2, move to nginx directory
ssh ec2-user@motiv8me.io
sudo rm -rf /app/motiv8-fe/dist
sudo mv /tmp/frontend-build /app/motiv8-fe/dist
sudo chown -R nginx:nginx /app/motiv8-fe/dist
```

Or set up automated deployment via GitHub Actions (recommended).

## Step 8: Update Security Groups

Ensure your EC2 security group allows HTTPS traffic.

```bash
# Get security group ID
WEB_APP_SG=$(aws cloudformation describe-stacks \
  --stack-name motiv8-main-infrastructure \
  --query 'Stacks[0].Outputs[?OutputKey==`WebAppSecurityGroup`].OutputValue' \
  --output text)

# Add HTTPS rule if not exists
aws ec2 authorize-security-group-ingress \
  --group-id ${WEB_APP_SG} \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0
```

This should already be configured in your CloudFormation template, but verify:

```yaml
# In main-stack.yaml SecurityGroup
- IpProtocol: tcp
  FromPort: 443
  ToPort: 443
  CidrIp: 0.0.0.0/0
```

## Step 9: Testing

### Test HTTPS Access

```bash
# Test root domain
curl -I https://motiv8me.io

# Test www subdomain
curl -I https://www.motiv8me.io

# Verify redirect from HTTP to HTTPS
curl -I http://motiv8me.io
# Should return 301 redirect to https://motiv8me.io
```

### Test OAuth Flow

1. Visit `https://motiv8me.io`
2. Click "Login with Google"
3. Complete OAuth flow
4. Should redirect back to `https://motiv8me.io/auth/callback?token=...`
5. Should log you in successfully

### Test API Endpoints

```bash
# Test health check
curl https://motiv8me.io/api/hello

# Test config endpoint
curl https://motiv8me.io/api/config
```

## Step 10: Ongoing Maintenance

### Monitor SSL Certificate Expiry

Let's Encrypt certificates expire after 90 days. Certbot auto-renews them.

```bash
# Check certificate expiry
sudo certbot certificates

# Test renewal process
sudo certbot renew --dry-run
```

### Update DNS if IP Changes

If you stop/start your EC2 instance, the public IP may change:

```bash
# Get new IP
NEW_IP=$(aws ec2 describe-instances \
  --instance-ids ${WEB_APP_INSTANCE} \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

# Update Route 53 A records
# (Use the same process from Step 2 with UPSERT instead of CREATE)
```

### Use Elastic IP (Recommended)

To avoid IP changes, allocate an Elastic IP:

```bash
# Allocate Elastic IP
ALLOCATION_ID=$(aws ec2 allocate-address \
  --domain vpc \
  --query 'AllocationId' \
  --output text)

# Associate with instance
aws ec2 associate-address \
  --instance-id ${WEB_APP_INSTANCE} \
  --allocation-id ${ALLOCATION_ID}

# Update DNS to point to Elastic IP
```

Add to CloudFormation template for persistence:

```yaml
WebAppElasticIP:
  Type: AWS::EC2::EIP
  Properties:
    InstanceId: !Ref WebAppInstance
    Domain: vpc
```

## Complete Checklist

Use this checklist to ensure everything is configured:

- [ ] Domain purchased and DNS configured in Route 53
- [ ] A records created for root domain and www subdomain
- [ ] DNS propagation verified (dig/nslookup)
- [ ] Nginx installed and configured on EC2
- [ ] SSL certificate obtained from Let's Encrypt
- [ ] HTTPS working for both motiv8me.io and www.motiv8me.io
- [ ] HTTP automatically redirects to HTTPS
- [ ] SSL auto-renewal tested
- [ ] Google OAuth authorized origins updated
- [ ] Google OAuth redirect URIs updated with HTTPS domain
- [ ] CloudFormation parameters.json updated with domain
- [ ] CloudFormation stack updated (Secrets Manager has new domain)
- [ ] EC2 .env file updated with FRONTEND_URL and GOOGLE_REDIRECT_URI
- [ ] Backend CORS configuration updated with production domain
- [ ] Backend restarted with new configuration
- [ ] Frontend API configuration updated for production
- [ ] Frontend built for production
- [ ] Frontend deployed to EC2 nginx directory
- [ ] Security group allows HTTPS traffic (port 443)
- [ ] OAuth login flow tested end-to-end
- [ ] API endpoints accessible via HTTPS
- [ ] Elastic IP allocated (optional but recommended)

## Troubleshooting

### DNS Not Resolving

**Problem**: `dig motiv8me.io` returns no A record

**Solutions**:
- Wait longer (DNS propagation can take up to 48 hours but usually 5-60 minutes)
- Verify A record exists in Route 53 console
- Check nameservers are correct if using external registrar
- Try flushing local DNS cache: `sudo dscacheutil -flushcache` (macOS)

### SSL Certificate Error

**Problem**: "Your connection is not private" error

**Solutions**:
- Verify certificate was obtained: `sudo certbot certificates`
- Check nginx SSL configuration: `sudo nginx -t`
- Ensure nginx is using correct certificate paths
- Check certificate isn't expired
- Try reissuing certificate: `sudo certbot delete --cert-name motiv8me.io` then re-run certbot

### OAuth Redirect Not Working

**Problem**: Google OAuth redirects to wrong URL or fails

**Solutions**:
- Verify authorized redirect URI in Google Console exactly matches `https://motiv8me.io/auth/callback`
- Check GOOGLE_REDIRECT_URI in backend .env matches
- Verify FRONTEND_URL in backend .env is set to `https://motiv8me.io`
- Check backend logs: `sudo journalctl -u motiv8-backend -f`

### CORS Errors

**Problem**: Browser shows CORS policy errors

**Solutions**:
- Verify backend CORS configuration includes your domain
- Ensure frontend is using HTTPS (not HTTP)
- Check frontend is making requests to correct API URL
- Restart backend after CORS changes
- Check browser console for exact error message

### 502 Bad Gateway

**Problem**: Nginx returns 502 error

**Solutions**:
- Check backend is running: `sudo systemctl status motiv8-backend`
- Verify backend is listening on port 8000: `sudo netstat -tlnp | grep 8000`
- Check backend logs for errors: `sudo journalctl -u motiv8-backend -f`
- Verify nginx proxy_pass points to correct port

## Cost Considerations

### Domain Costs
- Domain registration: $12-50/year (varies by TLD)
- Route 53 hosted zone: $0.50/month
- Route 53 queries: $0.40 per million queries (minimal cost)

### SSL Costs
- Let's Encrypt: **FREE**
- Auto-renewal: **FREE**

### Elastic IP Costs
- While associated with running instance: **FREE**
- If unassociated: $0.005/hour (~$3.60/month)
- **Recommendation**: Always keep associated or release when not needed

## Summary

After completing this guide, your Motiv8 application will be accessible at:
- **https://motiv8me.io** - Your main domain
- **https://www.motiv8me.io** - www subdomain
- **http://motiv8me.io** - Redirects to HTTPS

All traffic will be encrypted with a valid SSL certificate, Google OAuth will work seamlessly, and your application will be production-ready.

## Next Steps

Consider these enhancements:
1. **CloudFront CDN**: Cache static assets and improve global performance
2. **WAF**: Add AWS WAF for DDoS protection and security rules
3. **Monitoring**: Set up CloudWatch alarms for SSL expiry, instance health
4. **Backup domain**: Consider purchasing .com and .net variations
5. **Email**: Set up professional email addresses (support@motiv8me.io)
