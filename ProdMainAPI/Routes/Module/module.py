"""Module progress tracking API routes.

This module handles learning module operations including progress updates,
module completion, and resume functionality.
"""

from fastapi import APIRouter, Depends, HTTPException
import logging 
from pydantic import BaseModel, Field
from typing import Optional
import uuid
from utils.DBServiceClient import DBServiceClient
from utils.NotifyServiceClient import NotifyServiceClient
from utils.Auth import getCurrentUser

logging.basicConfig(level=logging.INFO, format="%(filename)s - %(levelname)s - %(message)s")

router = APIRouter(prefix="/module", tags=["Module"])

dbClient = DBServiceClient()
notifyClient = NotifyServiceClient()

class ModuleProgress(BaseModel):
    """Module progress update request model."""
    ModuleName: str
    PageName: str

class ModuleCompletion(BaseModel):
    """Module completion request model."""
    ModuleName: str
    QuizPercentage: float = Field(ge=0, le=100)

@router.post("/update") 
async def updateModuleProgress(module: ModuleProgress, userId: uuid.UUID = Depends(getCurrentUser)):
    """Update user's progress within a module.
    
    Records the current page/section the user is studying to enable
    resume functionality.
    
    Args:
        module: Module progress details
        userId: Authenticated user ID from JWT token
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If progress update fails
    """
    try:
        logging.info(f"Updating progress for user {userId} on module: {module.ModuleName}")
        await dbClient.updateModuleProgress(userId, module.ModuleName, module.PageName)
        return {"message": f"Progress for module '{module.ModuleName}' updated successfully for user {userId}"}

    except Exception as e:
        logging.error(f"Error updating module progress: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/complete")
async def completeModule(module: ModuleCompletion, userId: uuid.UUID = Depends(getCurrentUser)):
    """Mark a module as completed with quiz score.
    
    Records module completion, stores quiz score, and triggers a
    completion notification email to the user.
    
    Args:
        module: Module completion details including quiz score
        userId: Authenticated user ID from JWT token
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If module completion fails
    """
    try:
        logging.info(f"Completing module for user {userId} on module: {module.ModuleName}")

        await dbClient.completeModule(userId, module.ModuleName, module.QuizPercentage)
        await notifyClient.notifyRegistration(userId, "ModuleCompletion", QuizPercentage=module.QuizPercentage, ModuleName=module.ModuleName)

        return {"message": f"Module '{module.ModuleName}' completed successfully for user {userId}"}

    except Exception as e:
        logging.error(f"Error completing module: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/resume")
async def resumeModule(moduleName: str, userId: uuid.UUID = Depends(getCurrentUser)):
    """Get the last accessed page in a module for resume functionality.
    
    Retrieves the last page the user was studying to allow them to
    continue from where they left off.
    
    Args:
        moduleName: Name of the module to resume
        userId: Authenticated user ID from JWT token
        
    Returns:
        dict: Last page name accessed
        
    Raises:
        HTTPException: If resume data fetch fails
    """
    try:
        logging.info(f"Resuming module for user {userId} on module: {moduleName}")
        lastPage = await dbClient.getModuleProgress(userId, moduleName)
        return {"lastPage": lastPage}

    except Exception as e:
        logging.error(f"Error resuming module: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
