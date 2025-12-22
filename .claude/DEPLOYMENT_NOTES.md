# Deployment Notes

## Python Version Compatibility

**CRITICAL:** The EC2 production server runs **Python 3.9**.

### Type Hints Syntax

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

### Common Replacements

- `str | None` → `Optional[str]`
- `int | None` → `Optional[int]`
- `list[str]` → `List[str]`
- `dict[str, int]` → `Dict[str, int]`
- `tuple[str, ...]` → `Tuple[str, ...]`

### Why This Matters

Python 3.10 introduced PEP 604 which allows the `X | Y` union syntax. Code using this syntax will fail on Python 3.9 with:

```
TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
```

## Backend Architecture

### Web Server (Always Running - t3.small)
- Uses `requirements-web.txt` (lightweight, no ML dependencies)
- Handles uploads, authentication, API requests
- **Does NOT perform face extraction or image generation**
- Location: `/app/motiv8-be/` on EC2

### Batch Server (Scheduled Daily - t3.xlarge)
- Uses full `requirements.txt` (includes ML libraries)
- Runs `batch_generate.py` daily at 6 AM UTC
- **Performs face extraction AND image generation**
- Automatically shuts down after completion

### Face Extraction Flow

1. User uploads selfie → Web server saves image to S3
2. Web server sets `selfie_embedding_filename` to `NULL`
3. Batch job runs:
   - Checks if `selfie_embedding_filename` is NULL
   - If NULL, downloads image and extracts face
   - Saves embedding to S3
   - Updates database with embedding filename
   - Generates motivational image
   - Sends email

## Deployment Commands

### Quick Deployment Scripts

**Deploy Code Changes (Recommended)**
```bash
# Deploy both backend and frontend (most common)
./deploy-code.sh

# Deploy only backend
./deploy-code.sh --backend-only

# Deploy only frontend
./deploy-code.sh --frontend-only

# Deploy everything including batch script
./deploy-code.sh --all
```

**Run Batch Job Manually**
```bash
# Manually trigger batch image generation and email sending
./run-batch-job.sh

# Preview what would happen without running
./run-batch-job.sh --dry-run
```

**Update Infrastructure (Instance types, security groups, etc.)**
```bash
cd infrastructure
./update-infrastructure.sh
```

### Manual Deployment Commands (for reference)

**Deploy Backend Changes**
```bash
# Get instance ID
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name motiv8-ec2-instances \
  --query 'Stacks[0].Outputs[?OutputKey==`WebAppInstanceId`].OutputValue' \
  --output text)

# Deploy
aws ssm send-command \
  --instance-ids $INSTANCE_ID \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=[
    "cd /app && sudo git pull origin main",
    "sudo systemctl restart motiv8-backend"
  ]'
```

**Check Logs**
```bash
aws ssm send-command \
  --instance-ids $INSTANCE_ID \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["sudo journalctl -u motiv8-backend -n 50 --no-pager"]'
```

## Stack Names

- Main infrastructure: `production-motiv8-main`
- EC2 instances: `motiv8-ec2-instances`

## Current Deployment Scripts

### Active Scripts (used for day-to-day deployments)

**`deploy-code.sh`** - Deploys application code (Recommended)
- Pulls latest code from GitHub
- Installs dependencies
- Builds frontend with npm
- Restarts backend service
- Supports --backend-only, --frontend-only flags
- Runs via SSM commands

**`run-batch-job.sh`** - Manually triggers batch processing
- Finds users with today as workout day
- Extracts face embeddings (if needed)
- Generates motivational images
- Sends emails with generated images
- Creates separate ML environment (batch-venv) on first run
- Useful for testing or immediate processing

**`deploy-to-ec2.sh`** - Full EC2 setup script (Legacy)
- Used for initial EC2 instance setup
- Pulls latest code from GitHub
- Builds frontend with npm
- Sets up backend with Python virtualenv
- Configures nginx and systemd services
- Now superseded by deploy-code.sh for regular deployments

### Archive Scripts (used only for initial setup or disaster recovery)

**`infrastructure/deploy.sh`** - Creates CloudFormation stacks from scratch
- Note: EC2 stack name in script (`production-motiv8-ec2`) doesn't match actual deployed name (`motiv8-ec2-instances`)
- Only needed when creating infrastructure from scratch

**`infrastructure/setup-domain-and-deploy.sh`** - Full automated setup including DNS
- Used for initial deployment only
- Sets up Route53 DNS records and SSL certificates

## Database Protection

**CRITICAL:** The RDS database has been configured with:
```yaml
DeletionPolicy: Snapshot
UpdateReplacePolicy: Snapshot
```

This means:
- If you delete the CloudFormation stack, a final snapshot will be created
- If you update the stack and it requires replacing the database, a snapshot will be created first
- **You can safely update the CloudFormation template without losing data**
