from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import shutil
from pathlib import Path
from datetime import datetime
import logging
from faceid_extractor import get_face_extractor

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

# Create uploads and embeddings directories
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

EMBEDDINGS_DIR = Path("embeddings")
EMBEDDINGS_DIR.mkdir(exist_ok=True)


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


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
