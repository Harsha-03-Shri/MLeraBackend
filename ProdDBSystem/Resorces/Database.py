"""PostgreSQL connection pool manager.

Provides a SimpleConnectionPool for the application and exposes
methods to acquire/release connections and shut down the pool.
"""

import os
from psycopg2 import pool
import psycopg2.extras 
import logging

logging.basicConfig(level=logging.INFO, format="%(filename)s - %(levelname)s - %(message)s")
psycopg2.extras.register_uuid()

DB_NAME = str(os.getenv("DB_NAME", "postgres"))
DB_USER = str(os.getenv("DB_USER", "postgres"))
DB_PASS = str(os.getenv("DB_PASS", "password"))
DB_HOST = str(os.getenv("DB_HOST", "localhost"))
DB_PORT = int(os.getenv("DB_PORT", 5432))

class Database:
    """Manages a psycopg2 SimpleConnectionPool for PostgreSQL."""

    pool = None

    def __init__(self):
        """Initialize the connection pool and register UUID type support."""
        try:
            self.pool = pool.SimpleConnectionPool(
                minconn=1, maxconn=50,
                host=DB_HOST, database=DB_NAME,
                user=DB_USER, password=DB_PASS,
                port=DB_PORT
            )
            logging.info("DB pool created successfully")
        except Exception as e:
            logging.error(f"Failure creating DB Pool: {e}")

    def getDBconnection(self):
        """Get a connection from the pool.

        Returns:
            A psycopg2 connection object.
        """
        try:
            conn = self.pool.getconn()
            return conn
        except Exception as e:
            logging.error(f"Connection to DB Pool failed: {e}")
            raise
    
    def releaseDBconnection(self, conn):
        """Return a connection to the pool.
        
        Args:
            conn: Connection to return to the pool.
        """
        try:
            if conn:
                self.pool.putconn(conn)
        except Exception as e:
            logging.error(f"Failed to return connection to pool: {e}")

    def shutdownDBPool(self):
        """Close all connections in the pool."""
        try:
            if self.pool:
                self.pool.closeall()
                logging.info("Closed the DB pool")
        except Exception as e:
            logging.error(f"Failure trying to close the pool: {e}")




