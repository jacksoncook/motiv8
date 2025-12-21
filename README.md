# Motiv8

A full-stack application with Python backend and future frontend.

## Project Structure

```
motiv8/
├── motiv8-be/          # Python backend service
└── (frontend TBD)      # Frontend application (coming soon)
```

## Backend Service (motiv8-be)

A Python backend service built with FastAPI.

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
