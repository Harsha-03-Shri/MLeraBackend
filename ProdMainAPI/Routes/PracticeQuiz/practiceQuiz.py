"""Practice quiz reporting API routes.

This module handles quiz-related operations, specifically retrieving
quiz performance reports for users.
"""

from fastapi import APIRouter, Depends, HTTPException
import logging 
from pydantic import BaseModel
import uuid
from utils.DBServiceClient import DBServiceClient
from utils.Auth import getCurrentUser

logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/practicequiz", tags=["PracticeQuiz"])

dbClient = DBServiceClient()

class QuizSubmission(BaseModel):
    """Quiz submission request model."""
    moduleName: str
    score: int

@router.post("/submit")
async def submitQuizAnswers(submission: QuizSubmission, userId: uuid.UUID = Depends(getCurrentUser)):
    """Submit quiz answers for authenticated user.
    
    Args:
        submission: QuizSubmission containing moduleName and score
        userId: Authenticated user ID from JWT token
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If submission fails
    """
    try:
        logging.info(f"Submitting quiz score for user: {userId}")
        await dbClient.submitQuizAnswers(userId, submission.moduleName, submission.score)
        return {"message": "Quiz submitted successfully"}

    except Exception as e:
        logging.error(f"Error submitting quiz answers: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/report")
async def getQuizReport(moduleName: str, userId: uuid.UUID = Depends(getCurrentUser)):
    """Retrieve quiz performance report for authenticated user.
    
    Fetches comprehensive quiz statistics including scores, completion rates,
    and performance across all attempted quizzes.
    
    Args:
        moduleName: Name of the module for which to fetch reports
        userId: Authenticated user ID from JWT token
        
    Returns:
        dict: Quiz report with scores and statistics
        
    Raises:
        HTTPException: If report fetch fails
    """
    try:
        logging.info(f"Fetching quiz report for user: {userId}, module: {moduleName}")
        report = await dbClient.getQuizReport(userId, moduleName) 
        return report

    except Exception as e:
        logging.error(f"Error fetching quiz report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")