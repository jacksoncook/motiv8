"""
Background Generator - Generates background images separately
"""

import logging
from typing import Optional, Dict, Any
import torch
from diffusers import StableDiffusionPipeline, DDIMScheduler, AutoencoderKL
from PIL import Image

logger = logging.getLogger(__name__)


class BackgroundGenerator:
    """Generate background images using Stable Diffusion"""

    def __init__(self):
        """Initialize the background generator"""
        self.pipe = None
        self._initialized = False

        # Device selection
        if torch.cuda.is_available():
            self.device = "cuda"
        elif torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"

        self.dtype = torch.float16 if self.device in ("cuda", "mps") else torch.float32
        logger.info(f"BackgroundGenerator using device: {self.device}, dtype: {self.dtype}")

    def initialize(self):
        """Lazy initialization of the Stable Diffusion pipeline"""
        if self._initialized:
            return

        try:
            logger.info("Initializing background generation pipeline...")

            base_model_path = "SG161222/Realistic_Vision_V4.0_noVAE"
            vae_model_path = "stabilityai/sd-vae-ft-mse"

            noise_scheduler = DDIMScheduler(
                num_train_timesteps=1000,
                beta_start=0.00085,
                beta_end=0.012,
                beta_schedule="scaled_linear",
                clip_sample=False,
                set_alpha_to_one=False,
                steps_offset=1,
            )

            logger.info("Loading VAE for background generation...")
            vae = AutoencoderKL.from_pretrained(vae_model_path).to(self.device, dtype=self.dtype)

            logger.info("Loading Stable Diffusion pipeline for backgrounds...")
            self.pipe = StableDiffusionPipeline.from_pretrained(
                base_model_path,
                torch_dtype=self.dtype,
                scheduler=noise_scheduler,
                vae=vae,
                feature_extractor=None,
                safety_checker=None,
            ).to(self.device)

            self._initialized = True
            logger.info("Background generation pipeline initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize background pipeline: {e}", exc_info=True)
            raise

    def generate_background(
        self,
        prompt: str,
        negative_prompt: str = "blurry, low quality, distorted, people, person, human, face, body",
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
        width: int = 512,
        height: int = 768,
    ) -> Dict[str, Any]:
        """
        Generate a background image without any people

        Args:
            prompt: Background description prompt
            negative_prompt: Things to avoid in the background
            num_inference_steps: Number of denoising steps
            guidance_scale: Classifier-free guidance scale
            seed: Random seed for reproducibility
            width: Image width
            height: Image height

        Returns:
            Dictionary containing:
                - success: boolean
                - image: PIL Image if successful
                - error: error message if failed
        """
        if not self._initialized:
            self.initialize()

        try:
            logger.info(f"Generating background with prompt: {prompt}")

            # Set seed if provided
            generator = None
            if seed is not None:
                generator = torch.Generator(device=self.device).manual_seed(seed)

            # Generate background
            result = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator,
                width=width,
                height=height,
            )

            image = result.images[0]
            logger.info("Background generated successfully")

            return {"success": True, "image": image}

        except Exception as e:
            logger.error(f"Error generating background: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


# Global instance
_background_generator: Optional[BackgroundGenerator] = None


def get_background_generator() -> BackgroundGenerator:
    """Get or create the global background generator instance"""
    global _background_generator
    if _background_generator is None:
        _background_generator = BackgroundGenerator()
    return _background_generator
