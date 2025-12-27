"""
FaceID Embedding Extractor using InsightFace
Extracts face embeddings from images for IP-Adapter-FaceID
"""

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class FaceIDExtractor:
    """Extract face embeddings from images using InsightFace buffalo_l model"""

    def __init__(self):
        """Initialize the face analysis model"""
        self.app = None
        self._initialized = False

    def initialize(self):
        """Lazy initialization of the face analysis model"""
        if self._initialized:
            return

        try:
            logger.info("Initializing FaceAnalysis model (buffalo_l)...")
            self.app = FaceAnalysis(
                name="buffalo_l",
                providers=['CPUExecutionProvider']  # Use CPU for compatibility
            )
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            self._initialized = True
            logger.info("FaceAnalysis model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize FaceAnalysis model: {e}")
            raise

    def extract_embedding(self, image_path: str) -> Dict[str, Any]:
        """
        Extract face embedding from an image

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary containing:
                - embedding: numpy array of face embedding (512-dim)
                - num_faces: number of faces detected
                - bbox: bounding box of the detected face
                - success: boolean indicating if extraction was successful
                - error: error message if extraction failed
        """
        if not self._initialized:
            self.initialize()

        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                return {
                    "success": False,
                    "error": "Failed to read image file",
                    "num_faces": 0
                }

            # Detect faces
            faces = self.app.get(image)

            if len(faces) == 0:
                return {
                    "success": False,
                    "error": "No face detected in image",
                    "num_faces": 0
                }

            if len(faces) > 1:
                logger.warning(f"Multiple faces detected ({len(faces)}), using the first one")

            # Extract embedding from first face
            face = faces[0]
            embedding = face.normed_embedding  # 512-dimensional embedding
            bbox = face.bbox.tolist()  # [x1, y1, x2, y2]
            gender = "male" if face.gender == 1 else "female"  # insightface returns 0=female, 1=male

            return {
                "success": True,
                "embedding": embedding,
                "num_faces": len(faces),
                "bbox": bbox,
                "gender": gender,
                "embedding_shape": embedding.shape,
                "embedding_dtype": str(embedding.dtype)
            }

        except Exception as e:
            logger.error(f"Error extracting face embedding: {e}")
            return {
                "success": False,
                "error": str(e),
                "num_faces": 0
            }

    def save_embedding(self, embedding: np.ndarray, output_path: str) -> bool:
        """
        Save embedding to a file

        Args:
            embedding: numpy array of face embedding
            output_path: path to save the embedding (.npy file)

        Returns:
            True if successful, False otherwise
        """
        try:
            np.save(output_path, embedding)
            logger.info(f"Embedding saved to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save embedding: {e}")
            return False

    def load_embedding(self, embedding_path: str) -> Optional[np.ndarray]:
        """
        Load embedding from a file

        Args:
            embedding_path: path to the embedding file (.npy)

        Returns:
            numpy array of embedding or None if failed
        """
        try:
            embedding = np.load(embedding_path)
            return embedding
        except Exception as e:
            logger.error(f"Failed to load embedding: {e}")
            return None


# Global instance
_face_extractor: Optional[FaceIDExtractor] = None


def get_face_extractor() -> FaceIDExtractor:
    """Get or create the global face extractor instance"""
    global _face_extractor
    if _face_extractor is None:
        _face_extractor = FaceIDExtractor()
    return _face_extractor
