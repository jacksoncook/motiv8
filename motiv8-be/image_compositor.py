"""
Image Compositor - Utilities for background removal and compositing
"""

import logging
from PIL import Image, ImageDraw, ImageFilter
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy import for rembg - only loaded when needed
_rembg_loaded = False
_remove_func = None
_rembg_session = None


def _ensure_rembg_loaded():
    """Lazy load rembg only when needed (for local generation)"""
    global _rembg_loaded, _remove_func, _rembg_session
    if not _rembg_loaded:
        try:
            from rembg import remove, new_session
            _rembg_session = new_session("isnet-general-use")
            _remove_func = lambda img: remove(img, session=_rembg_session)
            _rembg_loaded = True
            logger.info("rembg loaded successfully (isnet-general-use)")
        except ImportError as e:
            logger.error(f"Failed to import rembg: {e}")
            raise ImportError(
                "rembg is required for background removal. Install with: pip install rembg"
            ) from e


def create_person_mask(width: int, height: int) -> Image.Image:
    """
    Create a centered ellipse mask representing where the person should be inpainted.
    White = region to inpaint, black = preserve background.

    The ellipse covers ~90% of the height and ~70% of the width, centered
    slightly above vertical midpoint to account for head room.

    Args:
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        Grayscale PIL Image mask
    """
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)

    margin_x = int(width * 0.05)
    margin_top = int(height * 0.01)
    margin_bottom = int(height * 0.01)

    draw.ellipse(
        [margin_x, margin_top, width - margin_x, height - margin_bottom],
        fill=255,
    )

    return mask


def composite_person_feathered(
    person_image: Image.Image,
    background_image: Image.Image,
    feather_radius: int = 8,
    alpha_threshold: int = 15,
) -> Image.Image:
    """
    Composite a person onto a background using rembg for accurate subject
    extraction. The alpha mask is binarized first (eliminating semi-transparent
    interior pixels), then GaussianBlur is applied — which on a binary mask
    naturally only softens edge pixels while keeping the interior fully opaque.

    Args:
        person_image: Generated person image (RGB)
        background_image: Background scene image (RGB)
        feather_radius: Gaussian blur radius applied to alpha edges
        alpha_threshold: Pixels above this value become fully opaque (0–255)

    Returns:
        Composited RGB image
    """
    _ensure_rembg_loaded()

    person = person_image.convert("RGB")
    bg = background_image.convert("RGB")

    if person.size != bg.size:
        bg = bg.resize(person.size, Image.LANCZOS)

    # Remove background to get person silhouette
    person_rgba = _remove_func(person.convert("RGBA"))
    if isinstance(person_rgba, bytes):
        from io import BytesIO
        person_rgba = Image.open(BytesIO(person_rgba))
    person_rgba = person_rgba.convert("RGBA")

    r, g, b, alpha = person_rgba.split()

    # Binarize: eliminate semi-transparent interior pixels caused by rembg uncertainty
    alpha = alpha.point(lambda p: 255 if p > alpha_threshold else 0)

    # Feather edges: blurring a binary mask only softens the boundary pixels;
    # interior pixels (surrounded by 255s) remain nearly fully opaque
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius=feather_radius))

    person_rgba = Image.merge("RGBA", (r, g, b, alpha))

    # Composite onto background
    result = Image.alpha_composite(bg.convert("RGBA"), person_rgba)
    return result.convert("RGB")


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
