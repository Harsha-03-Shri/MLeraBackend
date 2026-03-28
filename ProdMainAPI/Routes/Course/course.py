"""Course management API routes.

This module handles course-related operations including course purchases
and progress tracking for enrolled courses.
"""

from fastapi import APIRouter, Depends, HTTPException
import logging 
from pydantic import BaseModel
import uuid
from utils.DBServiceClient import DBServiceClient
from utils.NotifyServiceClient import NotifyServiceClient
from utils.Auth import getCurrentUser

logging.basicConfig(level=logging.INFO, format="%(filename)s - %(levelname)s - %(message)s")

router = APIRouter(prefix="/course", tags=["Course"])

dbClient = DBServiceClient()
notifyClient = NotifyServiceClient()

class CoursePurchase(BaseModel):
    """Course purchase request model."""
    courseName: str

@router.post("/purchase")
async def coursePurchase(course: CoursePurchase, userId: uuid.UUID = Depends(getCurrentUser)):
    """Purchase a course for the authenticated user.
    
    Enrolls the user in the specified course and grants access to all modules.
    
    Args:
        course: Course purchase details
        userId: Authenticated user ID from JWT token
        
    Returns:
        dict: Success message with course name
        
    Raises:
        HTTPException: If purchase fails
    """
    try:
        logging.info(f"User {userId} is purchasing course: {course.courseName}")
        await dbClient.purchaseCourse(userId, course.courseName)
        await notifyClient.notifyRegistration(userId, "CoursePurchase", CourseName=course.courseName)
        return {"message": f"Course '{course.courseName}' purchased successfully by user {userId}"}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error purchasing course: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/progress")
async def getCourseProgress(courseName: str, userId: uuid.UUID = Depends(getCurrentUser)):
    """Fetch course progress statistics for authenticated user.
    
    Returns the number of modules completed, in progress, and yet to start
    across all enrolled courses.
    
    Args:
        userId: Authenticated user ID from JWT token
        courseName: course name to filter progress by specific course
        
    Returns:
        dict: Progress statistics with module counts
        
    Raises:
        HTTPException: If progress fetch fails
    """
    try:
        logging.info(f"Fetching course progress for user: {userId}")
        progress = await dbClient.getCourseProgress(userId,courseName) 
        return progress

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching course progress: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
        

@router.get("/enrolled")
async def getEnrolledCourses(userId: uuid.UUID = Depends(getCurrentUser)):
    """Get all courses that are currently enrolled by the user.

    Returns a list of courses where the user has purchased access.

    Args:
        userId: Authenticated user ID from JWT token

    Returns:
        dict: List of enrolled course names

    Raises:
        HTTPException: If enrolled courses fetch fails
    """
    try:
        logging.info(f"Fetching enrolled courses for user: {userId}")
        courses = await dbClient.getEnrolledCourses(userId)
        return {"courses": courses}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching enrolled courses: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
