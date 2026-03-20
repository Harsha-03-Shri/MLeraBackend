"""Module routes for tracking and updating user module progress and completion.

Exposes endpoints to resume, update, and complete learning modules,
using Redis for caching and SQS for async event processing.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
import logging
import json

logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/module", tags=["Module"])

class ModuleProgress(BaseModel):
    userId: str 
    moduleName: str 
    Page: str

class ModuleCompletion(BaseModel):
    userId: str 
    moduleName: str
    QuizPercentage: float = Field(default=None, ge=0, le=100)


@router.get("/resume/{userId}/{moduleName}")
async def resumeModule(userId: str, moduleName: str, request: Request):
    """
    Retrieve the last saved progress for a user's module.

    Checks Redis cache first; on miss, sends a resumeModule event to SQS.
    Caches the result in Redis before returning.

    Args:
        userId: The unique identifier of the user.
        moduleName: The name of the module to resume.
        conn: Database connection dependency.
        redis: Redis connection dependency.
        sqs: SQS client dependency.

    Returns:
        The module progress data for the given user and module.

    Raises:
        HTTPException 404: If no progress record is found.
        HTTPException 500: On internal errors.
    """
    try:
        redis = await request.app.state.redis_instance.getRedisconnection()
        
        cachedData = await redis.hget(f"user:{userId}", "resumeModule")

        if cachedData:
            data = json.loads(cachedData)
            if data.get("moduleName") == moduleName:
                logging.info(f"Cache hit resume module")
                return data

        conn = request.app.state.db_instance.getDBconnection()
        cursor = conn.cursor()
        cursor.execute('SELECT "ModuleId" FROM "Module" WHERE "ModuleName" = %s', (moduleName,))
        moduleId = cursor.fetchone()

        if not moduleId:
            logging.warning("Module not found for name: %s", moduleName)
            cursor.close()
            raise HTTPException(
                status_code=404,
                detail="Module not found"
            )

        cursor.execute('SELECT "Page" FROM "UserModuleProgress" WHERE "UserId" = %s AND "ModuleId" = %s', (userId, moduleId[0]))
        progress = cursor.fetchone()
        cursor.close()  

        if progress is None:
            raise HTTPException(
                status_code=404,
                detail="Module progress not found"
            )
        
        progress = {
            "userId": userId,
            "moduleName": moduleName,
            "LastPage": progress[0]
        }

        logging.info(f"Cache miss resume module, fetched from DB: {progress}")
        await redis.hset(f"user:{userId}", "resumeModule", json.dumps(progress))
        return progress

    except Exception as e:
        logging.error(f"Error while fetching module resume data: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while fetching module resume data"
        )

@router.post("/update")
async def updateModule(moduleProgress: ModuleProgress, request: Request):
    """
    Update the last visited page for a user's module.

    Validates required fields, sends an updateModule event to SQS,
    and refreshes the Redis cache with the latest progress.

    Args:
        moduleProgress: Payload containing userId, moduleName, and Page.
        conn: Database connection dependency.
        redis: Redis connection dependency.
        sqs: SQS client dependency.

    Returns:
        A confirmation message that the update was queued.

    Raises:
        HTTPException 400: If any required fields are missing.
        HTTPException 500: On internal errors.
    """
    try:
        redis = await request.app.state.redis_instance.getRedisconnection()
        sqs = request.app.state.sqs_instance
        
        userId = moduleProgress.userId
        moduleName = moduleProgress.moduleName
        Page = moduleProgress.Page

        data = {
            "userId": userId,
            "moduleName": moduleName,
            "LastPage": Page
        }

        if not all([userId, moduleName, Page]):
            logging.warning("Missing required fields in module progress data: %s", json.dumps(data))
            raise HTTPException(
                status_code=400,
                detail="Missing required fields in module progress data"
            )

        message = {
            "eventType": "updateModule",
            "data": data
        }

        await sqs.send_message(QueueUrl=sqs.get_queue_url(), Message=json.dumps(message))

        cachedData = await redis.hget(f"user:{userId}", "resumeModule")

        if cachedData:
            data = json.loads(cachedData)
            if data.get("moduleName") == moduleName:
                await redis.hdel(f"user:{userId}", "resumeModule")  
        
        await redis.hset(f"user:{userId}", "resumeModule", json.dumps(data))

        return {"message": "Module progress update queued successfully"}

    except Exception as e:
        logging.error(f"Error while updating module progress: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while updating module progress"
        )

@router.post("/complete")
async def completeModule(moduleCompletion: ModuleCompletion, request: Request):
    """
    Mark a module as completed for a user.

    Validates required fields, then sends a completeModule event to SQS
    for async processing.

    Args:
        moduleCompletion: Payload containing userId, moduleName, and QuizPercentage.
        conn: Database connection dependency.
        redis: Redis connection dependency.
        sqs: SQS client dependency.

    Returns:
        A confirmation message that the completion was queued.

    Raises:
        HTTPException 400: If any required fields are missing.
        HTTPException 500: On internal errors.
    """
    try:
        sqs = request.app.state.sqs_instance
        
        userId = moduleCompletion.userId
        moduleName = moduleCompletion.moduleName
        QuizPercentage = moduleCompletion.QuizPercentage

        data = {
            "userId": userId,
            "moduleName": moduleName,
            "QuizPercentage": QuizPercentage
        }

        if not all([userId, moduleName]) or QuizPercentage is None:
            logging.warning("Missing required fields in module completion data: %s", json.dumps(data))
            raise HTTPException(
                status_code=400,
                detail="Missing required fields in module completion data"
            )

        message = {
            "eventType": "completeModule",
            "data": data
        }

        await sqs.send_message(QueueUrl=sqs.get_queue_url(), Message=json.dumps(message))

        return {"message": "Module completion queued successfully"}

    except Exception as e:
        logging.error(f"Error while processing module completion: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while processing module completion"
        )

