"""
Daily batch job to generate motivational images for users
Run this script once per day to generate images for users with today as a workout day
"""

import os
import sys
from datetime import datetime, date
from pathlib import Path
import logging
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from models import User, GeneratedImage
from database import SessionLocal  # Use the database module for DB connection
from faceid_extractor import get_face_extractor
from image_generator import get_image_generator
from email_utils import send_motivation_email
from storage import uploads_storage, embeddings_storage, generated_storage, USE_S3



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


def get_prompts_for_user(user: User):
    """
    Get the appropriate prompt and negative prompt based on user settings.

    Args:
        user: User object with gender and anti_motivation_mode settings

    Returns:
        tuple: (prompt, negative_prompt)
    """
    # Seven Natural Wonders of the World
    # One for each day of the week (7 wonders for 7 days)
    wonders = [
        "Aurora Borealis (Northern Lights) with vibrant green and purple lights dancing across the arctic sky",
        "Grand Canyon with its layered red rock formations and vast desert landscape",
        "Great Barrier Reef with crystal clear turquoise waters and colorful coral visible below",
        "Mount Everest with snow-covered peaks piercing through clouds",
        "Victoria Falls with massive waterfalls and mist rising into the sky",
        "Paricutin Volcano with volcanic landscape and ash plumes in the distance",
        "Harbor of Rio de Janeiro with Sugarloaf Mountain and Christ the Redeemer visible in the background"
    ]

    # Select wonder based on day of week (0=Monday, 6=Sunday)
    day_of_week = datetime.now().weekday()
    wonder = wonders[day_of_week % len(wonders)]

    gender_term = "female" if user.gender == "female" else "male"

    if user.anti_motivation_mode:
        # Anti-motivation prompt: obese, hairy, and unhealthy
        if user.gender == "female":
            # In underwear for females
            prompt = f"full body photo of an obese, overweight, unhealthy, ill-looking {gender_term}, out of shape, slovenly appearance, in her underwear, at {wonder}, highly detailed, 8k, photorealistic"
        else:
            # In underwear for males
            prompt = f"full body photo of an obese, overweight, hairy, unhealthy, ill-looking {gender_term}, out of shape, slovenly appearance, in his underwear, at {wonder}, highly detailed, 8k, photorealistic"
        negative_prompt = "blurry, low quality, distorted, deformed, monochrome, lowres, worst quality, low quality, muscular, fit, healthy, athletic, nude, naked, nudity, exposed genitals"
    else:
        # Regular motivation prompt: muscular and fit
        if user.gender == "female":
            # Toned body in two piece for females
            prompt = f"professional full body photo of a {gender_term} with toned athletic physique in a two piece, at {wonder}, highly detailed, 8k, photorealistic"
        else:
            # Bodybuilder physique for males
            prompt = f"professional full body photo of a {gender_term} bodybuilder with extremely muscular physique, at {wonder}, highly detailed, 8k, photorealistic"
        negative_prompt = "blurry, low quality, distorted, deformed, ugly, bad anatomy, monochrome, lowres, bad anatomy, worst quality, low quality, nude, naked, nudity, exposed genitals"

    return prompt, negative_prompt


