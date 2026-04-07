"""User management API routes.

This module handles user registration, authentication, and profile management.
Provides endpoints for user signup, login, and profile retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException ,Response
import logging 
from pydantic import BaseModel, Field, SecretStr
import uuid
from utils.DBServiceClient import DBServiceClient
from utils.NotifyServiceClient import NotifyServiceClient
from utils.Auth import getCurrentUser, createAccessToken

logging.basicConfig(level=logging.INFO, format="%(filename)s - %(levelname)s - %(message)s")

router = APIRouter(prefix="/user", tags=["User"])

dbClient = DBServiceClient()
notifyClient = NotifyServiceClient()

class UserRegister(BaseModel):
    """User registration request model."""
    Name: str = Field(max_length=25, min_length=3)
    Phone: str = Field(min_length=10)
    Email: str = Field(pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    Profession: str = Field(min_length=3)
    Password: SecretStr = Field(min_length=6)

class UserLogin(BaseModel):
    """User login request model."""
    Email: str = Field(pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    Password: SecretStr = Field(min_length=6)


@router.post("/register", status_code=201)
async def register(response:Response,user: UserRegister):
    """Register a new user account.
    
    Creates a new user in the database, sets up notification preferences,
    and sends a welcome email.
    
    Args:
        user: User registration details
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If registration fails
    """
    try:
        logging.info(f"Registering user with email: {user.Email}")

        userId = await dbClient.registerUser(user.Name, user.Phone, user.Email, user.Password.get_secret_value(),user.Profession)
        await notifyClient.createUser(userId, user.Name, user.Email)
        await notifyClient.notifyRegistration(userId, "Registration")
        token = createAccessToken(uuid.UUID(userId))
        
        # response.set_cookie("access_token", token, httponly=True,samesite="none")

        return {"message": "User registered successfully","token":token}

    except Exception as e:
        logging.error(f"Error registering user: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/login")
async def login(response:Response,user: UserLogin):
    """Authenticate user and generate access token.
    
    Validates user credentials and returns a JWT token for subsequent requests.
    
    Args:
        user: User login credentials
        
    Returns:
        dict: JWT access token
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        logging.info(f"Logging in user with email: {user.Email}")
        userId = await dbClient.loginUser(user.Email, user.Password.get_secret_value())
        token = createAccessToken(uuid.UUID(userId))
        
        # response.set_cookie("access_token", token, httponly=True,samesite="none")
        return {"message": "Login successful","token":token}

    except Exception as e:
        logging.error(f"Error logging in user: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid credentials")  

@router.get("/profile", responses={403: {"description": "Forbidden - Insufficient permissions"}})
async def getProfile(userId: uuid.UUID = Depends(getCurrentUser)):
    """Retrieve authenticated user's profile.
    
    Fetches user profile information including name, email, and enrolled courses.
    
    Args:
        userId: Authenticated user ID from JWT token
        
    Returns:
        dict: User profile data
        
    Raises:
        HTTPException: If profile fetch fails
    """
    try:
        logging.info(f"Fetching profile for user: {userId}")
        profile = await dbClient.getUserProfile(userId) 
        return profile 

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching user profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/delete", responses={403: {"description": "Forbidden - Insufficient permissions"}})
async def deleteAccount(userId: uuid.UUID = Depends(getCurrentUser)):
    """Delete user account.

    Removes user from database and sends cancellation notification.

    Args:
        userId: Authenticated user ID from JWT token

    Returns:
        dict: Success message

    Raises:
        HTTPException: If deletion fails
    """
    try:
        logging.info(f"Deleting account for user: {userId}")
        await dbClient.deleteUser(userId)
        await notifyClient.notifyRegistration(userId, "AccountDeletion")

        return {"message": "Account deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting user account: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
