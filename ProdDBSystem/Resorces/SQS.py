"""SQS client wrapper for sending messages to an AWS SQS queue.

Reads the queue URL from the SQS_QUEUE_URL environment variable and
provides an async interface for sending JSON messages.
"""

import boto3
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(filename)s - %(levelname)s - %(message)s")

QueueUrl = os.getenv("SQS_QUEUE_URL")


class SQS:
    """Wraps a boto3 SQS client for sending messages to a queue."""

    sqs = None

    def __init__(self):
        """Initialize the boto3 SQS client."""
        self.sqs = boto3.client("sqs", region_name="ap-south-1")

    def get_queue_url(self):
        """Return the SQS queue URL from environment configuration.

        Returns:
            The SQS queue URL string.
        """
        return QueueUrl

    async def send_message(self, QueueUrl: str, Message: str):
        """Send a message to the configured SQS queue.

        Args:
            QueueUrl: The URL of the SQS queue.
            Message: The message body string to send.

        Returns:
            The SQS send_message response dict.
        """
        try:
            response = self.sqs.send_message(
                QueueUrl=QueueUrl,
                MessageBody=Message
            )
            logging.info("Message sent to SQS queue: %s", QueueUrl)
            return response
        except Exception as e:
            logging.error(f"Error sending message to SQS: {e}")
            raise