def extract_face_for_user(user: User, extractor, db):
    """
    Extract face embedding for a user if needed.

    Returns:
        "extracted" - new extraction was performed
        "exists" - embedding already exists with gender, skipped extraction
        False - extraction failed
    """
    try:
        logger.info(f"Extracting face for user: {user.email}")

        # Check if user has a selfie
        if not user.selfie_filename:
            logger.warning(f"User {user.email} has no selfie, skipping")
            return False

        # Check if embedding already exists AND gender is detected
        # Force re-extraction if gender is not set to capture gender information
        if user.selfie_embedding_filename and embeddings_storage.exists(user.selfie_embedding_filename) and user.gender:
            logger.info(f"Embedding already exists for {user.email} with gender detected, skipping extraction")
            return "exists"

        if not user.gender:
            logger.info(f"Re-extracting face for {user.email} to detect gender")

        # Check if image exists in storage
        if not uploads_storage.exists(user.selfie_filename):
            logger.error(f"Image not found for {user.email}: {user.selfie_filename}")
            return False

        # Download image to temp location
        temp_image_path = UPLOAD_DIR / user.selfie_filename
        uploads_storage.download_to_local(user.selfie_filename, str(temp_image_path))
        logger.info(f"Downloaded image to temp: {temp_image_path}")

        # Extract face embedding
        result = extractor.extract_embedding(str(temp_image_path))

        if not result["success"]:
            logger.error(f"Face extraction failed for {user.email}: {result.get('error')}")
            # Clean up temp file
            if USE_S3 and temp_image_path.exists():
                os.remove(temp_image_path)
            return False

        # Save embedding to temp location
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        embedding_filename = f"{timestamp}_{os.path.splitext(user.selfie_filename)[0]}.npy"
        temp_embedding_path = EMBEDDINGS_DIR / embedding_filename

        extractor.save_embedding(result["embedding"], str(temp_embedding_path))
        logger.info(f"Embedding saved to temp: {temp_embedding_path}")

        # Upload embedding to storage
        embeddings_storage.save_from_file(embedding_filename, str(temp_embedding_path))
        logger.info(f"Embedding uploaded to storage: {embedding_filename}")

        # Update user's embedding filename and gender in database
        user.selfie_embedding_filename = embedding_filename
        user.gender = result.get("gender", "male")  # Default to male if not detected
        db.commit()
        db.refresh(user)
        logger.info(f"Updated user {user.email} embedding filename and gender ({user.gender}) in database")

        # Clean up temp files if using S3
        if USE_S3:
            if temp_image_path.exists():
                os.remove(temp_image_path)
            if temp_embedding_path.exists():
                os.remove(temp_embedding_path)
            logger.info("Cleaned up temporary files")

        return "extracted"

    except Exception as e:
        logger.error(f"Error extracting face for user {user.email}: {e}", exc_info=True)
        return False


