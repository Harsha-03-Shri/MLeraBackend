"""Redis connection pool manager.

Provides an async Redis connection pool and exposes methods
to acquire connections and shut down the pool.
"""

import redis.asyncio as redis
import os
import logging

logging.basicConfig(level=logging.INFO)

REDIS_HOST = str(os.getenv("REDIS_HOST", "localhost"))
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

class Redis:
    """Manages an async Redis ConnectionPool."""

    pool = None

    def __init__(self):
        """Initialize the async Redis connection pool."""
        try:
            self.pool = redis.ConnectionPool(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=0,
                max_connections=10,
                decode_responses=True
            )
            logging.info("Created redis pool")
        except Exception as e:
            logging.error(f"Failure creating Redis Pool: {e}")

    def getRedisconnection(self):
        """Return an async Redis client backed by the connection pool.

        Returns:
            An async redis.Redis client instance.
        """
        try:
            return redis.Redis(connection_pool=self.pool)
        except Exception as e:
            logging.error(f"Connection to Redis Pool failed: {e}")

    async def shutdownRedisPool(self):
        """Close all connections in the async Redis pool."""
        try:
            if self.pool:
                await self.pool.aclose()
                logging.info("Successfully closed the Redis pool")
        except Exception as e:
            logging.error(f"Failure trying to close the pool: {e}")
