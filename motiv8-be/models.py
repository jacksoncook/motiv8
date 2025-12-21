"""
Database models
"""

from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
import uuid
from database import Base


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    google_id = Column(String, unique=True, index=True, nullable=True)  # Optional: store Google's user ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
