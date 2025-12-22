# motiv8me AWS Deployment Guide

This guide explains how to deploy motiv8me to AWS using CloudFormation, with a cost-effective architecture that separates the web app from batch image generation.

## Architecture Overview

### Components

1. **Web App EC2 (Always Running - t3.small)**
   - Handles user authentication
   - Manages selfie uploads
   - Workout day settings
   - Serves React frontend
   - Cost: ~$15/month

2. **Batch EC2 (Scheduled Daily - t3.xlarge)**
   - Runs once per day at 6 AM
   - Generates images for users with today as workout day
   - Sends motivation emails
   - Auto-shuts down after completion
   - Cost: ~$40/month (1 hour/day)

3. **RDS PostgreSQL (db.t3.micro)**
   - User database
   - Cost: ~$15/month

4. **S3 Buckets**
   - Uploads (selfies, embeddings, generated images)
   - Frontend static files
   - Cost: ~$10/month

**Total Estimated Cost: ~$80/month**

## Prerequisites

1. **AWS Account** with admin access
2. **AWS CLI** installed and configured
3. **Docker** installed (for local testing)
4. **Domain** (optional, for custom domain)
5. **Google OAuth Credentials** from Google Cloud Console
6. **SMTP Credentials** (Gmail App Password recommended)

## Step 1: Prepare Configuration

### 1.1 Create Parameters File

Create `infrastructure/parameters.json`:

```json
[
  {
    "ParameterKey": "EnvironmentName",
    "ParameterValue": "production"
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
    "ParameterValue": "YOUR_EC2_KEY_PAIR_NAME"
  },
  {
    "ParameterKey": "DBMasterUsername",
    "ParameterValue": "motiv8admin"
  },
  {
    "ParameterKey": "DBMasterPassword",
    "ParameterValue": "YOUR_SECURE_PASSWORD"
  },
  {
    "ParameterKey": "DomainName",
    "ParameterValue": "motiv8me.io"
  },
  {
    "ParameterKey": "GoogleClientId",
    "ParameterValue": "YOUR_GOOGLE_CLIENT_ID"
  },
  {
    "ParameterKey": "GoogleClientSecret",
    "ParameterValue": "YOUR_GOOGLE_CLIENT_SECRET"
  },
  {
    "ParameterKey": "SMTPUser",
    "ParameterValue": "your-email@gmail.com"
  },
  {
    "ParameterKey": "SMTPPassword",
    "ParameterValue": "YOUR_GMAIL_APP_PASSWORD"
  },
  {
    "ParameterKey": "FromEmail",
    "ParameterValue": "your-email@gmail.com"
  }
]
```

**IMPORTANT:** Add this file to `.gitignore` - never commit credentials!

### 1.2 Create EC2 Key Pair

```bash
aws ec2 create-key-pair \
  --key-name motiv8-keypair \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/motiv8-keypair.pem

chmod 400 ~/.ssh/motiv8-keypair.pem
```

## Step 2: Deploy Infrastructure

### 2.1 Deploy Main Stack

```bash
cd infrastructure

aws cloudformation create-stack \
  --stack-name motiv8-main \
  --template-body file://cloudformation/main-stack.yaml \
  --parameters file://parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

Monitor deployment:
```bash
aws cloudformation wait stack-create-complete \
  --stack-name motiv8-main \
  --region us-east-1
```

### 2.2 Get Stack Outputs

```bash
aws cloudformation describe-stacks \
  --stack-name motiv8-main \
  --query 'Stacks[0].Outputs' \
  --region us-east-1
```

Save these outputs - you'll need them for the next step.

### 2.3 Deploy EC2 Instances

Get the required outputs from main stack:

```bash
aws cloudformation describe-stacks \
  --stack-name motiv8-main \
  --query 'Stacks[0].Outputs' \
  --region us-east-1
