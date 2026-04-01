"""Main FastAPI application entry point.

This module initializes the FastAPI application, configures CORS middleware,
and registers all API route handlers for the learning management system.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from Routes.User.user import router as user_router
from Routes.Course.course import router as course_router
from Routes.Module.module import router as module_router
from Routes.PracticeQuiz.practiceQuiz import router as quiz_router

logging.basicConfig(level=logging.INFO, format="%(filename)s - %(levelname)s - %(message)s")

app = FastAPI(
    title="Learning Management System API",
    description="Main API Gateway for LMS platform",
    version="1.0.0"
)

origins = ["*"]  

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(user_router)
app.include_router(course_router)
app.include_router(module_router)
app.include_router(quiz_router)

@app.get("/health")
async def health_check():
    """Health check endpoint for ALB target group."""
    return {"status": "healthy"}

if __name__ == "__main__":
    logging.info("Starting the FastAPI application...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)