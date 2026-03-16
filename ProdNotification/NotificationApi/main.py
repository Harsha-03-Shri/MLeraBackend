"""Main FastAPI application for the Notification API service.

This is the entry point for the notification service running on AWS Fargate.
It initializes AWS service connections (SNS, DynamoDB), configures CORS,
and sets up API routes for handling notification requests from the main API server.

The service receives notification requests via ALB, processes them, and publishes
messages to SNS which then routes them to appropriate SQS queues for Lambda consumers.
"""

from fastapi import FastAPI
import logging
import uvicorn 
from SNS import SNS
from Dynamo import Database
from fastapi.middleware.cors import CORSMiddleware
from Routes.Notify import router as notify_router
from Routes.user import router as user_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Notification API",
    description="Scalable notification service using AWS Fargate, SNS, and DynamoDB",
    version="1.0.0"
)

### CORS

origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

## Initialize services
@app.on_event("startup")
async def startup():
    """Initialize AWS service connections on application startup.
    
    This function runs once when the FastAPI application starts.
    It creates connections to SNS and DynamoDB and stores them in app state
    for use across all request handlers.
    
    Raises:
        Exception: If any AWS service connection fails
    """
    try:
        sns = SNS()
        db = Database()
        
        app.state.sns = sns
        app.state.db = db

        logging.info("Services initialized successfully.")
    except Exception as e:
        logging.error(f"Error during service startup of the server: {e}")

## Health check for ALB
@app.get("/health")
async def health_check():
    """Health check endpoint for Application Load Balancer.
    
    This endpoint is used by the ALB to determine if the Fargate task is healthy
    and ready to receive traffic. The ALB will route traffic only to healthy targets.
    
    Returns:
        dict: Status indicating the service is healthy
        Example: {"status": "healthy"}
    """
    return {"status": "healthy"}

## Include routers
app.include_router(notify_router, prefix="/notify", tags=["notifications"])
app.include_router(user_router, prefix="/api/v1", tags=["User"])

###
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)