```

Create `ec2-parameters.json` with values from the main stack outputs:

```json
[
  {
    "ParameterKey": "EnvironmentName",
    "ParameterValue": "production"
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
    "ParameterValue": "motiv8-keypair"
  },
  {
    "ParameterKey": "VPCId",
    "ParameterValue": "FROM_MAIN_STACK_OUTPUT"
  },
  {
    "ParameterKey": "PublicSubnet1",
    "ParameterValue": "FROM_MAIN_STACK_OUTPUT"
  },
  {
    "ParameterKey": "WebAppSecurityGroup",
    "ParameterValue": "FROM_MAIN_STACK_OUTPUT"
  },
  {
    "ParameterKey": "BatchSecurityGroup",
    "ParameterValue": "FROM_MAIN_STACK_OUTPUT"
  },
  {
    "ParameterKey": "InstanceProfile",
    "ParameterValue": "FROM_MAIN_STACK_OUTPUT"
  },
  {
    "ParameterKey": "AppSecretsArn",
    "ParameterValue": "FROM_MAIN_STACK_OUTPUT"
  },
  {
    "ParameterKey": "UploadsBucket",
    "ParameterValue": "FROM_MAIN_STACK_OUTPUT"
  },
  {
    "ParameterKey": "BatchControlRoleArn",
    "ParameterValue": "FROM_MAIN_STACK_OUTPUT"
  }
]
```

Deploy:
```bash
aws cloudformation create-stack \
  --stack-name motiv8-ec2 \
  --template-body file://cloudformation/ec2-instances.yaml \
  --parameters file://ec2-parameters.json \
  --region us-east-1
```

## Step 3: Deploy Application Code

### 3.1 Build Backend Docker Image

From `motiv8-be` directory:

```bash
# Install production dependencies
pip freeze > requirements.txt

# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Build and tag
docker build -t motiv8-backend .
```

### 3.2 Push to ECR (Optional but Recommended)

```bash
# Create ECR repository
aws ecr create-repository --repository-name motiv8-backend --region us-east-1

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag and push
docker tag motiv8-backend:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/motiv8-backend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/motiv8-backend:latest
```

### 3.3 Deploy Frontend to S3

From `motiv8-fe` directory:

```bash
# Update API URL in production
# Edit src/components/ImageUpload.tsx and src/contexts/AuthContext.tsx
# Change API_BASE_URL to your EC2 public DNS

# Build frontend
npm run build

# Upload to S3
aws s3 sync dist/ s3://production-motiv8-frontend-YOUR_ACCOUNT_ID/ \
  --delete \
  --cache-control "public, max-age=31536000"
```

### 3.4 SSH to Web App Instance and Deploy

```bash
# Get instance IP
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=production-webapp" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text

# SSH to instance
ssh -i ~/.ssh/motiv8-keypair.pem ec2-user@INSTANCE_IP

# On the instance:
cd /app

# Create docker-compose.yaml
cat > docker-compose.yaml << 'EOF'
version: '3.8'

services:
  backend:
    image: YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/motiv8-backend:latest
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - uploads:/app/uploads
      - embeddings:/app/embeddings
      - generated:/app/generated
    restart: always

volumes:
  uploads:
  embeddings:
  generated:
EOF

# Start the service
systemctl start motiv8-webapp
```

## Step 4: Setup Database

```bash
# SSH to web app instance
ssh -i ~/.ssh/motiv8-keypair.pem ec2-user@INSTANCE_IP

# Run migrations
docker exec motiv8-backend python -c "from database import init_db; init_db()"
```

## Step 5: Test Batch Job

```bash
# Manually start batch instance
aws ec2 start-instances --instance-ids BATCH_INSTANCE_ID

# SSH to batch instance
ssh -i ~/.ssh/motiv8-keypair.pem ec2-user@BATCH_INSTANCE_IP

# Check logs
sudo journalctl -u motiv8-batch -f
```

## Step 6: Configure Domain (Optional)

### 6.1 Route 53 Setup

```bash
# Create hosted zone (if not exists)
aws route53 create-hosted-zone --name motiv8me.io --caller-reference $(date +%s)

