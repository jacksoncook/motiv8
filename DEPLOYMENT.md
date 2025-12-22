# motiv8me Deployment Guide

## Quick Start

### Deploy Code Changes

After pushing changes to GitHub, deploy to production:

```bash
# Deploy both backend and frontend (most common)
./deploy-code.sh

# Deploy only backend changes
./deploy-code.sh --backend-only

# Deploy only frontend changes
./deploy-code.sh --frontend-only
```

### Update Infrastructure

To change instance types, security groups, or other AWS resources:

```bash
cd infrastructure
./update-infrastructure.sh
```

This script will:
1. Validate the CloudFormation template
2. Show you a preview of what will change
3. Ask for confirmation before applying changes
4. Safely update the infrastructure (database is protected with automatic snapshots)

## What Each Script Does

### `deploy-code.sh` - Application Deployment

Deploys your application code to the running EC2 instance via AWS Systems Manager (SSM).

**Backend deployment:**
- Pulls latest code from GitHub
- Installs Python dependencies
- Restarts the backend service

**Frontend deployment:**
- Builds the React app with Vite
- Sets correct permissions for nginx
- Reloads nginx to serve new files

**Usage:**
```bash
./deploy-code.sh [OPTIONS]

Options:
  --backend-only    Deploy only backend code
  --frontend-only   Deploy only frontend code
  --batch-only      Deploy only batch processing script
  --all             Deploy everything including batch
  --help            Show help message
```

### `infrastructure/update-infrastructure.sh` - Infrastructure Updates

Updates the AWS CloudFormation stack for infrastructure changes.

**Use this when you need to:**
- Change EC2 instance types (t3.small → t3.medium, etc.)
- Modify security group rules
- Update database settings (storage size, backup retention, etc.)
- Change any AWS resource configuration

**Features:**
- Shows a change preview before applying
- Requires confirmation (type "yes" to proceed)
- Database is protected with automatic snapshots
- Validates template before attempting update

**Usage:**
```bash
cd infrastructure
./update-infrastructure.sh
```

## Architecture

### Web Server (Always Running - t3.small)
- Handles HTTP requests, uploads, authentication
- Uses `requirements-web.txt` (lightweight, no ML dependencies)
- Does NOT perform face extraction or image generation
- Location: `/app/motiv8-be/` on EC2

### Batch Server (Scheduled Daily - t3.xlarge)
- Runs `batch_generate.py` daily at 6 AM UTC
- Uses full `requirements.txt` (includes ML libraries)
- Performs face extraction AND image generation
- Automatically shuts down after completion

### Face Extraction Flow

1. User uploads selfie → Web server saves to S3
2. Web server sets `selfie_embedding_filename` to `NULL`
3. Batch job runs:
   - Checks if `selfie_embedding_filename` is NULL
   - Downloads image and extracts face
   - Saves embedding to S3
   - Updates database with embedding filename
   - Generates motivational image
   - Sends email

## Database Protection

The RDS database is configured with:
```yaml
DeletionPolicy: Snapshot
UpdateReplacePolicy: Snapshot
```

This means:
- If you delete the CloudFormation stack, a final snapshot is created automatically
- If you update the stack and it requires replacing the database, a snapshot is created first
- **You can safely update CloudFormation templates without losing data**

## Current Stack Names

- Main infrastructure: `production-motiv8-main`
- EC2 instances: `motiv8-ec2-instances`

## Troubleshooting

### Check Backend Logs
```bash
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name motiv8-ec2-instances \
  --query 'Stacks[0].Outputs[?OutputKey==`WebAppInstanceId`].OutputValue' \
  --output text)

aws ssm send-command \
  --instance-ids $INSTANCE_ID \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["sudo journalctl -u motiv8-backend -n 50 --no-pager"]'
```

### SSH to Instance
```bash
aws ssm start-session --target $INSTANCE_ID
```

### Restart Backend Service
```bash
sudo systemctl restart motiv8-backend
sudo systemctl status motiv8-backend
```

### Check Nginx
```bash
sudo journalctl -u nginx -f
sudo systemctl reload nginx
```

## Python 3.9 Compatibility

**CRITICAL:** The EC2 production server runs **Python 3.9**.

Always use Python 3.9 compatible type hint syntax:

**❌ WRONG (Python 3.10+ only):**
```python
def func(param: str | None = None) -> list[str]:
    pass
```

**✅ CORRECT (Python 3.9 compatible):**
```python
from typing import Optional, List

def func(param: Optional[str] = None) -> List[str]:
    pass
```

See `.claude/DEPLOYMENT_NOTES.md` for more details.

## More Information

- Full deployment notes: `.claude/DEPLOYMENT_NOTES.md`
- Infrastructure setup: `infrastructure/README.md`
- Application URL: https://motiv8me.io
