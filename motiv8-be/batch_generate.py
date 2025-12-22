"""
Daily batch job to generate motivational images for users
Run this script once per day to generate images for users with today as a workout day
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import logging
from dotenv import load_dotenv

from models import User
from database import SessionLocal  # Use the database module for DB connection
from image_generator import get_image_generator
from email_utils import send_motivation_email
from storage import uploads_storage, embeddings_storage, generated_storage, USE_S3

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Local temp directories for processing
UPLOAD_DIR = Path("uploads")
EMBEDDINGS_DIR = Path("embeddings")
GENERATED_DIR = Path("generated")

# Ensure temp directories exist
UPLOAD_DIR.mkdir(exist_ok=True)
EMBEDDINGS_DIR.mkdir(exist_ok=True)
GENERATED_DIR.mkdir(exist_ok=True)

# Log storage mode
if USE_S3:
    logger.info("Using S3 storage with local temp processing")
else:
    logger.info("Using local filesystem storage")


def get_current_day():
    """Get current day of week in lowercase (monday, tuesday, etc.)"""
    return datetime.now().strftime("%A").lower()


def generate_for_user(user: User, generator):
    """Generate motivational image for a single user"""
    temp_embedding_path = None
    temp_image_path = None
    temp_generated_path = None

    try:
        logger.info(f"Generating image for user: {user.email}")

        # Check if user has selfie
        if not user.selfie_filename or not user.selfie_embedding_filename:
            logger.warning(f"User {user.email} has no selfie, skipping")
            return False

        # Check if files exist in storage
        if not embeddings_storage.exists(user.selfie_embedding_filename):
            logger.error(f"Embedding not found for {user.email}: {user.selfie_embedding_filename}")
            return False

        # Download embedding to temp location
        temp_embedding_path = EMBEDDINGS_DIR / user.selfie_embedding_filename
        embeddings_storage.download_to_local(user.selfie_embedding_filename, str(temp_embedding_path))
        logger.info(f"Downloaded embedding to temp: {temp_embedding_path}")

        # Download image to temp location if it exists
        temp_image_path_obj = None
        if uploads_storage.exists(user.selfie_filename):
            temp_image_path_obj = UPLOAD_DIR / user.selfie_filename
            uploads_storage.download_to_local(user.selfie_filename, str(temp_image_path_obj))
            logger.info(f"Downloaded image to temp: {temp_image_path_obj}")
            temp_image_path = temp_image_path_obj
        else:
            logger.warning(f"Image not found for {user.email}: {user.selfie_filename}")

        # Generate image using local temp files
        result = generator.generate_image(
            embedding_path=str(temp_embedding_path),
            image_path=str(temp_image_path) if temp_image_path else None,
            prompt="professional portrait photo of a person with extremely muscular bodybuilder physique, highly detailed, 8k, photorealistic",
            negative_prompt="blurry, low quality, distorted, deformed, ugly, bad anatomy, monochrome, lowres, bad anatomy, worst quality, low quality",
            num_inference_steps=30,
            guidance_scale=7.5,
            seed=None,  # Random seed for variation
            scale=0.8
        )

        if not result["success"]:
            logger.error(f"Generation failed for {user.email}: {result.get('error')}")
            return False

        # Save generated image to temp location
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        generated_filename = f"{timestamp}_{user.id}_generated.png"
        temp_generated_path = GENERATED_DIR / generated_filename

        generator.save_image(result["image"], str(temp_generated_path))
        logger.info(f"Image saved to temp: {temp_generated_path}")

        # Upload generated image to storage
        generated_storage.save_from_file(generated_filename, str(temp_generated_path))
        logger.info(f"Image uploaded to storage: {generated_filename}")

        # Send email with local temp file
        email_sent = send_motivation_email(user.email, str(temp_generated_path))
        if email_sent:
            logger.info(f"Email sent successfully to {user.email}")
        else:
            logger.warning(f"Failed to send email to {user.email}")

        return True

    except Exception as e:
        logger.error(f"Error generating for user {user.email}: {e}", exc_info=True)
        return False
    finally:
        # Clean up temp files if using S3
        if USE_S3:
            try:
                if temp_embedding_path and temp_embedding_path.exists():
                    os.remove(temp_embedding_path)
                if temp_image_path and temp_image_path.exists():
                    os.remove(temp_image_path)
                if temp_generated_path and temp_generated_path.exists():
                    os.remove(temp_generated_path)
                logger.info("Cleaned up temporary files")
            except Exception as cleanup_error:
                logger.warning(f"Error cleaning up temp files: {cleanup_error}")


def main():
    """Main batch job function"""
    logger.info("=" * 80)
    logger.info("Starting daily motivation batch job")
    logger.info("=" * 80)

    # Get current day
    today = get_current_day()
    logger.info(f"Today is: {today}")

    # Create database session
    db = SessionLocal()

    try:
        # Query users who have today as a workout day and have a selfie
        users = db.query(User).filter(
            User.selfie_filename.isnot(None),
            User.selfie_embedding_filename.isnot(None)
        ).all()

        # Filter users who have today marked as workout day
        workout_users = [
            user for user in users
            if user.workout_days and user.workout_days.get(today, False)
        ]

        logger.info(f"Found {len(workout_users)} users with {today} as workout day")

        if not workout_users:
            logger.info("No users to process today. Exiting.")
            return

        # Initialize image generator
        logger.info("Initializing image generator...")
        generator = get_image_generator()

        # Generate images for each user
        success_count = 0
        failure_count = 0

        for i, user in enumerate(workout_users, 1):
            logger.info(f"Processing user {i}/{len(workout_users)}: {user.email}")

            if generate_for_user(user, generator):
                success_count += 1
            else:
                failure_count += 1

        # Summary
        logger.info("=" * 80)
        logger.info("Batch job completed")
        logger.info(f"Total users processed: {len(workout_users)}")
        logger.info(f"Successful: {success_count}")
        logger.info(f"Failed: {failure_count}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Batch job failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