# Get name servers and update at your domain registrar

# Create A record pointing to Web App EC2
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch file://dns-record.json
```

### 6.2 Setup HTTPS with Let's Encrypt

```bash
# SSH to web app instance
ssh -i ~/.ssh/motiv8-keypair.pem ec2-user@INSTANCE_IP

# Install certbot
sudo yum install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d motiv8me.io -d www.motiv8me.io
```

## Updating the Application

### Update Backend

```bash
cd motiv8-be

# Build new image
docker build -t motiv8-backend:latest .

# Push to ECR
docker tag motiv8-backend:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/motiv8-backend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/motiv8-backend:latest

# SSH to web app and restart
ssh -i ~/.ssh/motiv8-keypair.pem ec2-user@INSTANCE_IP
cd /app
docker-compose pull
docker-compose up -d
```

### Update Frontend

```bash
cd motiv8-fe

npm run build

aws s3 sync dist/ s3://production-motiv8-frontend-YOUR_ACCOUNT_ID/ --delete
```

## Monitoring & Maintenance

### View Logs

```bash
# Web app logs
ssh -i ~/.ssh/motiv8-keypair.pem ec2-user@WEBAPP_IP
docker-compose logs -f

# Batch job logs
ssh -i ~/.ssh/motiv8-keypair.pem ec2-user@BATCH_IP
sudo journalctl -u motiv8-batch -f
```

### Database Backup

```bash
# RDS automated backups are enabled (7 days retention)
# Manual snapshot:
aws rds create-db-snapshot \
  --db-instance-identifier production-motiv8-db \
  --db-snapshot-identifier manual-backup-$(date +%Y%m%d)
```

### Cost Optimization

1. **Stop batch instance when not needed:**
   ```bash
   aws ec2 stop-instances --instance-ids BATCH_INSTANCE_ID
   ```

2. **Use Reserved Instances** for web app (save ~40%)

3. **Enable S3 Intelligent-Tiering** for old uploads

## Troubleshooting

### Web App Not Accessible

```bash
# Check security group
aws ec2 describe-security-groups --group-ids SG_ID

# Check instance status
aws ec2 describe-instances --instance-ids INSTANCE_ID

# Check logs
ssh -i ~/.ssh/motiv8-keypair.pem ec2-user@INSTANCE_IP
docker-compose logs
```

### Batch Job Failing

```bash
# Check CloudWatch Logs
aws logs tail /aws/lambda/production-start-batch-instance

# Manually run batch job
ssh -i ~/.ssh/motiv8-keypair.pem ec2-user@BATCH_IP
cd /app/batch
./run-batch.sh
```

### Database Connection Issues

```bash
# Test from web app instance
ssh -i ~/.ssh/motiv8-keypair.pem ec2-user@WEBAPP_IP
telnet DB_ENDPOINT 5432

# Check security group rules
aws ec2 describe-security-groups --group-ids DB_SG_ID
```

## Destroying Infrastructure

```bash
# Delete EC2 stack
aws cloudformation delete-stack --stack-name motiv8-ec2

# Delete main stack
aws cloudformation delete-stack --stack-name motiv8-main

# Empty and delete S3 buckets manually
aws s3 rm s3://production-motiv8-uploads-YOUR_ACCOUNT_ID --recursive
aws s3 rb s3://production-motiv8-uploads-YOUR_ACCOUNT_ID
```

## Security Best Practices

1. **Restrict SSH access** - Update security group to only allow your IP
2. **Use Secrets Manager** - Never hardcode credentials
3. **Enable CloudTrail** - Audit all API calls
4. **Regular updates** - Keep OS and dependencies updated
5. **Use IAM roles** - No hardcoded AWS credentials
6. **Enable MFA** - For AWS account access

## Support

For issues or questions:
- Check CloudWatch Logs
- Review CloudFormation Events
- SSH to instances and check application logs
