"""PracticeQuiz routes for submitting quiz results and retrieving quiz reports.

Exposes endpoints to submit a practice quiz score and fetch a user's
quiz performance report, using Redis for caching and SQS for async processing.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
import logging
import json
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(filename)s - %(levelname)s - %(message)s")

router = APIRouter(prefix="/practiceQuiz", tags=["Practice Quiz"])

class Submit(BaseModel):
    userId: str
    moduleName: str
    score: int

@router.post("/submit")
async def submitPracticeQuiz(submitData: Submit, request: Request):
    """Submit a practice quiz score and update the cached report.

    Sends a submitPracticeQuiz event to SQS and updates the user's
    cached quiz report in Redis if one already exists.

    Args:
        userId: The unique identifier of the user.
        moduleName: The name of the module the quiz belongs to.
        score: The score achieved in the quiz.
        conn: Database connection dependency.
        redis: Redis connection dependency.
        sqs: SQS client dependency.

    Returns:
        A confirmation message that the quiz submission was queued.

    Raises:
        HTTPException 500: On internal errors.
    """
    try:
        redis = await request.app.state.redis_instance.getRedisconnection()
        sqs = request.app.state.sqs_instance
        
        data = {
            "userId": submitData.userId,
            "moduleName": submitData.moduleName,
            "score": submitData.score
        }
        message = {
            "eventType": "submitPracticeQuiz",
            "data": data
        }
        await sqs.send_message(QueueUrl=sqs.get_queue_url(), Message=json.dumps(message))

        cachedData = await redis.hget(f"user:{submitData.userId}", "practiceQuizReport")
        if cachedData:
            data = json.loads(cachedData)
            data["HighestScore"] = max(data["HighestScore"], submitData.score)
            data["LowestScore"] = min(data["LowestScore"], submitData.score)
            data["Attempts"] += 1
            await redis.hset(f"user:{submitData.userId}", "practiceQuizReport", json.dumps(data))

        return {"message": "Practice quiz submission queued successfully"}

    except Exception as e:
        logging.error(f"Error while submitting practice quiz result: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while submitting practice quiz result"
        )


@router.get("/report/{userId}/{moduleName}")
async def getPracticeQuizReport(userId: str, moduleName: str, request: Request):
    """Retrieve the practice quiz performance report for a user and module.

    Checks Redis cache first; on miss, queries the database directly.
    Caches the result in Redis before returning.

    Args:
        userId: The unique identifier of the user.
        moduleName: The name of the module.
        request: FastAPI request object.

    Returns:
        A dict with HighestScore, LowestScore, and Attempts.

    Raises:
        HTTPException 404: If the module or report is not found.
        HTTPException 500: On internal errors.
    """
    conn = None
    try:
        redis = await request.app.state.redis_instance.getRedisconnection()
        
        cachedData = await redis.hget(f"user:{userId}", "practiceQuizReport")
        if cachedData:
            return json.loads(cachedData)

        conn = request.app.state.db_instance.getDBconnection()
        cursor = conn.cursor()
        cursor.execute('SELECT "ModuleId" FROM "Module" WHERE "ModuleName" = %s', (moduleName,))
        moduleId = cursor.fetchone()
        if not moduleId:
            cursor.close()
            raise HTTPException(
                status_code=404,
                detail="Module not found"
            )

        cursor.execute('SELECT * FROM "PracticeQuiz" WHERE "UserId" = %s AND "ModuleId" = %s', (userId, moduleId[0]))
        report = cursor.fetchone()
        cursor.close()

        if not report:
            raise HTTPException(
                status_code=404,
                detail="No quiz attempts found for this module"
            )

        reportData = {
            "HighestScore": report[2],
            "LowestScore": report[3],
            "Attempts": report[4],
        }

        await redis.hset(f"user:{userId}", "practiceQuizReport", json.dumps(reportData))
        return reportData

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error while fetching practice quiz report: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while fetching practice quiz report"
        )
    finally:
        if conn:
            request.app.state.db_instance.releaseDBconnection(conn)
