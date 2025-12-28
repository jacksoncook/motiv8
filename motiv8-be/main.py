from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, Response
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
import shutil
from pathlib import Path
from datetime import datetime, date, timedelta
import logging
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Load environment variables BEFORE importing other modules
load_dotenv()

from database import get_db, init_db
from models import User, GeneratedImage
from migrate import migrate_database
from email_utils import send_motivation_email
from storage import uploads_storage, embeddings_storage, generated_storage, USE_S3
from auth import (
    create_access_token,
    get_current_user,
    get_current_user_from_query,
    get_or_create_user,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PUBLIC_API_BASE = os.getenv("PUBLIC_API_BASE", "http://localhost:8000")

app = FastAPI(title="motiv8me API", version="1.0.0")

# Configure CORS - allow specific origins when using credentials
ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Local development
    "http://localhost:3000",  # Alternative local port
    "https://motiv8me.io",    # Production frontend
    "https://www.motiv8me.io" # Production frontend with www
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware for OAuth
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
)

# Proxy headers are handled by uvicorn with --proxy-headers flag

# Configure OAuth
oauth = OAuth()
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    # Run migrations first to add any missing columns to existing tables
    migrate_database()
    # Then ensure all tables exist
    init_db()
    logger.info("Database initialized")

# Create local directories for development or temporary storage
# In production with S3, these will be used for temporary file processing
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

EMBEDDINGS_DIR = Path("embeddings")
EMBEDDINGS_DIR.mkdir(exist_ok=True)

GENERATED_DIR = Path("generated")
GENERATED_DIR.mkdir(exist_ok=True)

# Log storage configuration
if USE_S3:
    logger.info("Using S3 for persistent storage, local directories for temporary processing")
else:
    logger.info("Using local filesystem for storage")


