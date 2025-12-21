from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn
import os
import shutil
from pathlib import Path
from datetime import datetime
import logging
from faceid_extractor import get_face_extractor
from image_generator import get_image_generator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Motiv8 API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads, embeddings, and generated directories
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

EMBEDDINGS_DIR = Path("embeddings")
EMBEDDINGS_DIR.mkdir(exist_ok=True)

GENERATED_DIR = Path("generated")
GENERATED_DIR.mkdir(exist_ok=True)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "motiv8-api"}


@app.get("/api/hello")
async def hello():
    """Returns a hello message"""
    return {"message": "hello"}


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    """Upload an image and extract FaceID embedding"""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{timestamp}_{file.filename}"
        file_path = UPLOAD_DIR / unique_filename

        # Save image file temporarily
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"Image saved: {file_path}")

        # Extract face embedding
        extractor = get_face_extractor()
        result = extractor.extract_embedding(str(file_path))

        if not result["success"]:
            # Clean up uploaded image if face extraction failed
            os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail=f"Face extraction failed: {result.get('error', 'Unknown error')}"
            )

        # Save embedding
        embedding_filename = f"{timestamp}_{os.path.splitext(file.filename)[0]}.npy"
        embedding_path = EMBEDDINGS_DIR / embedding_filename
        extractor.save_embedding(result["embedding"], str(embedding_path))

        logger.info(f"Embedding saved: {embedding_path}")

        # Optionally delete the original image to save space
        # os.remove(file_path)

        return JSONResponse(
            status_code=200,
            content={
                "message": "Face embedding extracted and saved successfully",
                "filename": unique_filename,
                "embedding_filename": embedding_filename,
                "original_filename": file.filename,
                "content_type": file.content_type,
                "size_bytes": os.path.getsize(file_path),
                "num_faces": result["num_faces"],
                "bbox": result["bbox"],
                "embedding_shape": list(result["embedding_shape"]),
                "embedding_dtype": result["embedding_dtype"]
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
    image_filename: str | None = None  # Original uploaded image filename
    prompt: str = "professional portrait photo of a person with extremely muscular bodybuilder physique, highly detailed, 8k, photorealistic"
    negative_prompt: str = "blurry, low quality, distorted, deformed, ugly, bad anatomy, monochrome, lowres, bad anatomy, worst quality, low quality"
    num_inference_steps: int = 30
    guidance_scale: float = 7.5
    seed: int | None = None
    scale: float = 0.8  # IP-Adapter scale (0-1), controls how much face is preserved


@app.post("/api/generate")
async def generate_image(request: GenerateRequest):
    """Generate an image using a face embedding"""
    try:
        # Check if embedding file exists
        embedding_path = EMBEDDINGS_DIR / request.embedding_filename
        if not embedding_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Embedding file not found: {request.embedding_filename}"
            )

        logger.info(f"Generating image using embedding: {request.embedding_filename}")

        # Get the original image path if provided
        image_path = None
        if request.image_filename:
            image_path = UPLOAD_DIR / request.image_filename
            if not image_path.exists():
                logger.warning(f"Image file not found: {request.image_filename}")
                image_path = None

        # Generate image
        generator = get_image_generator()
        result = generator.generate_image(
            embedding_path=str(embedding_path),
            image_path=str(image_path) if image_path else None,
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

        # Save generated image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(request.embedding_filename)[0]
        generated_filename = f"{timestamp}_{base_name}_generated.png"
        generated_path = GENERATED_DIR / generated_filename

        generator.save_image(result["image"], str(generated_path))

        logger.info(f"Image generated and saved: {generated_path}")

        return JSONResponse(
            status_code=200,
            content={
                "message": "Image generated successfully",
                "generated_filename": generated_filename,
                "embedding_filename": request.embedding_filename,
                "prompt": request.prompt
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
    file_path = GENERATED_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
