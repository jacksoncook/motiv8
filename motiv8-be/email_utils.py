"""
Email utility functions for sending notifications
"""

import os
import smtplib
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Email configuration from environment variables
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)

# AWS SES configuration for production
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SES_FROM_EMAIL = "no-reply@motiv8me.io"

# Initialize SES client (will only be used in production)
ses = boto3.client("ses", region_name=AWS_REGION)


def send_motivation_email_ses(to_email: str, generated_image_path: str, anti_motivation_mode: bool = False) -> bool:
    """
    Send a daily motivation email with the generated image using Amazon SES

    Args:
        to_email: Recipient email address
        generated_image_path: Path to the generated image file
        anti_motivation_mode: If True, use anti-motivation message

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Create message
        msg = MIMEMultipart('related')
        msg['Subject'] = 'Daily Motivation'
        msg['From'] = SES_FROM_EMAIL
        msg['To'] = to_email
        msg['Reply-To'] = 'support@motiv8me.io'

        # Choose message based on anti-motivation mode
        message_text = "This could be you" if anti_motivation_mode else "Get after it"

        # Create plain text body
        text_body = f"Daily motivation: {message_text}\nhttps://motiv8me.io"

        # Create HTML body with embedded image
        html_body = f"""
        <html>
          <head></head>
          <body style="font-family: Arial, sans-serif; text-align: center; padding: 20px;">
            <p style="font-size: 24px; font-weight: bold; margin: 30px 0;">{message_text}</p>

            <div style="margin: 30px 0;">
              <img src="cid:generated_image" style="max-width: 600px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);" alt="Your Motivational Image">
            </div>

            <footer style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #ccc; color: #666;">
              <p>Unsubscribe at <a href="https://motiv8me.io" style="color: #646cff; text-decoration: none;">motiv8me.io</a></p>
            </footer>
          </body>
        </html>
        """

        # Attach both plain text and HTML body
        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)

        text_part = MIMEText(text_body, 'plain')
        msg_alternative.attach(text_part)

        html_part = MIMEText(html_body, 'html')
        msg_alternative.attach(html_part)

        # Attach the generated image
        image_path = Path(generated_image_path)
        if image_path.exists():
            with open(image_path, 'rb') as img_file:
                img = MIMEImage(img_file.read())
                img.add_header('Content-ID', '<generated_image>')
                img.add_header('Content-Disposition', 'inline', filename=image_path.name)
                msg.attach(img)
        else:
            logger.error(f"Generated image not found: {generated_image_path}")
            return False

        # Send email via SES
        raw_bytes = msg.as_bytes()
        ses.send_raw_email(
            Source=SES_FROM_EMAIL,
            Destinations=[to_email],
            RawMessage={"Data": raw_bytes},
        )
        logger.info(f"Motivation email sent successfully via SES to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send motivation email via SES to {to_email}: {e}", exc_info=True)
        return False


def send_motivation_email_smtp(to_email: str, generated_image_path: str, anti_motivation_mode: bool = False) -> bool:
    """
    Send a daily motivation email with the generated image using SMTP (development only)

    Args:
        to_email: Recipient email address
        generated_image_path: Path to the generated image file
        anti_motivation_mode: If True, use anti-motivation message

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Check if SMTP is configured
        if not SMTP_USER or not SMTP_PASSWORD:
            logger.warning("SMTP credentials not configured. Skipping email send.")
            return False

        # Create message
        msg = MIMEMultipart('related')
        msg['Subject'] = 'Daily Motivation'
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email

        # Choose message based on anti-motivation mode
        message_text = "This could be you" if anti_motivation_mode else "Get after it"

        # Create HTML body with embedded image
        html_body = f"""
        <html>
          <head></head>
          <body style="font-family: Arial, sans-serif; text-align: center; padding: 20px;">
            <p style="font-size: 24px; font-weight: bold; margin: 30px 0;">{message_text}</p>

            <div style="margin: 30px 0;">
              <img src="cid:generated_image" style="max-width: 600px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);" alt="Your Motivational Image">
            </div>

            <footer style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #ccc; color: #666;">
              <p>Unsubscribe at <a href="https://motiv8me.io" style="color: #646cff; text-decoration: none;">motiv8me.io</a></p>
            </footer>
          </body>
        </html>
        """

        # Attach HTML body
        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)

        html_part = MIMEText(html_body, 'html')
        msg_alternative.attach(html_part)

        # Attach the generated image
        image_path = Path(generated_image_path)
        if image_path.exists():
            with open(image_path, 'rb') as img_file:
                img = MIMEImage(img_file.read())
                img.add_header('Content-ID', '<generated_image>')
                img.add_header('Content-Disposition', 'inline', filename=image_path.name)
                msg.attach(img)
        else:
            logger.error(f"Generated image not found: {generated_image_path}")
            return False

        # Send email
        logger.info(f"Connecting to SMTP server: {SMTP_HOST}:{SMTP_PORT}")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
            logger.info(f"Motivation email sent successfully via SMTP to {to_email}")
            return True

    except Exception as e:
        logger.error(f"Failed to send motivation email via SMTP to {to_email}: {e}", exc_info=True)
        return False


def send_motivation_email(to_email: str, generated_image_path: str, anti_motivation_mode: bool = False) -> bool:
    """
    Send a daily motivation email with the generated image.
    Routes to SES in production, SMTP in development.

    Args:
        to_email: Recipient email address
        generated_image_path: Path to the generated image file
        anti_motivation_mode: If True, use anti-motivation message

    Returns:
        True if email sent successfully, False otherwise
    """
    environment = os.getenv("ENVIRONMENT", "development")

    # TEMPORARY: Force SMTP usage even in production
    logger.info("Using SMTP for email delivery (temporarily forced)")
    return send_motivation_email_smtp(to_email, generated_image_path, anti_motivation_mode)

    # if environment == "production":
    #     logger.info("Using Amazon SES for email delivery (production environment)")
    #     return send_motivation_email_ses(to_email, generated_image_path, anti_motivation_mode)
    # else:
    #     logger.info("Using SMTP for email delivery (development environment)")
    #     return send_motivation_email_smtp(to_email, generated_image_path, anti_motivation_mode)
