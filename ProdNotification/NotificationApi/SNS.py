"""SNS (Simple Notification Service) module for publishing notification messages.

This module provides functionality to publish messages to AWS SNS topics
with message attributes for filtering and routing to appropriate SQS queues.
"""

import boto3
import logging 
import os
import json

logging.basicConfig(level=logging.INFO)

topic_arn = os.getenv("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:MyTopic")

class SNS:
    """Manages SNS client and message publishing operations.
    
    Attributes:
        SNS: boto3 SNS client object
    """
    SNS = None
    
    def __init__(self):
        """Initialize SNS client connection.
        
        Raises:
            Exception: If SNS client creation fails
        """
        try:
            self.SNS = boto3.client('sns')
        except Exception as e:
            logging.error(f"Error occurred while creating SNS connection: {e}")
    
    def publish(self, message: dict, messageAttributes: dict):
        """Publish a notification message to SNS topic.
        
        Args:
            message: Dictionary containing notification data (Subject, Body, Email)
            messageAttributes: Dictionary with message attributes for SNS filtering
                Example: {'Channel': {'DataType': 'String', 'StringValue': 'email'}}
                
        Returns:
            None
            
        Raises:
            Exception: If SNS publish operation fails
            
        Note:
            Message attributes are used by SNS filter policies to route messages
            to appropriate SQS queues (email, apn, fcm)
        """
        try:
            self.SNS.publish(
                TopicArn=topic_arn,
                Message=json.dumps(message),
                MessageAttributes=messageAttributes
            )
        except Exception as e:
            logging.error(f"Error occurred while publishing message to SNS: {e}")