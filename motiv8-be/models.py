"""
Database models
"""

from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
import uuid
from database import Base


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    google_id = Column(String, unique=True, index=True, nullable=True)  # Optional: store Google's user ID

    # Selfie fields - one selfie per user
    selfie_filename = Column(String, nullable=True)  # Original uploaded image filename
    selfie_embedding_filename = Column(String, nullable=True)  # Face embedding filename

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

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
