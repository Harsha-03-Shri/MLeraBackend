"""Authentication and authorization utilities.

This module provides JWT token generation and validation for securing API endpoints.
It handles user authentication through Bearer token validation.
"""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
import jwt
import os
import uuid
from datetime import datetime, timedelta


security = HTTPBearer()
logging.basicConfig(level=logging.INFO, format="%(filename)s - %(levelname)s - %(message)s")

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"

def getCurrentUser(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract and validate user ID from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        uuid.UUID: Validated user ID
        
    Raises:
        HTTPException: If token is invalid, expired, or missing user ID
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        userId = payload.get("userId")
        if userId is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return uuid.UUID(userId)

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")

    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def createAccessToken(userId: uuid.UUID):
    """Generate JWT access token for authenticated user.
    
    Args:
        userId: User's unique identifier
        
    Returns:
        str: Encoded JWT token valid for 1 hour
    """
    payload = {
        "userId": str(userId),
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token