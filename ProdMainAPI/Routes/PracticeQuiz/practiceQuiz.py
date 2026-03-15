"""Practice quiz reporting API routes.

This module handles quiz-related operations, specifically retrieving
quiz performance reports for users.
"""

from fastapi import APIRouter, Depends, HTTPException
import logging 
import uuid
from utils.DBServiceClient import DBServiceClient
from utils.Auth import getCurrentUser

logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/practicequiz", tags=["PracticeQuiz"])

dbClient = DBServiceClient()


@router.post("/submit")
async def submitQuizAnswers(userId: uuid.UUID = Depends(getCurrentUser), score: str ):
    """Submit quiz answers for authenticated user.
    
    Args:
        userId: Authenticated user ID from JWT token
        score: string containing quiz score
        
    Returns:
        None
        
    Raises:
        HTTPException: If submission fails
    """
    try:
        logging.info(f"Submitting quiz score for user: {userId}")
        await dbClient.submitQuizScore(userId, score)

    except Exception as e:
        logging.error(f"Error submitting quiz answers: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/report")
async def getQuizReport(userId: uuid.UUID = Depends(getCurrentUser),moduleName: str):
    """Retrieve quiz performance report for authenticated user.
    
    Fetches comprehensive quiz statistics including scores, completion rates,
    and performance across all attempted quizzes.
    
    Args:
        userId: Authenticated user ID from JWT token
        
    Returns:
        dict: Quiz report with scores and statistics
        
    Raises:
        HTTPException: If report fetch fails
    """
    try:
        logging.info(f"Fetching quiz report for user: {userId}")
        report = await dbClient.getQuizReport(userId) 
        return report

    except Exception as e:
        logging.error(f"Error fetching quiz report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")