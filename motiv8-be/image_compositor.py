"""
Image Compositor - Utilities for background removal and compositing
"""

import logging
from PIL import Image
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy import for rembg - only loaded when needed
_rembg_loaded = False
_remove_func = None


def _ensure_rembg_loaded():
    """Lazy load rembg only when needed (for local generation)"""
    global _rembg_loaded, _remove_func
    if not _rembg_loaded:
        try:
            from rembg import remove
            _remove_func = remove
            _rembg_loaded = True
            logger.info("rembg loaded successfully")
        except ImportError as e:
            logger.error(f"Failed to import rembg: {e}")
            raise ImportError(
                "rembg is required for background removal. Install with: pip install rembg"
            ) from e


def remove_background(image: Image.Image) -> Image.Image:
    """
    Remove background from an image using rembg.
    Returns an RGBA image with transparent background.

    Args:
        image: Input PIL Image (RGB or RGBA)

    Returns:
        RGBA PIL Image with transparent background
    """
    _ensure_rembg_loaded()

    try:
        logger.info("Removing background from image...")

        # Ensure input is RGBA
        img = image.convert("RGBA")

        # Remove background
        output = _remove_func(img)

        # Handle different return types from rembg
        if isinstance(output, bytes):
            from io import BytesIO
            result = Image.open(BytesIO(output))
        else:
            result = output

        # Ensure output is RGBA
        result = result.convert("RGBA")
        logger.info("Background removed successfully")

        return result

    except Exception as e:
        logger.error(f"Error removing background: {e}", exc_info=True)
        raise


def alpha_composite(bg_rgb: Image.Image, fg_rgba: Image.Image) -> Image.Image:
    """
    Composite a foreground RGBA image onto a background RGB image.

    Args:
        bg_rgb: Background image in RGB format
        fg_rgba: Foreground image in RGBA format (with alpha channel)

    Returns:
        Composited RGB image
    """
    try:
        logger.info("Compositing foreground onto background...")

        # Ensure background is RGBA for compositing
        bg_rgba = bg_rgb.convert("RGBA")

        # Ensure foreground is RGBA
        fg_rgba = fg_rgba.convert("RGBA")

        # Resize foreground to match background if needed
        if fg_rgba.size != bg_rgba.size:
            logger.info(f"Resizing foreground from {fg_rgba.size} to {bg_rgba.size}")
            fg_rgba = fg_rgba.resize(bg_rgba.size, Image.LANCZOS)

        # Composite using alpha channel
        result = Image.alpha_composite(bg_rgba, fg_rgba)

        # Convert back to RGB
        result_rgb = result.convert("RGB")
        logger.info("Compositing completed successfully")

        return result_rgb

    except Exception as e:
        logger.error(f"Error compositing images: {e}", exc_info=True)
        raise


def composite_person_on_background(
    person_image: Image.Image,
    background_image: Image.Image,
    remove_bg: bool = True
) -> Image.Image:
    """
    High-level function to composite a person image onto a background.
    Optionally removes the background from the person image first.

    Args:
        person_image: Image of person (RGB or RGBA)
        background_image: Background image (RGB)
        remove_bg: Whether to remove background from person first (default: True)

    Returns:
        Final composited RGB image
    """
    try:
        # Remove background from person if requested
        if remove_bg:
            person_rgba = remove_background(person_image)
        else:
            # Assume person_image already has transparent background
            person_rgba = person_image.convert("RGBA")

        # Composite person onto background
        final_image = alpha_composite(background_image, person_rgba)

        return final_image

    except Exception as e:
        logger.error(f"Error in composite_person_on_background: {e}", exc_info=True)
        raise
