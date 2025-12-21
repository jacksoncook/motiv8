# Motiv8

A full-stack application with Python backend and future frontend.

## Project Structure

```
motiv8/
├── motiv8-be/          # Python backend service (FastAPI)
└── motiv8-fe/          # Frontend application (React + TypeScript + Vite)
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
