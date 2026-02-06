"""
Database models
"""

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Date, BigInteger, Boolean, Enum
from sqlalchemy.sql import func
import uuid
import enum
from database import Base


class ModeEnum(str, enum.Enum):
    """Valid mode options for user motivation"""
    SHAME = "shame"
    TONED = "toned"
    RIPPED = "ripped"
    FURRY = "furry"


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    google_id = Column(String, unique=True, index=True, nullable=True)  # Optional: store Google's user ID

    # Selfie fields - one selfie per user
    selfie_filename = Column(String, nullable=True)  # Original uploaded image filename
    selfie_embedding_filename = Column(String, nullable=True)  # Face embedding filename
    gender = Column(String, nullable=True)  # Detected gender: "male" or "female"

    # Workout days - JSON object with days of week
    # Format: {"monday": true, "tuesday": false, ...}
    workout_days = Column(JSON, nullable=True, default=lambda: {
        "monday": False,
        "tuesday": False,
        "wednesday": False,
        "thursday": False,
        "friday": False,
        "saturday": False,
        "sunday": False
    })

    # Anti-motivation mode - if True, generate demotivational images
    anti_motivation_mode = Column(Boolean, nullable=False, default=False)

    # Mode - determines the type of image generation
    # Valid values are defined in ModeEnum: 'shame', 'toned', 'ripped'
    # Using String instead of Enum for SQLite compatibility
    mode = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class GeneratedImage(Base):
    """Generated image tracking model"""
    __tablename__ = "generated_images"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    s3_key = Column(String, nullable=False)  # S3 key (e.g., "generated_images/filename.png")
    generation_date = Column(Date, nullable=False, index=True)  # Date only (YYYY-MM-DD)
    generated_at_millis = Column(BigInteger, nullable=False)  # Epoch time in milliseconds
    mode = Column(String, nullable=True)  # Mode used for generation: 'shame', 'toned', 'ripped', 'furry'

    def __repr__(self):
        return f"<GeneratedImage(id={self.id}, user_id={self.user_id}, generation_date={self.generation_date}, mode={self.mode})>"
