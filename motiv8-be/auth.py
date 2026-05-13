"""
Authentication utilities for OAuth and JWT
"""

from datetime import datetime, timedelta
from typing import Optional
import time
from jose import JWTError, jwt
from jose import jwk as jose_jwk
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models import User
import os
import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")  # Change this!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")

# Apple OAuth Configuration
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID")
APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID")
APPLE_KEY_ID = os.getenv("APPLE_KEY_ID")
APPLE_PRIVATE_KEY = os.getenv("APPLE_PRIVATE_KEY", "").replace("\\n", "\n")
APPLE_REDIRECT_URI = os.getenv("APPLE_REDIRECT_URI", "http://localhost:8000/auth/apple/callback")

# Security scheme
security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_user_from_query(
    token: str = Query(..., description="JWT authentication token"),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from query parameter token (for image URLs)"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
        )

    payload = verify_token(token)

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def get_or_create_user(
    db: Session,
    email: Optional[str] = None,
    google_id: Optional[str] = None,
    apple_id: Optional[str] = None,
    name: Optional[str] = None,
) -> User:
    """Get existing user by provider ID or email, or create a new one"""
    user = None

    # Try provider IDs first (most specific)
    if google_id:
        user = db.query(User).filter(User.google_id == google_id).first()
    if not user and apple_id:
        user = db.query(User).filter(User.apple_id == apple_id).first()

    # Fall back to email lookup
    if not user and email:
        user = db.query(User).filter(User.email == email).first()

    if not user:
        if not email:
            raise HTTPException(status_code=400, detail="Email required to create account")
        user = User(email=email, google_id=google_id, apple_id=apple_id, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        updated = False
        if google_id and not user.google_id:
            user.google_id = google_id
            updated = True
        if apple_id and not user.apple_id:
            user.apple_id = apple_id
            updated = True
        if name and not user.name:
            user.name = name
            updated = True
        if updated:
            db.commit()
            db.refresh(user)

    return user


# ---------------------------------------------------------------------------
# Apple Sign In helpers
# ---------------------------------------------------------------------------

def generate_apple_client_secret() -> str:
    """Generate a short-lived ES256 JWT used as Apple's client secret"""
    now = int(time.time())
    payload = {
        "iss": APPLE_TEAM_ID,
        "iat": now,
        "exp": now + 3600,  # 1 hour; max allowed is 6 months
        "aud": "https://appleid.apple.com",
        "sub": APPLE_CLIENT_ID,
    }
    return jwt.encode(payload, APPLE_PRIVATE_KEY, algorithm="ES256", headers={"kid": APPLE_KEY_ID})


async def get_apple_public_keys() -> dict:
    """Fetch Apple's current JWKS"""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://appleid.apple.com/auth/keys")
        response.raise_for_status()
        return response.json()


def verify_apple_token(token: str, jwks: dict, audience: str) -> dict:
    """Verify an Apple-signed JWT (id_token or notification payload) using Apple's JWKS"""
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")

    key_data = next((k for k in jwks["keys"] if k["kid"] == kid), None)
    if not key_data:
        raise HTTPException(status_code=400, detail="Apple: matching public key not found")

    public_key = jose_jwk.construct(key_data)
    return jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=audience,
        options={"verify_at_hash": False},
    )
