"""User routes for registration, login, and profile retrieval.

Exposes endpoints to register a new user, authenticate an existing user,
and fetch a user's profile, using PostgreSQL for persistence and Redis for caching.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, SecretStr, EmailStr, Field
import bcrypt
import logging
import uuid
import json

logging.basicConfig(level=logging.INFO, format="%(filename)s - %(levelname)s - %(message)s")

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


@router.post("/register")
async def userRegistration(user: User, request: Request):
    """Register a new user and store credentials in the database.

    Hashes the user's password with bcrypt, inserts the user record
    and auth record in a single transaction, rolling back on failure.

    Args:
        user: Payload containing Name, Profession, Phone, Email, and Password.
        request: FastAPI request object.

    Returns:
        A confirmation message with the new user's ID.

    Raises:
        HTTPException 500: On database transaction errors or internal errors.
    """
    conn = None
    try:
        logging.info(f"Processing user registration - email: {user.Email}, name: {user.Name}")
        userId = uuid.uuid4()
        password = user.Password.get_secret_value().encode()
        hashed = bcrypt.hashpw(password, bcrypt.gensalt())
        logging.info(f"Password hashed successfully - userId: {userId}")

        conn = request.app.state.db_instance.getDBconnection()
        cursor = conn.cursor()
        try:
            logging.info(f"Inserting user into database - userId: {userId}, email: {user.Email}")
            cursor.execute(
                'INSERT INTO "User" ("UserId", "Name", "Profession", "Phone", "Email") VALUES (%s,%s,%s,%s,%s)',
                (userId, user.Name, user.Profession, user.Phone, user.Email)
            )
            cursor.execute(
                'INSERT INTO "Auth" ("Email", "PasswordHash", "UserId") VALUES (%s,%s,%s)',
                (user.Email, hashed.decode('utf-8'), userId)
            )
            conn.commit()
            logging.info(f"User registered successfully in database - userId: {userId}, email: {user.Email}")
        except Exception as e:
            conn.rollback()
            logging.error(f"Transaction failed, rolled back - email: {user.Email}, error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Database transaction error registering user"
            )
        finally:
            cursor.close()

        logging.info(f"User registration completed successfully - userId: {userId}, email: {user.Email}")
        return {"message": "User registered successfully", "userId": str(userId)}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error while registering user - email: {user.Email}, error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while registering user"
        )
    finally:
        if conn:
            request.app.state.db_instance.releaseDBconnection(conn)


@router.post("/login")
async def userLogin(userlogin: UserLogin, request: Request):
    """Authenticate a user by verifying their password.

    Fetches the stored hashed password from the Auth table and
    verifies it against the provided password using bcrypt.

    Args:
        userlogin: Payload containing Email and Password.
        request: FastAPI request object.

    Returns:
        A dict containing the authenticated user's ID.

    Raises:
        HTTPException 401: If credentials are invalid.
        HTTPException 500: On internal errors.
    """
    conn = None
    try:
        logging.info(f"Processing user login - email: {userlogin.Email}")
        email = userlogin.Email
        password = userlogin.Password.get_secret_value().encode()

        conn = request.app.state.db_instance.getDBconnection()
        cursor = conn.cursor()
        try:
            logging.info(f"Querying auth credentials - email: {email}")
            cursor.execute('SELECT * FROM "Auth" WHERE "Email" = %s', (email,))
            userData = cursor.fetchone()
        finally:
            cursor.close()

        if not userData:
            logging.warning(f"Login failed - user not found - email: {email}")
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        
        if not bcrypt.checkpw(password, userData[1].encode('utf-8')):
            logging.warning(f"Login failed - invalid password - email: {email}")
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        logging.info(f"User login successful - email: {email}, userId: {userData[2]}")
        return {"userId": str(userData[2])}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error while logging in user - email: {userlogin.Email}, error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while logging in user"
        )
    finally:
        if conn:
            request.app.state.db_instance.releaseDBconnection(conn)


@router.get("/profile/{userId}")
async def userProfile(userId: str, request: Request):
    """Retrieve a user's profile by their ID.

    Checks Redis cache first; on miss, queries the database and
    caches the result before returning.

    Args:
        userId: The unique identifier of the user.
        request: FastAPI request object.

    Returns:
        A dict containing Name, Profession, Phone, and Email.

    Raises:
        HTTPException 404: If the user is not found.
        HTTPException 500: On internal errors.
    """
    conn = None
    try:
        logging.info(f"Fetching user profile - userId: {userId}")
        redis = await request.app.state.redis_instance.getRedisconnection()
        cachedData = await redis.hget(f"user:{userId}", "profile")
        if cachedData:
            profile = json.loads(cachedData)
            logging.info(f"Cache hit for user profile - userId: {userId}, email: {profile.get('Email')}")
            return profile
        
        logging.info(f"Cache miss for user profile, querying database - userId: {userId}")
        userId = uuid.UUID(userId)

        conn = request.app.state.db_instance.getDBconnection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM "User" WHERE "UserId" = %s', (userId,))
        userData = cursor.fetchone()
        cursor.close()

        if not userData:
            logging.warning(f"User not found - userId: {userId}")
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

        await redis.hset(f"user:{userId}", "profile", json.dumps(profile))
        logging.info(f"User profile fetched from DB and cached - userId: {userId}, email: {profile['Email']}")
        return profile

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error while fetching user profile - userId: {userId}, error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while fetching user profile"
        )
    finally:
        if conn:
            request.app.state.db_instance.releaseDBconnection(conn)

@router.post("/delete/{userId}")
async def deleteAccount(userId: str, request: Request):
    """Delete a user account by their ID.

    Sends delete event to SQS for async processing. The Lambda consumer
    will delete the user and all related data via CASCADE constraints.

    Args:
        userId: The unique identifier of the user to delete.
        request: FastAPI request object.

    Returns:
        A confirmation message.

    Raises:
        HTTPException 400: If userId is invalid.
        HTTPException 500: On SQS or internal errors.
    """
    try:
        logging.info(f"Processing account deletion - userId: {userId}")
        redis = await request.app.state.redis_instance.getRedisconnection()
        sqs = request.app.state.sqs_instance
        
        if userId is None:
            logging.warning(f"Account deletion failed - invalid userId: None")
            raise HTTPException(status_code=400, detail="Invalid userId: None")
        
        data = {
            "userId": str(userId)
        }
        message = {
            "eventType": "deleteAccount",
            "data": data
        }
        
        await sqs.send_message(QueueUrl=sqs.get_queue_url(), Message=json.dumps(message))
        logging.info(f"Delete account event sent to SQS - userId: {userId}")
        
        await redis.delete(f"user:{userId}")
        logging.info(f"User cache cleared from Redis - userId: {userId}")
        
        logging.info(f"Account deletion initiated successfully - userId: {userId}")
        return {"message": "Account deletion initiated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error while deleting user - userId: {userId}, error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while deleting user"
        )
