"""Entry point for the ProdDBSystem FastAPI application.

Initializes the app with CORS middleware, registers all routers,
and manages startup/shutdown of database, Redis, and SQS connections.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Resorces import Database, Redis, SQS
from APIService.Routes.User.User import router as userRouter
from APIService.Routes.Course.Course import router as courseRouter
from APIService.Routes.Modules.Module import router as moduleRouter
from APIService.Routes.PracticeQuiz.PracticeQuiz import router as practiceQuizRouter
import logging
import uvicorn

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of resource pools.

    Initializes Database, Redis, and SQS instances on startup
    and cleanly shuts them down on application exit.

    Args:
        app: The FastAPI application instance.
    """
    try:
        app.state.db_instance = Database()
        app.state.redis_instance = Redis()
        app.state.sqs_instance = SQS()
        logging.info("Database, SQS and Redis pools initialized successfully")
    except Exception as e:
        logging.error(f"Failures while starting up the server: {e}")

    yield

    try:
        if app.state.db_instance:
            app.state.db_instance.shutdownDBPool()
        if app.state.redis_instance:
            await app.state.redis_instance.shutdownRedisPool()
        logging.info("Database and Redis pools closed successfully")
    except Exception as e:
        logging.error(f"Failures while shutting down the server: {e}")


app = FastAPI(lifespan=lifespan)

origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(userRouter)
app.include_router(courseRouter)
app.include_router(moduleRouter)
app.include_router(practiceQuizRouter)

@app.get("/health")
async def health_check():
    """Health check endpoint for ALB target group."""
    return {"status": "healthy"}

if __name__ == "__main__":
    try:
        uvicorn.run(
            "main:app",
            host="127.0.0.1",
            port=8080,
            reload=True
        )
    except Exception as e:
        logging.error(f"Failure while starting the server: {e}")
