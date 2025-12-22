# Credentials and Configuration Guide

## Where to Put Your Credentials

### For AWS Deployment

Your credentials go in **`infrastructure/parameters.json`** (NOT in .env files).

This file has been created for you at: `/Users/jcook/motiv8/infrastructure/parameters.json`

Edit this file and fill in your actual values:

```json
[
  {
    "ParameterKey": "KeyPairName",
    "ParameterValue": "YOUR_EC2_KEY_PAIR_NAME"  // ← Create this with: aws ec2 create-key-pair
  },
  {
    "ParameterKey": "DBMasterPassword",
    "ParameterValue": "YOUR_SECURE_PASSWORD"  // ← Strong password (min 8 chars)
  },
  {
    "ParameterKey": "GoogleClientId",
    "ParameterValue": "YOUR_GOOGLE_CLIENT_ID"  // ← From Google Cloud Console
  },
  {
    "ParameterKey": "GoogleClientSecret",
    "ParameterValue": "YOUR_GOOGLE_CLIENT_SECRET"  // ← From Google Cloud Console
  },
  {
    "ParameterKey": "SMTPUser",
    "ParameterValue": "your-email@gmail.com"  // ← Your Gmail address
  },
  {
    "ParameterKey": "SMTPPassword",
    "ParameterValue": "YOUR_GMAIL_APP_PASSWORD"  // ← Gmail App Password (not regular password!)
  },
  {
    "ParameterKey": "FromEmail",
    "ParameterValue": "your-email@gmail.com"  // ← Email address for sending notifications
  }
]
```

### How Credentials Flow

```
Local Development:
  motiv8-be/.env ──────────────────> Your backend reads this

AWS Deployment:
  infrastructure/parameters.json ──> CloudFormation
                                     ↓
                        AWS Secrets Manager
                                     ↓
                        EC2 instances pull secrets
                                     ↓
                        /app/.env on EC2 instances
                                     ↓
                        Your backend reads this
```

## What Gets Created on EC2 Instances

When the CloudFormation templates deploy, they automatically create `.env` files on each EC2 instance with ALL required variables:

### Web App Instance (`/app/.env`):
```bash
DB_HOST=production-motiv8-db.xxxxx.rds.amazonaws.com
DB_PORT=5432
DB_NAME=motiv8
DB_USERNAME=motiv8admin
DB_PASSWORD=<from Secrets Manager>
JWT_SECRET_KEY=<generated from stack ID>
GOOGLE_CLIENT_ID=<from parameters.json>
GOOGLE_CLIENT_SECRET=<from parameters.json>
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<from parameters.json>
SMTP_PASSWORD=<from parameters.json>
FROM_EMAIL=<from parameters.json>
ENVIRONMENT=production
S3_BUCKET=production-motiv8-uploads-123456789
AWS_REGION=us-east-1
FRONTEND_URL=http://ec2-xx-xxx-xxx-xx.compute-1.amazonaws.com
GOOGLE_REDIRECT_URI=http://ec2-xx-xxx-xxx-xx.compute-1.amazonaws.com:8000/auth/callback
```

### Batch Instance (`/app/batch/.env`):
```bash
# Same as above, plus:
ENVIRONMENT=production
S3_BUCKET=production-motiv8-uploads-123456789
AWS_REGION=us-east-1
```

## Environment Variables Reference

| Variable | Source | Description |
|----------|--------|-------------|
| `DB_HOST` | Auto-generated from RDS | Database endpoint |
| `DB_PORT` | Auto-generated from RDS | Database port (5432) |
| `DB_NAME` | Hardcoded | Database name (motiv8) |
| `DB_USERNAME` | parameters.json | Database master username |
| `DB_PASSWORD` | parameters.json | Database master password |
| `JWT_SECRET_KEY` | Auto-generated | JWT signing key (uses CloudFormation Stack ID) |
| `GOOGLE_CLIENT_ID` | parameters.json | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | parameters.json | Google OAuth Client Secret |
| `SMTP_HOST` | Hardcoded | SMTP server (smtp.gmail.com) |
| `SMTP_PORT` | Hardcoded | SMTP port (587) |
| `SMTP_USER` | parameters.json | SMTP username |
| `SMTP_PASSWORD` | parameters.json | SMTP password (Gmail App Password) |
| `FROM_EMAIL` | parameters.json | From email address |
| `ENVIRONMENT` | Hardcoded in deployment | production |
| `S3_BUCKET` | Auto-generated from S3 | Uploads bucket name |
| `AWS_REGION` | Auto-detected | AWS region (us-east-1) |
| `FRONTEND_URL` | Auto-generated from EC2 | Web app public URL |
| `GOOGLE_REDIRECT_URI` | Auto-generated from EC2 | OAuth callback URL |

## Security Notes

1. **Never commit `parameters.json`** - It's in `.gitignore` for a reason!
2. **Gmail App Password**: Go to https://myaccount.google.com/apppasswords to create one
3. **Google OAuth**: Configure at https://console.cloud.google.com/apis/credentials
4. **Strong DB Password**: Use at least 8 characters with mixed case, numbers, and symbols
5. **EC2 Key Pair**: Create with `aws ec2 create-key-pair` and save the `.pem` file securely

## Quick Setup Checklist

- [ ] Create EC2 key pair and save `.pem` file
- [ ] Get Google OAuth credentials from Google Cloud Console
- [ ] Generate Gmail App Password
- [ ] Fill in `infrastructure/parameters.json` with all credentials
- [ ] Run `./deploy.sh` from infrastructure directory
- [ ] Keep `parameters.json` safe and never commit it!
