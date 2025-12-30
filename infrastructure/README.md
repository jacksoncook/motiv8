# motiv8me Infrastructure

This directory contains AWS CloudFormation templates and deployment scripts for the motiv8me application.

## Architecture

motiv8me uses a cost-optimized AWS architecture that separates the always-running web application from the scheduled batch image generation:

- **Web App EC2** (t3.small): Always running, handles user authentication, selfie uploads, and serves the React frontend (~$15/month)
- **Batch EC2** (g4dn.xlarge): Runs once daily at 6 AM UTC, generates images and sends emails, then auto-shuts down (~$40/month for 1 hour/day)
- **RDS PostgreSQL** (db.t3.micro): User database (~$15/month)
- **S3 Buckets**: Storage for uploads and frontend hosting (~$10/month)

**Total estimated cost: ~$80/month**

## Files

```
infrastructure/
├── cloudformation/
│   ├── main-stack.yaml        # VPC, RDS, S3, IAM, Secrets Manager
│   └── ec2-instances.yaml     # EC2 instances, Lambda, EventBridge
├── deploy.sh                   # Automated deployment script
├── DEPLOYMENT.md               # Detailed deployment guide
├── README.md                   # This file
└── .gitignore                  # Prevents committing sensitive files
```

## Quick Start

### Prerequisites

1. AWS CLI installed and configured with credentials
2. jq installed (for JSON parsing in deploy script)
3. An AWS EC2 key pair created
4. Google OAuth credentials
5. SMTP credentials for sending emails

### Deployment

1. Create `parameters.json` with your configuration:

```json
[
  {
    "ParameterKey": "EnvironmentName",
    "ParameterValue": "production"
  },
  {
    "ParameterKey": "KeyPairName",
    "ParameterValue": "YOUR_KEY_PAIR_NAME"
  },
  {
    "ParameterKey": "DBMasterPassword",
    "ParameterValue": "YOUR_SECURE_PASSWORD"
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

2. Run the deployment script:

```bash
cd infrastructure
./deploy.sh
```

The script will:
- Deploy the main infrastructure stack (VPC, RDS, S3, etc.)
- Wait for completion
- Extract outputs and create ec2-parameters.json
- Deploy the EC2 instances stack
- Display connection information

### Manual Deployment

If you prefer to deploy manually or need more control, see [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step instructions.

## Stack Dependencies

```
main-stack.yaml
    ↓ (exports VPC, Security Groups, S3, IAM, etc.)
ec2-instances.yaml
    ↓ (creates instances, Lambda, EventBridge)
```

The EC2 instances stack depends on outputs from the main stack. Always deploy `main-stack.yaml` first.

## Updating Infrastructure

To update the infrastructure after making changes to the templates:

```bash
# Update main stack
aws cloudformation update-stack \
  --stack-name production-motiv8-main \
  --template-body file://cloudformation/main-stack.yaml \
  --parameters file://parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Update EC2 stack
aws cloudformation update-stack \
  --stack-name production-motiv8-ec2 \
  --template-body file://cloudformation/ec2-instances.yaml \
  --parameters file://ec2-parameters.json \
  --region us-east-1
```

## Destroying Infrastructure

⚠️ **Warning**: This will delete all resources and data!

```bash
# Delete EC2 stack first
aws cloudformation delete-stack --stack-name production-motiv8-ec2

# Wait for deletion
aws cloudformation wait stack-delete-complete --stack-name production-motiv8-ec2

# Empty S3 buckets (required before deleting)
aws s3 rm s3://production-motiv8-uploads-YOUR_ACCOUNT_ID --recursive
aws s3 rm s3://production-motiv8-frontend-YOUR_ACCOUNT_ID --recursive

# Delete main stack
aws cloudformation delete-stack --stack-name production-motiv8-main
```

## Security Notes

- `parameters.json` and `ec2-parameters.json` contain sensitive credentials and are excluded from git
- Never commit these files to version control
- Use AWS Secrets Manager for storing credentials in production (already configured in templates)
- Restrict SSH access by updating security group rules to allow only your IP
- Use strong passwords for database and other services
- Enable MFA on your AWS account

## Monitoring

### View Stack Status

```bash
aws cloudformation describe-stacks \
  --stack-name production-motiv8-main \
  --region us-east-1
```

### View Stack Events

```bash
aws cloudformation describe-stack-events \
  --stack-name production-motiv8-main \
  --region us-east-1 \
  --max-items 10
```

### Check Lambda Logs

```bash
aws logs tail /aws/lambda/production-start-batch-instance --follow
```

## Support

For detailed deployment instructions, troubleshooting, and operational procedures, see [DEPLOYMENT.md](DEPLOYMENT.md).
