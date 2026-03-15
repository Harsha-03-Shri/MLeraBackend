"""User routes for registration, login, and profile retrieval.

Exposes endpoints to register a new user, authenticate an existing user,
and fetch a user's profile, using PostgreSQL for persistence and Redis for caching.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, SecretStr, EmailStr, Field
import bcrypt
import logging
import uuid
from main import app

logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/user", tags=["User"])


class User(BaseModel):
    Name: str = Field(min_length=1)
    Profession: str = Field(min_length=1)
    Phone: str = Field(min_length=1)
    Email: EmailStr
    Password: SecretStr


class UserLogin(BaseModel):
    Email: EmailStr
    Password: SecretStr


def getDB():
    yield from app.state.db_instance.getDBconnection()

def getRedis():
    yield from app.state.redis_instance.getRedisconnection()


@router.post("/register")
async def userRegistration(user: User, conn=Depends(getDB)):
    """Register a new user and store credentials in the database.

    Hashes the user's password with bcrypt, inserts the user record
    and auth record in a single transaction, rolling back on failure.

    Args:
        user: Payload containing Name, Profession, Phone, Email, and Password.
        conn: Database connection dependency.

    Returns:
        A confirmation message with the new user's ID.

    Raises:
        HTTPException 500: On database transaction errors or internal errors.
    """
    try:
        userId = uuid.uuid4()
        password = user.Password.get_secret_value().encode()
        hashed = bcrypt.hashpw(password, bcrypt.gensalt())

        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO Users VALUES (%s,%s,%s,%s,%s)",
                (userId, user.Name, user.Profession, user.Phone, user.Email)
            )
            cursor.execute(
                "INSERT INTO Auth VALUES (%s,%s,%s)",
                (user.Email, hashed, userId)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            logging.error(f"Transaction failed, rolled back: {e}")
            raise HTTPException(
                status_code=500,
                detail="Database transaction error registering user"
            )
        finally:
            cursor.close()

        return {"message": "User registered successfully", "userId": str(userId)}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error while registering user: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while registering user"
        )


@router.post("/login")
async def userLogin(userlogin: UserLogin, conn=Depends(getDB)):
    """Authenticate a user by verifying their password.

    Fetches the stored hashed password from the Auth table and
    verifies it against the provided password using bcrypt.

    Args:
        userlogin: Payload containing Email and Password.
        conn: Database connection dependency.

    Returns:
        A dict containing the authenticated user's ID.

    Raises:
        HTTPException 401: If credentials are invalid.
        HTTPException 500: On internal errors.
    """
    try:
        email = userlogin.Email
        password = userlogin.Password.get_secret_value().encode()

        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Auth WHERE Email = %s", (email,))
            userData = cursor.fetchone()
        finally:
            cursor.close()

        if not userData or not bcrypt.checkpw(password, userData[1].encode()):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        return {"userId": str(userData[2])}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error while logging in user: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while logging in user"
        )


@router.get("/profile/{userId}")
async def userProfile(userId: str, conn=Depends(getDB), redis=Depends(getRedis)):
    """Retrieve a user's profile by their ID.

    Checks Redis cache first; on miss, queries the database and
    caches the result before returning.

    Args:
        userId: The unique identifier of the user.
        conn: Database connection dependency.
        redis: Redis connection dependency.

    Returns:
        A dict containing Name, Profession, Phone, and Email.

    Raises:
        HTTPException 404: If the user is not found.
        HTTPException 500: On internal errors.
    """
    try:
        cachedData = await redis.hget(f"user:{userId}", "profile")
        if cachedData:
            return cachedData

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE UserId = %s", (userId,))
        userData = cursor.fetchone()
        cursor.close()

        if not userData:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        profile = {
            "Name": userData[1],
            "Profession": userData[2],
            "Phone": userData[3],
            "Email": userData[4]
        }

        await redis.hset(f"user:{userId}", "profile", profile)
        return profile

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error while fetching user profile: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while fetching user profile"
        )
