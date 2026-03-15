"""User management routes for creating users in the notification system.

This module defines the FastAPI routes for user operations.
It handles user creation requests and stores user data in DynamoDB.
"""

from fastapi import APIRouter, Request, HTTPException
from Dynamo import User as UserDB, Database
from pydantic import BaseModel, Field, EmailStr
import logging
import uuid

logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/user", tags=["User"])

class UserCreate(BaseModel):
    """Request model for user creation endpoint.

    Attributes:
        Name: Full name of the user, between 3 and 25 characters
        Email: Valid email address of the user
    """
    Name: str = Field(min_length=3, max_length=25)
    Email: EmailStr

@router.post("/create")
async def createUser(user: UserCreate, request: Request):
    """Create a new user in the DynamoDB Users table.

    Generates a new UUID for the user, then stores the user's
    Name and Email in DynamoDB under the 'email' channel.

    Args:
        user: UserCreate request body containing Name and Email
        request: FastAPI request object with app state (db connection)

    Returns:
        dict: Newly generated user_id
        Example: {"user_id": "123e4567-e89b-12d3-a456-426614174000"}

    Raises:
        HTTPException 500: If DynamoDB write operation fails

    Example:
        POST /api/v1/user/create
        {
            "Name": "John Doe",
            "Email": "john@example.com"
        }
    """
    try:
        userId = str(uuid.uuid4())
        db_user = UserDB(request.app.state.db)
        db_user.create_user(userId, user.Name, user.Email)
        return {"user_id": userId}
    except Exception as e:
        logging.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Error creating user")