@app.get("/")
async def root():
    """Root endpoint"""
    return {"status": "ok", "service": "motiv8-api"}


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancer"""
    return {"status": "healthy"}


@app.get("/api/config")
async def get_config():
    """Get public configuration (environment, features, etc.)"""
    environment = os.getenv("ENVIRONMENT", "development")
    return {
        "environment": environment,
        "features": {
            "onDemandGeneration": environment == "development"
        }
    }


@app.get("/api/hello")
async def hello():
    """Returns a hello message"""
    return {"message": "hello"}


@app.post("/api/upload")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a selfie image. Face extraction will be done during batch processing."""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Delete old selfie files if updating
        is_update = False
        if current_user.selfie_filename:
            is_update = True
            # Delete old files from storage (S3 or local)
            uploads_storage.delete(current_user.selfie_filename)
            # Also delete old embedding if it exists
            if current_user.selfie_embedding_filename:
                embeddings_storage.delete(current_user.selfie_embedding_filename)

        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{timestamp}_{file.filename}"

        # Save to temporary local file
        temp_file_path = UPLOAD_DIR / unique_filename
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"Image saved temporarily: {temp_file_path}")

        # Get file size before uploading
        file_size = os.path.getsize(temp_file_path)

        # Upload image to storage (S3 or local)
        uploads_storage.save_from_file(unique_filename, str(temp_file_path))

        logger.info(f"File uploaded to storage: {unique_filename}")

        # Clean up temp file if using S3
        if USE_S3:
            os.remove(temp_file_path)
            logger.info("Cleaned up temporary file")

        # Update user's selfie in database
        # Note: embedding will be created during batch processing
        current_user.selfie_filename = unique_filename
        current_user.selfie_embedding_filename = None  # Will be set by batch job
        db.commit()
        db.refresh(current_user)

        logger.info(f"Updated user {current_user.email} selfie")

        return JSONResponse(
            status_code=200,
            content={
                "message": "Selfie updated successfully. Face extraction will occur during next batch processing." if is_update else "Selfie uploaded successfully. Face extraction will occur during next batch processing.",
                "filename": unique_filename,
                "original_filename": file.filename,
                "content_type": file.content_type,
                "size_bytes": file_size,
                "is_update": is_update
            }
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


class GenerateRequest(BaseModel):
    """Request body for image generation"""
    embedding_filename: str
    image_filename: Optional[str] = None  # Original uploaded image filename
    prompt: str = "professional full body photo of a person with extremely muscular bodybuilder physique, highly detailed, 8k, photorealistic"
    negative_prompt: str = "blurry, low quality, distorted, deformed, ugly, bad anatomy, monochrome, lowres, bad anatomy, worst quality, low quality"
    num_inference_steps: int = 30
    guidance_scale: float = 7.5
    seed: Optional[int] = None
    scale: float = 0.8  # IP-Adapter scale (0-1), controls how much face is preserved


@app.post("/api/generate")
async def generate_image(
    request: GenerateRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate an image using a face embedding (development only)"""
    # Only allow in development environment
    environment = os.getenv("ENVIRONMENT", "development")
    if environment != "development":
        raise HTTPException(
            status_code=403,
            detail="On-demand image generation is disabled in production. Images are generated daily via batch job."
        )

    try:
        # Lazy import image generator (only needed in development)
        from image_generator import get_image_generator

        # Check if embedding file exists in storage
        if not embeddings_storage.exists(request.embedding_filename):
            raise HTTPException(
                status_code=404,
                detail=f"Embedding file not found: {request.embedding_filename}"
            )

        logger.info(f"Generating image using embedding: {request.embedding_filename}")

        # Download embedding to local temp file for processing
        temp_embedding_path = EMBEDDINGS_DIR / request.embedding_filename
        embeddings_storage.download_to_local(request.embedding_filename, str(temp_embedding_path))

        # Get the original image if provided and download to temp location
        temp_image_path = None
        if request.image_filename:
            if uploads_storage.exists(request.image_filename):
                temp_image_path = UPLOAD_DIR / request.image_filename
                uploads_storage.download_to_local(request.image_filename, str(temp_image_path))
            else:
                logger.warning(f"Image file not found: {request.image_filename}")

        # Generate image using local temp files
        generator = get_image_generator()
        result = generator.generate_image(
            embedding_path=str(temp_embedding_path),
            image_path=str(temp_image_path) if temp_image_path else None,
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            seed=request.seed,
            scale=request.scale
        )

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Image generation failed: {result.get('error', 'Unknown error')}"
            )

        # Save generated image to temp location
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(request.embedding_filename)[0]
        generated_filename = f"{timestamp}_{base_name}_generated.png"
        temp_generated_path = GENERATED_DIR / generated_filename

        generator.save_image(result["image"], str(temp_generated_path))

        # Upload generated image to storage
        generated_storage.save_from_file(generated_filename, str(temp_generated_path))

        logger.info(f"Image generated and uploaded to storage: {generated_filename}")

        # Send motivation email to user with local temp file
        email_sent = send_motivation_email(current_user.email, str(temp_generated_path))

        # Clean up temp files if using S3
        if USE_S3:
            if temp_embedding_path.exists():
                os.remove(temp_embedding_path)
            if temp_image_path and temp_image_path.exists():
                os.remove(temp_image_path)
            if temp_generated_path.exists():
                os.remove(temp_generated_path)
            logger.info("Cleaned up temporary files")
        if email_sent:
            logger.info(f"Motivation email sent to {current_user.email}")
        else:
            logger.warning(f"Failed to send motivation email to {current_user.email}")

        return JSONResponse(
            status_code=200,
            content={
                "message": "Image generated successfully",
                "generated_filename": generated_filename,
                "embedding_filename": request.embedding_filename,
                "prompt": request.prompt,
                "email_sent": email_sent
            }
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.get("/api/generated/{filename}")
async def get_generated_image(filename: str):
    """Serve a generated image"""
    # Check if file exists in storage
    if not generated_storage.exists(filename):
        raise HTTPException(status_code=404, detail="Image not found")

    # Get file from storage (S3 or local)
    try:
        file_data = generated_storage.get(filename)
        # Generated images are always PNG
        return Response(content=file_data, media_type='image/png')
    except Exception as e:
        logger.error(f"Error serving generated image: {e}")
        raise HTTPException(status_code=500, detail="Error serving image")


@app.get("/api/daily-motivation")
async def get_daily_motivation(
    date_str: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the generated image for a specific date for the current user

    Args:
        date_str: Date in YYYY-MM-DD format (treated as logical day, not converted to UTC)

    Returns:
        JSON with s3_key and generation timestamp if found, otherwise 404
    """
    try:
        # Parse the date string and use it directly as the query date
        query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Query for generated images for this user and date, ordered by timestamp descending
    generated_image = db.query(GeneratedImage).filter(
        GeneratedImage.user_id == current_user.id,
        GeneratedImage.generation_date == query_date
    ).order_by(GeneratedImage.generated_at_millis.desc()).first()

    if not generated_image:
        raise HTTPException(status_code=404, detail="No generated image found for this date")

    # Extract filename from s3_key (format: "generated/filename.png")
    filename = generated_image.s3_key.split('/')[-1] if '/' in generated_image.s3_key else generated_image.s3_key

    return {
        "filename": filename,
        "s3_key": generated_image.s3_key,
        "generated_at_millis": generated_image.generated_at_millis
    }


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.get("/auth/login")
async def login(request: Request):
    """Initiate Google OAuth login"""
    redirect_uri = GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        # Exchange authorization code for access token
        token = await oauth.google.authorize_access_token(request)

        # Get user info from Google
        user_info = token.get('userinfo')
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")

        email = user_info.get('email')
        google_id = user_info.get('sub')

        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")

        # Get or create user in database
        user = get_or_create_user(db, email=email, google_id=google_id)

        # Create JWT token
        access_token = create_access_token(data={"sub": user.id})

        # Redirect to frontend with token
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        return RedirectResponse(url=f"{frontend_url}/?token={access_token}")

    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@app.get("/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user with selfie information"""
    # Ensure workout_days has default value if None
    workout_days = current_user.workout_days
    if workout_days is None:
        workout_days = {
            "monday": False,
            "tuesday": False,
            "wednesday": False,
            "thursday": False,
            "friday": False,
            "saturday": False,
            "sunday": False
        }

    return {
        "id": current_user.id,
        "email": current_user.email,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "has_selfie": current_user.selfie_filename is not None,
        "selfie_filename": current_user.selfie_filename,
        "selfie_embedding_filename": current_user.selfie_embedding_filename,
        "gender": current_user.gender,
        "workout_days": workout_days
    }


@app.get("/api/selfie/{filename}")
async def get_selfie_image(
    filename: str,
    current_user: User = Depends(get_current_user_from_query)
):
    """Serve authenticated user's selfie image"""
    # Verify the requested file belongs to the current user
    if current_user.selfie_filename != filename:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if file exists in storage
    if not uploads_storage.exists(filename):
        raise HTTPException(status_code=404, detail="Selfie not found")

    # Get file from storage (S3 or local)
    try:
        file_data = uploads_storage.get(filename)
        # Determine content type from filename extension
        ext = filename.split('.')[-1].lower()
        content_type = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp'
        }.get(ext, 'application/octet-stream')

        return Response(content=file_data, media_type=content_type)
    except Exception as e:
        logger.error(f"Error serving selfie: {e}")
        raise HTTPException(status_code=500, detail="Error serving selfie")


@app.post("/auth/logout")
async def logout():
    """Logout user (client-side token removal)"""
    return {"message": "Logged out successfully"}


class WorkoutDaysUpdate(BaseModel):
    """Request body for updating workout days"""
    workout_days: dict


@app.put("/api/workout-days")
async def update_workout_days(
    request: WorkoutDaysUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's workout days"""
    try:
        # Update workout days
        current_user.workout_days = request.workout_days
        db.commit()
        db.refresh(current_user)

        logger.info(f"Updated workout days for user {current_user.email}")

        return {
            "message": "Workout days updated successfully",
            "workout_days": current_user.workout_days
        }
    except Exception as e:
        logger.error(f"Failed to update workout days: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update workout days: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
