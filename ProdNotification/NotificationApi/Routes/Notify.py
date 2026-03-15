"""Notification API routes for sending notifications to users.

This module defines the FastAPI routes for the notification service.
It handles incoming notification requests, retrieves user and template data,
formats messages, and publishes them to SNS.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from Dynamo import User, Templates
from typing import Optional
from pydantic import BaseModel
import logging  
from Utils.utils import formMessage
import uuid

logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/notify", tags=["notifications"])

class Notify(BaseModel):
    """Request model for notification endpoint.
    
    Attributes:
        user_id: UUID of the user to send notification to
        TemplateType: Type of notification template (e.g., 'ModuleCompletion', 'Welcome')
        QuizPercentage: Optional quiz score percentage (required for ModuleCompletion)
    """
    userId: uuid.UUID
    TemplateType: str
    QuizPercentage: Optional[int] = None


@router.post("/")
async def notify_user(notify: Notify, request: Request):
    """Send notification to a user via SNS.
    
    This endpoint orchestrates the notification process:
    1. Retrieves user data from DynamoDB
    2. Fetches appropriate message template
    3. Formats message with user data
    4. Publishes message to SNS topic
    
    Args:
        notify: Notification request containing user_id, TemplateType, and optional data
        request: FastAPI request object with app state (db, sns connections)
        
    Returns:
        dict: Success response (implicitly returns 200 OK)
        
    Raises:
        HTTPException 400: If required fields are missing (e.g., QuizPercentage for ModuleCompletion)
        HTTPException 500: If message formatting or SNS publishing fails
        
    Example:
        POST /api/v1/notify/
        {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "TemplateType": "ModuleCompletion",
            "QuizPercentage": 85
        }
    """
    try: 
        userId = str(notify.userId)

        user = User(request.app.state.db)
        UserData = user.getUser(userId)

        if notify.TemplateType == "ModuleCompletion":

            if notify.QuizPercentage is None:
                logging.warning(f"QuizPercentage is required for TemplateType 'ModuleCompletion' for user {userId}.")
                raise HTTPException(
                    status_code=400,
                    detail=f"QuizPercentage is required for TemplateType 'ModuleCompletion'"
                )

            UserData['QuizPercentage'] = notify.QuizPercentage

        template = Templates(request.app.state.db) 
        templateData = template.getTemplate(notify.TemplateType, "email")

        message = formMessage(templateData, UserData)

        if message is None:
            logging.warning(f"Message formatting returned None for user {userId} and template {notify.TemplateType}.")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to format message for user {userId}"
            )

        message['Email'] = UserData.get('Email')
        try:
            messageAttributes = {
                'Channel': {
                    'DataType': 'String',
                    'StringValue': "email"
                }
            }
            request.app.state.sns.publish(message,messageAttributes)
            logging.info(f"Notification sent successfully for user {userId}.")

        except Exception as e:
            logging.error(f"Error occurred while publishing message to SNS for user {userId}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred while sending the notification for user {userId}"
            )

        
    except Exception as e:
        logging.error(f"Error occurred while processing notification for user {userId}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing the notification for user {userId}"
        )