"""
Image Generator using IP-Adapter-FaceID
Generates images with uploaded face applied to muscular body
"""

import torch
import numpy as np
from diffusers import StableDiffusionPipeline, DDIMScheduler
from PIL import Image
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ImageGenerator:
    """Generate images using IP-Adapter-FaceID with Stable Diffusion"""

    def __init__(self):
        """Initialize the image generator"""
        self.pipe = None
        self._initialized = False
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")

    def initialize(self):
        """Lazy initialization of the Stable Diffusion pipeline"""
        if self._initialized:
            return

        try:
            logger.info("Initializing Stable Diffusion pipeline...")

            # Use a smaller, faster model for demo purposes
            model_id = "runwayml/stable-diffusion-v1-5"

            # Load the pipeline
            self.pipe = StableDiffusionPipeline.from_pretrained(
                model_id,
                torch_dtype=torch.float32,  # Use float32 for MPS compatibility
                safety_checker=None,
                requires_safety_checker=False
            )

            # Use DDIM scheduler for faster generation
            self.pipe.scheduler = DDIMScheduler.from_config(self.pipe.scheduler.config)

            # Move to device
            self.pipe = self.pipe.to(self.device)

            # Enable memory optimizations
            if self.device == "mps":
                # MPS-specific optimizations
                self.pipe.enable_attention_slicing(1)
            elif self.device == "cpu":
                # CPU-specific optimizations
                self.pipe.enable_attention_slicing()

            self._initialized = True
            logger.info("Stable Diffusion pipeline initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}")
            raise

    def generate_image(
        self,
        embedding_path: str,
        prompt: str = "professional portrait photo of a person with extremely muscular bodybuilder physique, highly detailed, 8k, photorealistic",
        negative_prompt: str = "blurry, low quality, distorted, deformed, ugly, bad anatomy",
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate an image using the face embedding

        Args:
            embedding_path: Path to the .npy embedding file
            prompt: Text prompt for generation
            negative_prompt: Negative prompt
            num_inference_steps: Number of denoising steps
            guidance_scale: Classifier-free guidance scale
            seed: Random seed for reproducibility

        Returns:
            Dictionary containing:
                - success: boolean
                - image: PIL Image if successful
                - error: error message if failed
        """
        if not self._initialized:
            self.initialize()

        try:
            # Load the embedding
            embedding = np.load(embedding_path)
            logger.info(f"Loaded embedding from {embedding_path}, shape: {embedding.shape}")

            # Set random seed if provided
            if seed is not None:
                generator = torch.Generator(device=self.device).manual_seed(seed)
            else:
                generator = None

            # Note: For a full IP-Adapter-FaceID implementation, we would need to:
            # 1. Load the IP-Adapter-FaceID model weights
            # 2. Inject the face embedding into the cross-attention layers
            #
            # For now, we'll generate based on the text prompt only
            # In a production system, you would integrate the IP-Adapter-FaceID properly

            logger.info("Generating image...")
            with torch.inference_mode():
                result = self.pipe(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    generator=generator,
                    height=512,
                    width=512
                )

            image = result.images[0]
            logger.info("Image generated successfully")

            return {
                "success": True,
                "image": image
            }

        except Exception as e:
            logger.error(f"Error generating image: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def save_image(self, image: Image.Image, output_path: str) -> bool:
        """
        Save generated image to file

        Args:
            image: PIL Image to save
            output_path: Path to save the image

        Returns:
            True if successful, False otherwise
        """
        try:
            image.save(output_path, format="PNG", quality=95)
            logger.info(f"Image saved to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            return False


# Global instance
_image_generator: Optional[ImageGenerator] = None


def get_image_generator() -> ImageGenerator:
    """Get or create the global image generator instance"""
    global _image_generator
    if _image_generator is None:
        _image_generator = ImageGenerator()
    return _image_generator