def generate_for_user(user: User, generator, db):
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

        # Get prompts based on user settings
        prompt, negative_prompt = get_prompts_for_user(user)

        # Generate image using local temp files
        result = generator.generate_image(
            embedding_path=str(temp_embedding_path),
            image_path=str(temp_image_path) if temp_image_path else None,
            prompt=prompt,
            negative_prompt=negative_prompt,
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
        s3_key = generated_storage.save_from_file(generated_filename, str(temp_generated_path))
        logger.info(f"Image uploaded to storage: {generated_filename}")

        # Record generated image in database
        generation_time_millis = int(time.time() * 1000)
        generated_image = GeneratedImage(
            user_id=user.id,
            s3_key=s3_key,
            generation_date=date.today(),
            generated_at_millis=generation_time_millis
        )
        db.add(generated_image)
        db.commit()
        logger.info(f"Generated image recorded in database: {generated_image.id}")

        # Send email with local temp file
        email_sent = send_motivation_email(user.email, str(temp_generated_path), user.anti_motivation_mode)
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
    print("=" * 80, flush=True)
    print("Starting daily motivation batch job", flush=True)
    print("=" * 80, flush=True)
    logger.info("=" * 80)
    logger.info("Starting daily motivation batch job")
    logger.info("=" * 80)

    # Check for email filter from environment
    email_filter = os.environ.get('BATCH_EMAIL_FILTER')
    if email_filter:
        print(f"EMAIL FILTER ACTIVE: {email_filter}", flush=True)
        logger.info(f"EMAIL FILTER ACTIVE: {email_filter}")
    else:
        print("No email filter - processing all eligible users", flush=True)
        logger.info("No email filter - processing all eligible users")

    # Get current day
    today = get_current_day()
    print(f"Today is: {today}", flush=True)
    logger.info(f"Today is: {today}")

    # Create database session
    db = SessionLocal()

    try:
        # Query users who have today as a workout day and have a selfie
        # Note: We now allow users without embeddings (will extract face first)
        query = db.query(User).filter(User.selfie_filename.isnot(None))

        # Apply email filter if provided
        if email_filter:
            query = query.filter(User.email == email_filter)

        users = query.all()

        # Filter users who have today marked as workout day (skip this if email filter is active)
        if email_filter:
            # When filtering by email, process that user regardless of workout day
            workout_users = users
            print(f"Found {len(workout_users)} user(s) matching email filter", flush=True)
            logger.info(f"Found {len(workout_users)} user(s) matching email filter")
        else:
            # Normal operation: only users with today as workout day
            workout_users = [
                user for user in users
                if user.workout_days and user.workout_days.get(today, False)
            ]
            print(f"Found {len(workout_users)} users with {today} as workout day", flush=True)
            logger.info(f"Found {len(workout_users)} users with {today} as workout day")

            # Filter out users who already have an image generated today
            # (only when not using email filter)
            today_date = date.today()
            users_with_images_today = set(
                db.query(GeneratedImage.user_id)
                .filter(GeneratedImage.generation_date == today_date)
                .distinct()
                .all()
            )
            users_with_images_today = {user_id[0] for user_id in users_with_images_today}

            original_count = len(workout_users)
            workout_users = [
                user for user in workout_users
                if user.id not in users_with_images_today
            ]
            skipped_count = original_count - len(workout_users)

            if skipped_count > 0:
                print(f"Skipped {skipped_count} user(s) who already have an image generated today", flush=True)
                logger.info(f"Skipped {skipped_count} user(s) who already have an image generated today")

            print(f"Processing {len(workout_users)} user(s) without images generated today", flush=True)
            logger.info(f"Processing {len(workout_users)} user(s) without images generated today")

        if not workout_users:
            print("No users to process today. Exiting.", flush=True)
            logger.info("No users to process today. Exiting.")
            return

        # Initialize face extractor and image generator
        print("Initializing face extractor...", flush=True)
        logger.info("Initializing face extractor...")
        extractor = get_face_extractor()
        print("Face extractor ready!", flush=True)

        print("Initializing image generator (this may take a minute)...", flush=True)
        logger.info("Initializing image generator...")
        generator = get_image_generator()
        print("Image generator ready!", flush=True)

        # Process each user: extract face if needed, then generate image
        extraction_count = 0
        success_count = 0
        failure_count = 0

        for i, user in enumerate(workout_users, 1):
            print(f"\n[{i}/{len(workout_users)}] Processing user: {user.email}", flush=True)
            logger.info(f"Processing user {i}/{len(workout_users)}: {user.email}")

            # Extract face if needed (function handles all conditional logic)
            print(f"  → Checking/extracting face embedding...", flush=True)
            result = extract_face_for_user(user, extractor, db)

            if result == False:
                print(f"  ✗ Face extraction failed, skipping", flush=True)
                logger.error(f"Face extraction failed for {user.email}, skipping image generation")
                failure_count += 1
                continue
            elif result == "extracted":
                extraction_count += 1
                print(f"  ✓ Face extraction successful", flush=True)
                logger.info(f"Face extraction successful for {user.email}")
            elif result == "exists":
                print(f"  ✓ Face embedding already exists", flush=True)

            # Generate motivational image
            print(f"  → Generating motivational image...", flush=True)
            if generate_for_user(user, generator, db):
                print(f"  ✓ Image generated and email sent!", flush=True)
                success_count += 1
            else:
                print(f"  ✗ Generation failed", flush=True)
                failure_count += 1

        # Summary
        print("\n" + "=" * 80, flush=True)
        print("BATCH JOB COMPLETED", flush=True)
        print("=" * 80, flush=True)
        print(f"Total users processed: {len(workout_users)}", flush=True)
        print(f"Face extractions performed: {extraction_count}", flush=True)
        print(f"Images generated successfully: {success_count}", flush=True)
        print(f"Failed: {failure_count}", flush=True)
        print("=" * 80, flush=True)
        logger.info("=" * 80)
        logger.info("Batch job completed")
        logger.info(f"Total users processed: {len(workout_users)}")
        logger.info(f"Face extractions performed: {extraction_count}")
        logger.info(f"Images generated successfully: {success_count}")
        logger.info(f"Failed: {failure_count}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Batch job failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    print("batch_generate.py script starting...", flush=True)
    main()
