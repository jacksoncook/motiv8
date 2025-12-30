# motiv8me

A full-stack application with Python backend and future frontend.

## Project Structure

```
motiv8/
├── motiv8-be/          # Python backend service (FastAPI)
└── motiv8-fe/          # Frontend application (React + TypeScript + Vite)
```

## Backend Service (motiv8-be)

A Python backend service built with FastAPI!

### Prerequisites

- Python 3.11 or higher
- pip (Python package installer)

### Local Development Setup

1. **Navigate to the backend directory:**
   ```bash
   cd motiv8-be
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   ```
   This creates an isolated Python environment in the `.venv` directory.

3. **Activate the virtual environment:**
   ```bash
   source .venv/bin/activate  # On macOS/Linux
   # OR
   .venv\Scripts\activate     # On Windows
   ```
   Your terminal prompt should now show `(.venv)` indicating the virtual environment is active.

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   This installs FastAPI, Uvicorn, and other required packages.

5. **Run the development server:**
   ```bash
   python main.py
   ```
   The server will start with auto-reload enabled for development.

The API will be available at `http://localhost:8000`

### Testing the API

Once running, try these endpoints:
- Health check: `curl http://localhost:8000/`
- Hello endpoint: `curl http://localhost:8000/api/hello`

### Docker

Build and run with Docker:
```bash
cd motiv8-be
docker build -t motiv8-api .
docker run -p 8000:8000 motiv8-api
```

## API Endpoints

- `GET /` - Health check
- `GET /api/hello` - Returns a hello message

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Frontend Application (motiv8-fe)

A React + TypeScript frontend built with Vite.

### Prerequisites

- Node.js 20+ or higher
- npm (Node package manager)

### Local Development Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd motiv8-fe
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Run the development server:**
   ```bash
   npm run dev
   ```
   The frontend will start with Hot Module Replacement (HMR) enabled.

The app will be available at `http://localhost:5173` (default Vite port)

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run lint` - Lint TypeScript files
- `npm run preview` - Preview production build

### Docker

Build and run with Docker:
```bash
cd motiv8-fe
docker build -t motiv8-fe .
docker run -p 80:80 motiv8-fe
```

## Development Workflow

1. **Start the backend:**
   ```bash
   cd motiv8-be
   source .venv/bin/activate
   python main.py
   ```
   Backend runs on http://localhost:8000

2. **Start the frontend:**
   ```bash
   cd motiv8-fe
   npm run dev
   ```
   Frontend runs on http://localhost:5173

## Production Deployment

Application URL: https://motiv8me.io

### Quick Deployment Commands

#### Deploy Code Changes

```bash
# Deploy both backend and frontend (most common)
./deploy-all.sh

# Or use the infrastructure script
./deploy-code.sh
```

#### Update CloudFormation Stack

Update the main EC2 instances stack (e.g., to deploy new batch code):

```bash
aws cloudformation update-stack \
  --stack-name motiv8-ec2-instances \
  --region us-east-1 \
  --use-previous-template \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=EnvironmentName,UsePreviousValue=true \
    ParameterKey=WebAppInstanceType,UsePreviousValue=true \
    ParameterKey=BatchInstanceType,UsePreviousValue=true \
    ParameterKey=KeyPairName,UsePreviousValue=true \
    ParameterKey=VPCId,UsePreviousValue=true \
    ParameterKey=PublicSubnet1,UsePreviousValue=true \
    ParameterKey=PublicSubnet2,UsePreviousValue=true \
    ParameterKey=HostedZoneId,UsePreviousValue=true \
    ParameterKey=RootDomainName,UsePreviousValue=true \
    ParameterKey=ApiSubdomain,UsePreviousValue=true \
    ParameterKey=BatchSecurityGroup,UsePreviousValue=true \
    ParameterKey=RdsSecurityGroup,UsePreviousValue=true \
    ParameterKey=InstanceProfileName,UsePreviousValue=true \
    ParameterKey=AppSecretsArn,UsePreviousValue=true \
    ParameterKey=UploadsBucket,UsePreviousValue=true \
    ParameterKey=BatchControlRoleArn,UsePreviousValue=true \
    ParameterKey=FrontendPublishVersion,UsePreviousValue=true \
    ParameterKey=ApiDeployVersion,UsePreviousValue=true \
    ParameterKey=BatchDeployVersion,ParameterValue=batch-$(date +%Y%m%d%H%M%S)
```

#### Test Batch Job for a Specific User

Manually trigger a test batch run for a specific email address:

```bash
aws lambda invoke \
  --function-name production-start-batch-instance \
  --region us-east-1 \
  --payload '{"email": "jacksoncook73@gmail.com"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/start-batch.json
```

### Database Access

After SSH-ing into an EC2 instance:

```bash
# Install PostgreSQL client
sudo yum install -y postgresql15

# Connect to the database
psql "host=production-motiv8-db.cwswzlcofoxd.us-east-1.rds.amazonaws.com port=5432 user=motiv8admin dbname=postgres sslmode=require"

# Switch to motiv8 database
\c motiv8

# Query users table
select * from users;
```

### Monitoring

#### View Batch Job Logs

When the batch instance is running:

```bash
journalctl -u motiv8-batch.service -n 200
```

#### View Backend Logs

```bash
sudo journalctl -u motiv8-backend -n 50 --no-pager
```

#### Check Service Status

```bash
sudo systemctl status motiv8-backend
sudo systemctl status nginx
```

### Architecture

- **Web Server (t3.small)**: Always running, handles HTTP requests, uploads, authentication
- **Batch Server (t3.xlarge)**: Runs daily at 3 PM UTC for image generation, auto-shuts down
- **RDS PostgreSQL**: User database
- **S3**: Uploads, embeddings, generated images, frontend static files

### Stack Names

- Main infrastructure: `production-motiv8-main`
- EC2 instances: `motiv8-ec2-instances`

### Additional Documentation

- Full infrastructure setup: `infrastructure/README.md`
- Infrastructure deployment guide: `infrastructure/DEPLOYMENT.md`
- Python 3.9 compatibility notes: `.claude/DEPLOYMENT_NOTES.md`
