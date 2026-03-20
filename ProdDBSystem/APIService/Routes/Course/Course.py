"""Course routes for purchasing courses and tracking course progress.

Exposes endpoints to purchase a course and retrieve a user's course progress,
using Redis for caching and SQS for async event processing.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
import logging
import json

logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/course", tags=["Course"])


class CoursePurchase(BaseModel):
    userId: str
    courseName: str


@router.post("/purchase")
async def purchaseCourse(coursePurchase: CoursePurchase, request: Request):
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
        redis = await request.app.state.redis_instance.getRedisconnection()
        sqs = request.app.state.sqs_instance
        
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
async def getCourseProgress(userId: str, courseName: str, request: Request):
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
        redis = await request.app.state.redis_instance.getRedisconnection()
        
        cachedData = await redis.hget(f"user:{userId}", "courseProgress")
        if cachedData:
            data = json.loads(cachedData)
            if data.get("courseName") == courseName:
                logging.info(f"Cache hit for course progress: {data}")
                return data

        conn = request.app.state.db_instance.getDBconnection()
        cursor = conn.cursor()

        cursor.execute('SELECT "CourseId" FROM "Course" WHERE "CourseName" = %s', (courseName,))
        courseId = cursor.fetchone()    
        if not courseId:
            logging.warning("Course not found for name: %s", courseName)
            cursor.close()
            return

        cursor.execute('SELECT COUNT(*) FROM "Module" WHERE "CourseId" = %s', (courseId[0],))
        totalModules = cursor.fetchone()[0]

        cursor.execute('SELECT "Completed" FROM "UserModuleProgress" WHERE "UserId" = %s', (userId,))
        progress = cursor.fetchall()
        cursor.close()

        inprogress = 0
        completed = 0
        for row in progress:
            if not row[0]:
                inprogress += 1
            else:
                completed += 1

        logging.info("Fetched course progress for user: %s, course: %s", userId, courseName)
        return {
            "totalModules": totalModules,
            "inProgress": inprogress,
            "completed": completed
        }

    except Exception as e:
        logging.error(f"Error while fetching course progress: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while fetching course progress"
        )






