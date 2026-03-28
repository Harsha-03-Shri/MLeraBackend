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
        logging.info(f"Processing practice quiz submission - userId: {submitData.userId}, moduleName: {submitData.moduleName}, score: {submitData.score}")
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
        logging.info(f"Practice quiz submission event sent to SQS - userId: {submitData.userId}, moduleName: {submitData.moduleName}, score: {submitData.score}")

        cachedData = await redis.hget(f"user:{submitData.userId}", "practiceQuizReport")
        if cachedData:
            data = json.loads(cachedData)
            oldHighest = data["HighestScore"]
            oldLowest = data["LowestScore"]
            data["HighestScore"] = max(data["HighestScore"], submitData.score)
            data["LowestScore"] = min(data["LowestScore"], submitData.score)
            data["Attempts"] += 1
            await redis.hset(f"user:{submitData.userId}", "practiceQuizReport", json.dumps(data))
            logging.info(f"Practice quiz cache updated - userId: {submitData.userId}, attempts: {data['Attempts']}, highest: {oldHighest}->{data['HighestScore']}, lowest: {oldLowest}->{data['LowestScore']}")
        else:
            logging.info(f"No cached practice quiz report found - userId: {submitData.userId}")

        logging.info(f"Practice quiz submission completed successfully - userId: {submitData.userId}, moduleName: {submitData.moduleName}")
        return {"message": "Practice quiz submission queued successfully"}

    except Exception as e:
        logging.error(f"Error while submitting practice quiz result - userId: {submitData.userId}, moduleName: {submitData.moduleName}, error: {str(e)}")
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
        logging.info(f"Fetching practice quiz report - userId: {userId}, moduleName: {moduleName}")
        redis = await request.app.state.redis_instance.getRedisconnection()
        
        cachedData = await redis.hget(f"user:{userId}", "practiceQuizReport")
        if cachedData:
            reportData = json.loads(cachedData)
            logging.info(f"Cache hit for practice quiz report - userId: {userId}, moduleName: {moduleName}, attempts: {reportData.get('Attempts')}")
            return reportData

        logging.info(f"Cache miss for practice quiz report, querying database - userId: {userId}, moduleName: {moduleName}")
        conn = request.app.state.db_instance.getDBconnection()
        cursor = conn.cursor()
        cursor.execute('SELECT "ModuleId" FROM "Module" WHERE "ModuleName" = %s', (moduleName,))
        moduleId = cursor.fetchone()
        if not moduleId:
            cursor.close()
            logging.warning(f"Module not found - moduleName: {moduleName}")
            raise HTTPException(
                status_code=404,
                detail="Module not found"
            )

        cursor.execute('SELECT * FROM "PracticeQuiz" WHERE "UserId" = %s AND "ModuleId" = %s', (userId, moduleId[0]))
        report = cursor.fetchone()
        cursor.close()

        if not report:
            logging.warning(f"No quiz attempts found - userId: {userId}, moduleName: {moduleName}")
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
        logging.info(f"Practice quiz report fetched from DB and cached - userId: {userId}, moduleName: {moduleName}, attempts: {reportData['Attempts']}, highest: {reportData['HighestScore']}, lowest: {reportData['LowestScore']}")
        return reportData

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error while fetching practice quiz report - userId: {userId}, moduleName: {moduleName}, error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while fetching practice quiz report"
        )
    finally:
        if conn:
            request.app.state.db_instance.releaseDBconnection(conn)
