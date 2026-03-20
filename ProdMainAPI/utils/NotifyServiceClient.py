"""Notification service client for user communications.

This module provides an async HTTP client to communicate with the notification microservice.
It handles user creation in the notification system and sends event-based notifications.
"""

import httpx
from fastapi import HTTPException
import os 
import logging

logging.basicConfig(level=logging.INFO, format="%(filename)s - %(levelname)s - %(message)s")


NotifyServiceURL = os.getenv("NOTIFICATION_SERVICE_URL")

class NotifyServiceClient:
    """Async HTTP client for notification service operations.
    
    This client manages user notification preferences and sends event-triggered
    notifications such as registration confirmations and module completions.
    """
    
    def __init__(self):
        """Initialize the notification service client with base URL."""
        self.client = httpx.AsyncClient(base_url=NotifyServiceURL)
    
    async def createUser(self, userId, name, email):
        """Create user profile in notification service.
        
        Args:
            userId: User's unique identifier
            name: User's full name
            email: User's email address for notifications
            
        Raises:
            HTTPException: If user creation fails
        """
        try:
            payload = {
                "userId": str(userId),
                "name": name,
                "email": email
            }
            response = await self.client.post("/api/v1/user/create", json=payload)
            response.raise_for_status()
                
        except httpx.HTTPStatusError as exc:
            logging.error(f"Failed to create user in Notify Service: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
    
    async def notifyRegistration(self, userId, event, quizPercentage=None):
        """Send event-based notification to user.
        
        Args:
            userId: User's unique identifier
            event: Type of event (e.g., 'Registration', 'ModuleCompletion')
            quizPercentage: Optional quiz score for module completion events
            
        Raises:
            HTTPException: If notification sending fails
        """
        try:
            payload = {
                "userId": str(userId),
                "TemplateType": event
            }
            
            if event == "ModuleCompletion":
                payload["QuizPercentage"] = quizPercentage

            response = await self.client.post("/notify/", json=payload)
            response.raise_for_status()
                
        except httpx.HTTPStatusError as exc:
            logging.error(f"Failed to send notification: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)