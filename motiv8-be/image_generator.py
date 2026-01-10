"""
Image Generator using IP-Adapter-FaceID
Generates images with uploaded face applied to muscular body
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

import numpy as np
import torch
from diffusers import StableDiffusionPipeline, DDIMScheduler, AutoencoderKL
from PIL import Image

from ip_adapter.ip_adapter_faceid import IPAdapterFaceIDPlus

logger = logging.getLogger(__name__)


class ImageGenerator:
    """Generate images using IP-Adapter-FaceID with Stable Diffusion"""

    def __init__(self):
        """Initialize the image generator"""
        self.ip_model = None
        self._initialized = False

        # Correct device selection for EC2 (CUDA) + local (MPS) + fallback (CPU)
        if torch.cuda.is_available():
            self.device = "cuda"
        elif torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"

        # Keep dtype consistent across pipeline + IP-Adapter
        # (fp16 on GPU/MPS, fp32 on CPU)
        self.dtype = torch.float16 if self.device in ("cuda", "mps") else torch.float32

        logger.info(f"Using device: {self.device}, dtype: {self.dtype}")

    def initialize(self):
        """Lazy initialization of the IP-Adapter-FaceID pipeline"""
        if self._initialized:
            return

        try:
            logger.info("Initializing IP-Adapter-FaceID pipeline...")

            # Model paths
            base_model_path = "SG161222/Realistic_Vision_V4.0_noVAE"
            vae_model_path = "stabilityai/sd-vae-ft-mse"
            image_encoder_path = "laion/CLIP-ViT-H-14-laion2B-s32B-b79K"
            ip_ckpt = "models/ip-adapter-faceid-plus_sd15.bin"

            # Setup scheduler
            noise_scheduler = DDIMScheduler(
                num_train_timesteps=1000,
                beta_start=0.00085,
                beta_end=0.012,
                beta_schedule="scaled_linear",
                clip_sample=False,
                set_alpha_to_one=False,
                steps_offset=1,
            )

            # Load VAE in the same dtype/device
            logger.info("Loading VAE...")
            vae = AutoencoderKL.from_pretrained(vae_model_path).to(self.device, dtype=self.dtype)

            # Create base pipeline in the same dtype/device
            logger.info("Loading Stable Diffusion pipeline...")
            pipe = StableDiffusionPipeline.from_pretrained(
                base_model_path,
                torch_dtype=self.dtype,
                scheduler=noise_scheduler,
                vae=vae,
                feature_extractor=None,
                safety_checker=None,
            ).to(self.device)

            # Initialize IP-Adapter-FaceID with matching dtype
            logger.info("Loading IP-Adapter-FaceID...")
            self.ip_model = IPAdapterFaceIDPlus(
                pipe,
                image_encoder_path,
                ip_ckpt,
                self.device,
                torch_dtype=self.dtype,
            )

            self._initialized = True
            logger.info("IP-Adapter-FaceID pipeline initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}", exc_info=True)
            raise

    def generate_image(
        self,
        embedding_path: str,
        image_path: Optional[str] = None,
        prompt: str = "professional full body photo of a person with extremely muscular bodybuilder physique standing in front of one of the seven wonders of the world, highly detailed, 8k, photorealistic",
        negative_prompt: str = "blurry, low quality, distorted, deformed, ugly, bad anatomy, monochrome, lowres, bad anatomy, worst quality, low quality",
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
        scale: float = 0.8,  # IP-Adapter scale (0-1, controls how much face is preserved)
    ) -> Dict[str, Any]:
        """
        Generate an image using the face embedding with IP-Adapter-FaceID

        Args:
            embedding_path: Path to the .npy embedding file
            image_path: Path to the face image (required by Plus variant for CLIP encoding)
            prompt: Text prompt for generation
            negative_prompt: Negative prompt
            num_inference_steps: Number of denoising steps
            guidance_scale: Classifier-free guidance scale
            seed: Random seed for reproducibility
            scale: IP-Adapter scale (0-1), higher = more face preservation

        Returns:
            Dictionary containing:
                - success: boolean
                - image: PIL Image if successful
                - error: error message if failed
        """
        if not self._initialized:
            self.initialize()

        try:
            # Load the embedding and normalize dtype
            embedding = np.load(embedding_path).astype(np.float32)
            logger.info(f"Loaded embedding from {embedding_path}, shape: {embedding.shape}, dtype: {embedding.dtype}")

            # Convert to torch tensor and add batch dimension; move to device + dtype
            faceid_embeds = (
                torch.from_numpy(embedding)
                .unsqueeze(0)
                .to(device=self.device, dtype=self.dtype)
            )
            logger.info(
                f"Face embedding tensor shape: {faceid_embeds.shape}, dtype: {faceid_embeds.dtype}, device: {faceid_embeds.device}"
            )

            # Load the original face image for CLIP encoding (required by Plus variant)
            face_image = None
            if image_path and Path(image_path).exists():
                face_image = Image.open(image_path).convert("RGB")
                logger.info(f"Loaded face image from {image_path}")
            else:
                logger.warning("No face image provided - IPAdapterFaceIDPlus expects a face image; generation may fail.")

            logger.info(f"Generating image with prompt: {prompt}")
            logger.info(f"IP-Adapter scale: {scale}")

            # Generate image using IP-Adapter-FaceID
            images = self.ip_model.generate(
                prompt=prompt,
                negative_prompt=negative_prompt,
                face_image=face_image,          # Original face image for CLIP
                faceid_embeds=faceid_embeds,    # InsightFace embedding
                shortcut=True,                  # Use shortcut mode
                s_scale=0.2,                    # Structure scale
                num_samples=1,
                width=512,
                height=768,                     # Portrait aspect ratio
                num_inference_steps=num_inference_steps,
                guidance_scale=5.5,
                seed=seed,                      # Pass seed directly (None = random)
                scale=0.75,                     # IP-Adapter influence
            )

            logger.info("Image generated successfully")

            # ip_model.generate returns a list of PIL images
            out_image = images[0] if isinstance(images, list) else images
            return {"success": True, "image": out_image}

        except Exception as e:
            logger.error(f"Error generating image: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

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
            logger.error(f"Failed to save image: {e}", exc_info=True)
            return False


# Global instance
_image_generator: Optional[ImageGenerator] = None


def get_image_generator() -> ImageGenerator:
    """Get or create the global image generator instance"""
    global _image_generator
    if _image_generator is None:
        _image_generator = ImageGenerator()
    return _image_generator
