"""User management routes for creating users in the notification system.

This module defines the FastAPI routes for user operations.
It handles user creation requests and stores user data in DynamoDB.
"""

from fastapi import APIRouter, Request, HTTPException
from Dynamo import User as UserDB, Database
from pydantic import BaseModel, Field, EmailStr
import logging
import uuid

logging.basicConfig(level=logging.INFO, format="%(filename)s - %(levelname)s - %(message)s")

router = APIRouter(prefix="/user", tags=["User"])

class UserCreate(BaseModel):
    """Request model for user creation endpoint.

    Attributes:
        userId: User ID string
        name: Full name of the user, between 3 and 25 characters
        email: Valid email address of the user
    """
    userId: str
    name: str = Field(min_length=3, max_length=25)
    email: EmailStr

@router.post("/create")
async def createUser(user: UserCreate, request: Request):
    """Create a new user in the DynamoDB Users table.

    Uses the provided userId from the main API instead of generating a new one.

    Args:
        user: UserCreate request body containing userId, name and email
        request: FastAPI request object with app state (db connection)

    Returns:
        dict: Success confirmation with user_id
        Example: {"user_id": "123e4567-e89b-12d3-a456-426614174000"}

    Raises:
        HTTPException 500: If DynamoDB write operation fails

    Example:
        POST /api/v1/user/create
        {
            "userId": "123e4567-e89b-12d3-a456-426614174000",
            "name": "John Doe",
            "email": "john@example.com"
        }
    """
    try:
        db_user = UserDB(request.app.state.db)
        db_user.create_user(user.userId, user.name, user.email)
        return {"user_id": user.userId}
    except Exception as e:
        logging.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Error creating user")