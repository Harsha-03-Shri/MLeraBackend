"""Course routes for purchasing courses and tracking course progress.

Exposes endpoints to purchase a course and retrieve a user's course progress,
using Redis for caching and SQS for async event processing.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
import logging
import json

logging.basicConfig(level=logging.INFO, format="%(filename)s - %(levelname)s - %(message)s")

router = APIRouter(prefix="/course", tags=["Course"])


class CoursePurchase(BaseModel):
    userId: str
    courseName: str


@router.post("/purchase", status_code=201)
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
        logging.info(f"Processing course purchase request - userId: {coursePurchase.userId}, courseName: {coursePurchase.courseName}")
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
        logging.info(f"Course purchase event sent to SQS - userId: {coursePurchase.userId}, courseName: {coursePurchase.courseName}")
        
        await redis.hset(f"user:{coursePurchase.userId}", "purchasedCourse", coursePurchase.courseName)
        logging.info(f"Course purchase cached in Redis - userId: {coursePurchase.userId}, courseName: {coursePurchase.courseName}")
        
        logging.info(f"Course purchase completed successfully - userId: {coursePurchase.userId}, courseName: {coursePurchase.courseName}")
        return {"message": "Course purchase queued successfully"}

    except Exception as e:
        logging.error(f"Error while purchasing course - userId: {coursePurchase.userId}, courseName: {coursePurchase.courseName}, error: {str(e)}")
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
    conn = None
    try:
        logging.info(f"Fetching course progress - userId: {userId}, courseName: {courseName}")
        redis = await request.app.state.redis_instance.getRedisconnection()
        
        cachedData = await redis.hget(f"user:{userId}", "courseProgress")
        if cachedData:
            data = json.loads(cachedData)
            if data.get("courseName") == courseName:
                logging.info(f"Cache hit for course progress - userId: {userId}, courseName: {courseName}, data: {data}")
                return data

        logging.info(f"Cache miss for course progress, querying database - userId: {userId}, courseName: {courseName}")
        conn = request.app.state.db_instance.getDBconnection()
        cursor = conn.cursor()

        cursor.execute('SELECT "CourseId" FROM "Course" WHERE "CourseName" = %s', (courseName,))
        courseId = cursor.fetchone()    
        if not courseId:
            logging.warning(f"Course not found - courseName: {courseName}")
            cursor.close()
            raise HTTPException(status_code=404, detail="Course not found")

        cursor.execute('SELECT COUNT(*) FROM "Module" WHERE "CourseId" = %s', (courseId[0],))
        totalModules = cursor.fetchone()[0]
        logging.info(f"Total modules found - courseName: {courseName}, totalModules: {totalModules}")

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

        result = {
            "totalModules": totalModules,
            "inProgress": inprogress,
            "completed": completed
        }
        logging.info(f"Course progress fetched successfully - userId: {userId}, courseName: {courseName}, progress: {result}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error while fetching course progress - userId: {userId}, courseName: {courseName}, error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while fetching course progress"
        )
    finally:
        if conn:
            request.app.state.db_instance.releaseDBconnection(conn)

@router.get("/enrolled/{userId}")
async def getEnrolledCourses(userId: str, request: Request):
    """Retrieve all courses enrolled by a user.

    Fetches the list of courses a user has purchased from Redis cache or DB.

    Args:
        userId: The unique identifier of the user.
        conn: Database connection dependency.
        redis: Redis connection dependency.

    Returns:
        A list of course names the user is enrolled in.

    Raises:
        HTTPException 404: If no enrolled courses found.
        HTTPException 500: On internal errors.
    """
    conn = None
    try:
        logging.info(f"Fetching enrolled courses - userId: {userId}")
        redis = await request.app.state.redis_instance.getRedisconnection()

        cachedData = await redis.hget(f"user:{userId}", "enrolledCourse")
        if cachedData:
            courseList = json.loads(cachedData)
            logging.info(f"Cache hit for enrolled courses - userId: {userId}, courses: {courseList}")
            return {"courses": courseList}

        logging.info(f"Cache miss for enrolled courses, querying database - userId: {userId}")
        conn = request.app.state.db_instance.getDBconnection()
        cursor = conn.cursor()
        cursor.execute('SELECT c."CourseName" FROM "Course" c JOIN "UserCourse" uc ON uc."CourseId" = c."CourseId" WHERE uc."UserId" = %s', (userId, ))
        courses = cursor.fetchall()
        cursor.close()

        if not courses:
            logging.warning(f"No enrolled courses found - userId: {userId}")
            raise HTTPException(status_code=404, detail="No enrolled courses found")

        courseList = [course[0] for course in courses]
        await redis.hset(f"user:{userId}", "enrolledCourse", json.dumps(courseList))
        logging.info(f"Enrolled courses fetched from DB and cached - userId: {userId}, courses: {courseList}, count: {len(courseList)}")
        return {"courses": courseList}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error while fetching enrolled courses - userId: {userId}, error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while fetching enrolled courses"
        )
    finally:
        if conn:
            request.app.state.db_instance.releaseDBconnection(conn)



