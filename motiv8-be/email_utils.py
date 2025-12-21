"""
Email utility functions for sending notifications
"""

import os
import smtplib
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


def send_motivation_email(to_email: str, generated_image_path: str) -> bool:
    """
    Send a daily motivation email with the generated image

    Args:
        to_email: Recipient email address
        generated_image_path: Path to the generated image file

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

        # Create HTML body with embedded image
        html_body = """
        <html>
          <head></head>
          <body style="font-family: Arial, sans-serif; text-align: center; padding: 20px;">
            <h1 style="color: #646cff;">Daily Motivation</h1>
            <p style="font-size: 24px; font-weight: bold; margin: 30px 0;">Get after it</p>

            <div style="margin: 30px 0;">
              <img src="cid:generated_image" style="max-width: 600px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);" alt="Your Motivational Image">
            </div>

            <footer style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #ccc; color: #666;">
              <p>Powered by <a href="https://motiv8.ai" style="color: #646cff; text-decoration: none;">motiv8.ai</a></p>
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
            logger.info(f"Motivation email sent successfully to {to_email}")
            return True

    except Exception as e:
        logger.error(f"Failed to send motivation email to {to_email}: {e}", exc_info=True)
        return False
