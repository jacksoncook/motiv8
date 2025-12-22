# PostgreSQL and S3 Migration Summary

This document outlines the changes made to support PostgreSQL and S3 storage in production while maintaining SQLite and local filesystem support for development.

## Architecture

### Development Environment
- **Database**: SQLite (`motiv8.db`)
- **Storage**: Local filesystem (`uploads/`, `embeddings/`, `generated/`)

### Production Environment
- **Database**: PostgreSQL (AWS RDS)
- **Storage**: AWS S3 bucket

## Changes Made

### 1. Database Support (`database.py`)

**Before**: Hardcoded SQLite only
```python
SQLALCHEMY_DATABASE_URL = "sqlite:///./motiv8.db"
```

**After**: Auto-detects PostgreSQL from environment
```python
if DB_HOST and DB_USERNAME and DB_PASSWORD:
    # PostgreSQL for production
    SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    # SQLite for development
    SQLALCHEMY_DATABASE_URL = "sqlite:///./motiv8.db"
```

**Environment Variables**:
- `DB_HOST` - Database host (from RDS)
- `DB_PORT` - Database port (5432)
- `DB_NAME` - Database name
- `DB_USERNAME` - Database username
- `DB_PASSWORD` - Database password

### 2. Storage Abstraction (`storage.py` - NEW)

Created a storage abstraction layer that automatically uses S3 or local filesystem based on environment.

**Key Features**:
- Unified API for save/get/delete/exists operations
- Automatic S3 vs local detection via `S3_BUCKET` environment variable
- Handles temporary file downloads for processing
- Automatic cleanup of temp files when using S3

**API**:
```python
# Initialize storage instances
uploads_storage = Storage("uploads")
embeddings_storage = Storage("embeddings")
generated_storage = Storage("generated")

# Operations work the same locally or in S3
uploads_storage.save(filename, data)
uploads_storage.get(filename)
uploads_storage.exists(filename)
uploads_storage.delete(filename)
uploads_storage.download_to_local(filename, local_path)
```

**Environment Variables**:
- `S3_BUCKET` - S3 bucket name (if set, uses S3)
- `AWS_REGION` - AWS region (default: us-east-1)

### 3. Updated Endpoints (`main.py`)

#### `/api/upload`
- Saves uploaded images and embeddings to storage (S3 or local)
- Uses temp files for processing, then uploads to storage
- Cleans up temp files when using S3

#### `/api/selfie/{filename}`
- Serves images from storage (S3 or local)
- Returns image data directly instead of file paths

#### `/api/generate`
- Downloads embedding and image from storage to temp files
- Processes locally (required for ML models)
- Uploads generated image to storage
- Sends email with temp file
- Cleans up temp files when using S3

#### `/api/generated/{filename}`
- Serves generated images from storage (S3 or local)
- Returns PNG data directly

### 4. Updated Batch Script (`batch_generate.py`)

- Uses `database.SessionLocal` for DB connection (supports PostgreSQL)
- Downloads user selfies and embeddings from storage to temp files
- Processes images locally
- Uploads generated images to storage
- Sends emails with temp files
- Cleans up temp files when using S3

## Dependencies Added

Updated `requirements.txt`:
```
psycopg2-binary>=2.9.0  # PostgreSQL adapter
boto3>=1.28.0            # AWS SDK for S3
python-dotenv>=1.0.0     # Environment variable loading
```

## How It Works

### Environment Detection

The system automatically detects the environment:

1. **PostgreSQL Detection**:
   ```python
   if DB_HOST and DB_USERNAME and DB_PASSWORD:
       # Use PostgreSQL
   else:
       # Use SQLite
   ```

2. **S3 Detection**:
   ```python
   USE_S3 = os.getenv("S3_BUCKET") is not None
   ```

### File Processing Flow

#### Development (Local)
```
Upload → Save to local uploads/ → Process → Save to local generated/
```

#### Production (S3)
```
Upload → Save to temp → Process → Upload to S3 → Clean up temp
```

### Why Temp Files in Production?

Machine learning models (InsightFace, Stable Diffusion) require local file access. They cannot directly process S3 URLs or bytes in memory. Therefore:

1. Download from S3 to temp file
2. Process with ML models
3. Upload result to S3
4. Clean up temp file

This is efficient because:
- Temp files are automatically cleaned up
- Processing happens on EC2 instances with local SSD
- Only stores persistent data in S3

## Production Deployment

### Environment Variables Set by CloudFormation

The CloudFormation templates automatically populate these in `/app/.env`:

```bash
# Database (from RDS)
DB_HOST=production-motiv8-db.xxxxx.rds.amazonaws.com
DB_PORT=5432
DB_NAME=motiv8
DB_USERNAME=motiv8admin
DB_PASSWORD=<from Secrets Manager>

# Storage (from S3)
S3_BUCKET=production-motiv8-uploads-123456789
AWS_REGION=us-east-1

# Other vars...
ENVIRONMENT=production
```

### No Code Changes Required

The application automatically:
- Detects PostgreSQL and connects to RDS
- Detects S3 and uses boto3 for storage
- Maintains backward compatibility with development setup

## Testing

### Local Development
```bash
cd motiv8-be
.venv/bin/python main.py
```

Should show:
```
INFO:__main__:Using local filesystem storage
INFO:database:Connected to sqlite:///./motiv8.db
```

### Production (After Deployment)
SSH to EC2 and check logs:
```bash
docker-compose logs
```

Should show:
```
INFO:__main__:Using S3 for persistent storage
INFO:database:Connected to postgresql://...
```

## Migration Path

### For Existing Development Data

If you have existing data in SQLite and local filesystem:

1. **Database Migration**: Export from SQLite, import to PostgreSQL
   ```bash
   # Export from SQLite
   sqlite3 motiv8.db .dump > motiv8_dump.sql

   # Import to PostgreSQL (after connecting to RDS)
   psql -h <rds-endpoint> -U motiv8admin -d motiv8 < motiv8_dump.sql
   ```

2. **File Migration**: Upload local files to S3
   ```bash
   # Upload uploads directory
   aws s3 sync uploads/ s3://production-motiv8-uploads-ACCOUNT/uploads/

   # Upload embeddings directory
   aws s3 sync embeddings/ s3://production-motiv8-uploads-ACCOUNT/embeddings/

   # Upload generated directory
   aws s3 sync generated/ s3://production-motiv8-uploads-ACCOUNT/generated/
   ```

## Benefits

1. **Cost-Effective**: S3 storage is much cheaper than EC2 disk space
2. **Scalable**: S3 can handle unlimited files
3. **Durable**: S3 provides 99.999999999% durability
4. **Portable**: PostgreSQL allows scaling to managed services
5. **Backward Compatible**: Still works locally for development
6. **Zero Config**: Automatically detects environment

## Future Enhancements

Potential improvements:
- S3 signed URLs for direct browser uploads
- CloudFront CDN for serving images
- Read replicas for database scaling
- Multi-region S3 replication
