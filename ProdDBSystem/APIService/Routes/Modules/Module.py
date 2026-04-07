"""Module routes for tracking and updating user module progress and completion.

Exposes endpoints to resume, update, and complete learning modules,
using Redis for caching and SQS for async event processing.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
import logging
import json

logging.basicConfig(level=logging.INFO, format="%(filename)s - %(levelname)s - %(message)s")

router = APIRouter(prefix="/module", tags=["Module"])

class ModuleProgress(BaseModel):
    userId: str 
    moduleName: str 
    CompletedPage: str
    LastseenPage: str

class ModuleCompletion(BaseModel):
    userId: str 
    moduleName: str
    QuizPercentage: float = Field(default=None, ge=0, le=100)


@router.get("/resume/{userId}/{moduleName}")
async def resumeModule(userId: str, moduleName: str, request: Request):
    """
    Retrieve the last saved progress for a user's module.

    Checks Redis cache first; on miss, queries the database directly.

    Args:
        userId: The unique identifier of the user.
        moduleName: The name of the module to resume.

    Returns:
        The module progress data for the given user and module.

    Raises:
        HTTPException 404: If no progress record is found.
        HTTPException 500: On internal errors.
    """
    conn = None
    try:
        logging.info(f"Fetching resume module data - userId: {userId}, moduleName: {moduleName}")
        redis = await request.app.state.redis_instance.getRedisconnection()
        
        cachedData = await redis.hget(f"user:{userId}", "resumeModule")

        if cachedData:
            data = json.loads(cachedData)
            if data.get("moduleName") == moduleName:
                logging.info(f"Cache hit for resume module - userId: {userId}, moduleName: {moduleName}, data: {data}")
                return data

        logging.info(f"Cache miss for resume module, querying database - userId: {userId}, moduleName: {moduleName}")
        conn = request.app.state.db_instance.getDBconnection()
        cursor = conn.cursor()
        cursor.execute('SELECT "ModuleId" FROM "Module" WHERE "ModuleName" = %s', (moduleName,))
        moduleId = cursor.fetchone()

        if not moduleId:
            logging.warning(f"Module not found - moduleName: {moduleName}")
            cursor.close()
            raise HTTPException(
                status_code=404,
                detail="Module not found"
            )

        cursor.execute('SELECT "LastSeenPage" FROM "UserModuleProgress" WHERE "UserId" = %s AND "ModuleId" = %s', (userId, moduleId[0]))
        progress = cursor.fetchone()
        cursor.close()  

        if progress is None:
            logging.warning(f"Module progress not found - userId: {userId}, moduleName: {moduleName}")
            raise HTTPException(
                status_code=404,
                detail="Module progress not found"
            )
        
        progressData = {
            "userId": userId,
            "moduleName": moduleName,
            "LastPage": progress[0] if progress else None
        }

        await redis.hset(f"user:{userId}", "resumeModule", json.dumps(progressData))
        logging.info(f"Resume module data fetched from DB and cached - userId: {userId}, moduleName: {moduleName}, data: {progressData}")
        return progressData

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error while fetching module resume data - userId: {userId}, moduleName: {moduleName}, error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while fetching module resume data"
        )
    finally:
        if conn:
            request.app.state.db_instance.releaseDBconnection(conn)
            
@router.post("/update", status_code=201)
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
        logging.info(f"Processing module progress update - userId: {moduleProgress.userId}, moduleName: {moduleProgress.moduleName}, page: {moduleProgress.CompletedPage}")
        redis = await request.app.state.redis_instance.getRedisconnection()
        sqs = request.app.state.sqs_instance
        
        userId = moduleProgress.userId
        moduleName = moduleProgress.moduleName
        CompletedPage = moduleProgress.CompletedPage
        LastseenPage = moduleProgress.LastseenPage
        data = {
            "userId": userId,
            "moduleName": moduleName,
            "CompletedPage": CompletedPage,
            "LastseenPage": LastseenPage
        }

        if not all([userId, moduleName, CompletedPage]):
            logging.warning(f"Missing required fields in module progress data - userId: {userId}, moduleName: {moduleName}, page: {CompletedPage}")
            raise HTTPException(
                status_code=400,
                detail="Missing required fields in module progress data"
            )

        message = {
            "eventType": "updateModule",
            "data": data
        }

        await sqs.send_message(QueueUrl=sqs.get_queue_url(), Message=json.dumps(message))
        logging.info(f"Module update event sent to SQS - userId: {userId}, moduleName: {moduleName}, page: {CompletedPage}")

        cachedData = await redis.hget(f"user:{userId}", "resumeModule")

        if cachedData:
            cachedDataDict = json.loads(cachedData)
            if cachedDataDict.get("moduleName") == moduleName:
                await redis.hdel(f"user:{userId}", "resumeModule")
                logging.info(f"Cleared old resume module cache - userId: {userId}, moduleName: {moduleName}")
        
        await redis.hset(f"user:{userId}", "resumeModule", json.dumps(data))
        logging.info(f"Module progress cached in Redis - userId: {userId}, moduleName: {moduleName}, page: {CompletedPage}")

        await redis.hdel(f"user:{userId}", "inProgressModules")

        logging.info(f"Module progress update completed successfully - userId: {userId}, moduleName: {moduleName}")
        return {"message": "Module progress update queued successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error while updating module progress - userId: {moduleProgress.userId}, moduleName: {moduleProgress.moduleName}, error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while updating module progress"
        )

@router.post("/complete", status_code=201)
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
        logging.info(f"Processing module completion - userId: {moduleCompletion.userId}, moduleName: {moduleCompletion.moduleName}, quizPercentage: {moduleCompletion.QuizPercentage}")
        sqs = request.app.state.sqs_instance
        redis = await request.app.state.redis_instance.getRedisconnection()

        userId = moduleCompletion.userId
        moduleName = moduleCompletion.moduleName
        QuizPercentage = moduleCompletion.QuizPercentage

        data = {
            "userId": userId,
            "moduleName": moduleName,
            "QuizPercentage": QuizPercentage
        }

        if not all([userId, moduleName]) or QuizPercentage is None:
            logging.warning(f"Missing required fields in module completion data - userId: {userId}, moduleName: {moduleName}, quizPercentage: {QuizPercentage}")
            raise HTTPException(
                status_code=400,
                detail="Missing required fields in module completion data"
            )

        message = {
            "eventType": "completeModule",
            "data": data
        }

        await sqs.send_message(QueueUrl=sqs.get_queue_url(), Message=json.dumps(message))
        logging.info(f"Module completion event sent to SQS - userId: {userId}, moduleName: {moduleName}, quizPercentage: {QuizPercentage}")
        
        await redis.hdel(f"user:{userId}", "courseProgress")
        await redis.hdel(f"user:{userId}", "inProgressModules")
        await redis.hdel(f"user:{userId}", "completedModules")
        
        logging.info(f"Cleared in-progress modules cache - userId: {userId}")

        logging.info(f"Module completion processed successfully - userId: {userId}, moduleName: {moduleName}")
        return {"message": "Module completion queued successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error while processing module completion - userId: {moduleCompletion.userId}, moduleName: {moduleCompletion.moduleName}, error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while processing module completion"
        )


@router.get("/inProgress/{userId}")
async def getInProgressModules(userId: str, request: Request):
    """
    Retrieve a list of modules that a user is currently studying.

    Queries the database for modules where the user has started but not yet
    completed the learning process.

    Args:
        userId: The unique identifier of the user.
        conn: Database connection dependency.

    Returns:
        A list of module names that the user is currently studying.

    Raises:
        HTTPException 500: On internal errors.
    """
    conn = None
    try:
        logging.info(f"Fetching in-progress modules - userId: {userId}")
        redis = await request.app.state.redis_instance.getRedisconnection()
        cachedModules = await redis.hget(f"user:{userId}","inProgressModules")

        if cachedModules:
            data = json.loads(cachedModules)
            logging.info(f"Cache hit for in-progress modules - userId: {userId}, count: {len(data.get('modules', []))}")
            return data

        logging.info(f"Cache miss for in-progress modules, querying database - userId: {userId}")
        conn = request.app.state.db_instance.getDBconnection()
        cursor = conn.cursor()
        
       
        query = """
            SELECT m."ModuleName",c."CourseName",p."CompletedPage"
            FROM "Module" m
            JOIN "UserModuleProgress" p ON m."ModuleId" = p."ModuleId"
            LEFT JOIN "Course" c ON c."CourseId" = m."CourseId"
            WHERE p."UserId" = %s AND p."Completed" = FALSE
        """
        logging.info(f"Executing query with userId: {userId}, type: {type(userId)}")
        cursor.execute(query, (userId,))

        modules = cursor.fetchall()
        logging.info(f"Query returned {len(modules)} rows - userId: {userId}")
        cursor.close()
        
        if not modules:
            logging.warning(f"No in-progress modules found - userId: {userId}")
            raise HTTPException(status_code=404, detail="No in-progress modules found")
        
        moduleNames = [module[0] for module in modules]
        courseNames = [module[1] for module in modules]
        lastPages = [module[2] for module in modules]

        data = {
            "modules": moduleNames,
            "courseNames": courseNames,
            "lastPages": lastPages
        }

        await redis.hset(f"user:{userId}", "inProgressModules", json.dumps(data))
        logging.info(f"In-progress modules fetched from DB and cached - userId: {userId}, count: {len(moduleNames)}, modules: {moduleNames}")
        return data


    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error while fetching in-progress modules - userId: {userId}, error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while fetching in-progress modules"
        )
    finally:
        if conn:
            request.app.state.db_instance.releaseDBconnection(conn)

@router.get("/completed/{userId}")
async def getCompletedModules(userId: str, request: Request):
    """
    Retrieve a list of modules that a user has completed.

    Queries the database for modules where the user has marked completion.

    Args:
        userId: The unique identifier of the user.
        conn: Database connection dependency.

    Returns:
        A list of module names that the user has completed.

    Raises:
        HTTPException 500: On internal errors.
    """
    conn = None
    try:
        logging.info(f"Fetching completed modules - userId: {userId}")
        redis = await request.app.state.redis_instance.getRedisconnection()
        
        cachedData = await redis.hget(f"user:{userId}", "completedModules")
        if cachedData:
            data = json.loads(cachedData)
            logging.info(f"Cache hit for completed modules - userId: {userId}, count: {len(data.get('modules', []))}")
            return data

        logging.info(f"Cache miss for completed modules, querying database - userId: {userId}")
        conn = request.app.state.db_instance.getDBconnection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m."ModuleName", p."CompletedOn"
            FROM "Module" m
            JOIN "UserModuleProgress" p 
                ON m."ModuleId" = p."ModuleId"
            WHERE 
                p."UserId" = %s 
                AND p."Completed" = TRUE 
            ORDER BY p."CompletedOn" DESC
            LIMIT 3
        """, (userId,))
        modules = cursor.fetchall()
        cursor.close()

        if not modules:
            logging.warning(f"No completed modules found - userId: {userId}")
            raise HTTPException(status_code=404, detail="No completed modules found")

        moduleNames = [module[0] for module in modules]
        completionTimes = [module[1].isoformat() if module[1] else None for module in modules]
        
        data = {
            "modules": moduleNames,
            "completionTimes": completionTimes
        }
        
        await redis.hset(f"user:{userId}", "completedModules", json.dumps(data))
        logging.info(f"Completed modules fetched from DB and cached - userId: {userId}, count: {len(moduleNames)}, modules: {moduleNames}")
        return data

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error while fetching completed modules - userId: {userId}, error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while fetching completed modules"
        )
    finally:
        if conn:
            request.app.state.db_instance.releaseDBconnection(conn)
