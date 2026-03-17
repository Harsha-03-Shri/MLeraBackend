"""Database service client for user and course data operations.

This module provides an async HTTP client to communicate with the database microservice.
It handles all CRUD operations related to users, courses, modules, and quiz data.
"""

import httpx
from fastapi import HTTPException
import os 
import logging

logging.basicConfig(level=logging.INFO)


DBServiceURL = os.getenv("DB_SERVICE_URL")

class DBServiceClient:
    """Async HTTP client for database service operations.
    
    This client manages all interactions with the database microservice,
    including user management, course purchases, progress tracking, and quiz reports.
    """
    
    def __init__(self):
        """Initialize the database service client with base URL."""
        self.client = httpx.AsyncClient(base_url=DBServiceURL)
        
    async def purchaseCourse(self, userId, courseName):
        """Record a course purchase for a user.
        
        Args:
            userId: User's unique identifier
            courseName: Name of the course being purchased
            
        Raises:
            HTTPException: If the purchase operation fails
        """
        try:
            payload = {
                "userId": str(userId),
                "courseName": courseName
            }
            response = await self.client.post("/course/purchase", json=payload)
            response.raise_for_status()
                
        except httpx.HTTPStatusError as exc:
            logging.error(f"Failed to purchase course: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)

    async def registerUser(self, name, phone, email, password,profession):
        """Register a new user in the database.
        
        Args:
            name: User's full name
            phone: User's phone number
            email: User's email address
            password: User's hashed password
            
        Returns:
            str: Newly created user ID
            
        Raises:
            HTTPException: If registration fails
        """
        try:
            payload = {
                "Name": name,
                "Profession": profession,
                "Phone": phone,
                "Email": email,
                "Password": password
            }
            logging.info(f"DBUrl:{DBServiceURL}")
            response = await self.client.post("/user/register", json=payload)
            response.raise_for_status()
            return response.json().get("userId")

        except httpx.HTTPStatusError as exc:
            logging.error(f"Failed to register user: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)

    async def loginUser(self, email, password):
        """Authenticate user credentials and retrieve user ID.
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            str: User ID if authentication successful
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            payload = {
                "email": email,
                "password": password
            }

            response = await self.client.post("/user/login", json=payload)
            response.raise_for_status()
            return response.json().get("userId")

        except httpx.HTTPStatusError as exc:
            logging.error(f"Failed to login user: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)


    async def getUserProfile(self, userId):
        """Fetch user profile information.
        
        Args:
            userId: User's unique identifier
            
        Returns:
            dict: User profile data including name, email, and enrolled courses
            
        Raises:
            HTTPException: If profile fetch fails
        """
        try:
            response = await self.client.get(f"/user/profile/{userId}")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as exc:
            logging.error(f"Failed to fetch user profile: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)     
    
    async def getQuizReport(self, userId,moduleName):
        """Retrieve quiz performance report for a user.
        
        Args:
            userId: User's unique identifier
            moduleName: Name of the module for which to fetch reports
            
        Returns:
            dict: Quiz report with scores and completion status
            
        Raises:
            HTTPException: If report fetch fails
        """
        try:
            response = await self.client.get(f"/practiceQuiz/report/{userId}/{moduleName}")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as exc:
            logging.error(f"Failed to fetch quiz report: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)

    
    async def submitQuizAnswers(self, userId, moduleName, score):
        """Submit quiz answers and score for a user.
        
        Args:
            userId: User's unique identifier
            moduleName: Name of the module
            score: Quiz score to be recorded
        
        """
        try:
            payload = {
                "userId": str(userId),
                "moduleName": moduleName,
                "score": score
            }
            response = await self.client.post("/practiceQuiz/submit", json=payload)
            response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            logging.error(f"Failed to submit quiz answers: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)


    async def getCourseProgress(self, userId,courseName):
        """Get overall course progress statistics for a user.
        
        Args:
            userId: User's unique identifier
            courseName: Name of the course for which to fetch progress
            
        Returns:
            dict: Progress data including completed, in-progress, and pending modules
            
        Raises:
            HTTPException: If progress fetch fails
        """
        try:
            response = await self.client.get(f"/course/progress/{userId}/{courseName}")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as exc:
            logging.error(f"Failed to fetch course progress: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
    
    async def updateModuleProgress(self, userId, moduleName, pageName):
        """Update user's progress within a specific module.
        
        Args:
            userId: User's unique identifier
            moduleName: Name of the module being studied
            pageName: Current page/section within the module
            
        Raises:
            HTTPException: If progress update fails
        """
        try:
            payload = {
                "userId": str(userId),
                "moduleName": moduleName,
                "Page": pageName
            }
            response = await self.client.post("/module/update", json=payload)
            response.raise_for_status()
                
        except httpx.HTTPStatusError as exc:
            logging.error(f"Failed to update module progress: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)

    async def completeModule(self, userId, moduleName, quizPercentage):
        """Mark a module as completed with quiz score.
        
        Args:
            userId: User's unique identifier
            moduleName: Name of the completed module
            quizPercentage: Quiz score percentage (0-100)
            
        Raises:
            HTTPException: If module completion fails
        """
        try:
            payload = {
                "userId": str(userId),
                "moduleName": moduleName,
                "QuizPercentage": quizPercentage
            }
            response = await self.client.post("/module/complete", json=payload)
            response.raise_for_status()
                
        except httpx.HTTPStatusError as exc:
            logging.error(f"Failed to complete module: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
    
    async def getModuleProgress(self, userId, moduleName):
        """Retrieve the last accessed page in a module for resume functionality.
        
        Args:
            userId: User's unique identifier
            moduleName: Name of the module
            
        Returns:
            str: Last page name accessed by the user
            
        Raises:
            HTTPException: If progress fetch fails
        """
        try:
            response = await self.client.get(f"/module/resume/{userId}/{moduleName}")
            response.raise_for_status()
            return response.json().get("lastPage")

        except httpx.HTTPStatusError as exc:
            logging.error(f"Failed to fetch module progress: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)