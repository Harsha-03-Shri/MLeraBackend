"""Course routes for purchasing courses and tracking course progress.

Exposes endpoints to purchase a course and retrieve a user's course progress,
using Redis for caching and SQS for async event processing.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging
import json
from main import app

logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/course", tags=["Course"])


def getDB():
    yield from app.state.db_instance.getDBconnection()

def getRedis():
    yield from app.state.redis_instance.getRedisconnection()

def getSQS():
    yield from app.state.sqs_instance


class CoursePurchase(BaseModel):
    userId: str
    courseName: str


@router.post("/purchase")
async def purchaseCourse(coursePurchase: CoursePurchase, conn=Depends(getDB), redis=Depends(getRedis), sqs=Depends(getSQS)):
    """Queue a course purchase event and cache the result.

    Sends a purchaseCourse event to SQS for async processing and
    stores the purchased course name in Redis.

    Args:
        coursePurchase: Payload containing userId and courseName.
        conn: Database connection dependency.
        redis: Redis connection dependency.
        sqs: SQS client dependency.

    Returns:
        A confirmation message that the purchase was queued.

    Raises:
        HTTPException 500: On internal errors.
    """
    try:
        data = {
            "userId": coursePurchase.userId,
            "courseName": coursePurchase.courseName
        }
        message = {
            "eventType": "purchaseCourse",
            "data": data
        }
        await sqs.send_message(QueueUrl=sqs.get_queue_url(), Message=json.dumps(message))
        await redis.hset(f"user:{coursePurchase.userId}", "purchasedCourse", coursePurchase.courseName)
        return {"message": "Course purchase queued successfully"}

    except Exception as e:
        logging.error(f"Error while purchasing course: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while purchasing course"
        )


@router.get("/progress/{userId}/{courseName}")
async def getCourseProgress(userId: str, courseName: str, conn=Depends(getDB), redis=Depends(getRedis), sqs=Depends(getSQS)):
    """Retrieve the progress of a user for a specific course.

    Checks Redis cache first; on miss, sends a courseProgress event to SQS.
    Caches the result in Redis before returning.

    Args:
        userId: The unique identifier of the user.
        courseName: The name of the course.
        conn: Database connection dependency.
        redis: Redis connection dependency.
        sqs: SQS client dependency.

    Returns:
        The course progress data for the given user and course.

    Raises:
        HTTPException 404: If no progress record is found.
        HTTPException 500: On internal errors.
    """
    try:
        cachedData = await redis.hget(f"user:{userId}", "courseProgress")
        if cachedData and cachedData.get("courseName") == courseName:
            return cachedData

        data = {
            "userId": userId,
            "courseName": courseName
        }
        message = {
            "eventType": "courseProgress",
            "data": data
        }

        progress = await sqs.send_message(QueueUrl=sqs.get_queue_url(), Message=json.dumps(message))
        if progress:
            await redis.hset(f"user:{userId}", "courseProgress", progress)
            return progress
        else:
            raise HTTPException(
                status_code=404,
                detail="Course progress not found"
            )

    except Exception as e:
        logging.error(f"Error while fetching course progress: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while fetching course progress"
        )
