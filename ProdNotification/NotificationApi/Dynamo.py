"""DynamoDB database module for managing Users and Templates tables.

This module provides classes for interacting with DynamoDB tables:
- Database: Base connection to DynamoDB
- User: Operations on Users table (userId, channel, id, Name)
- Templates: Operations on Templates table (TemplateType, Channel, Subject, Body)
"""

import boto3
import logging
import uuid
import os

logging.basicConfig(level=logging.INFO)

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

class Database:
    """Manages DynamoDB connection and resource initialization.
    
    Attributes:
        DB: boto3 DynamoDB resource object
    """
    DB = None
    
    def __init__(self):
        """Initialize DynamoDB resource connection.
        
        On Fargate: uses IAM Task Role automatically (no credentials needed in code).
        Locally: reads from ~/.aws/credentials or AWS_* environment variables.
        Region is read from AWS_REGION env variable (default: us-east-1).
        
        Raises:
            Exception: If DynamoDB connection fails
        """
        try:
            self.DB = boto3.resource('dynamodb', region_name=AWS_REGION)
        except Exception as e:
            logging.error(f"Error occurred while creating DynamoDB connection: {e}")

class User():
    """Handles operations on the Users DynamoDB table.
    
    Table Schema:
        - Partition Key: userId (String)
        - Sort Key: channel (String)
        - Attributes: id (email address), Name
    
    Attributes:
        table: DynamoDB Table resource for Users table
    """
    table = None

    def __init__(self, db: Database):
        """Initialize User table connection.
        
        Args:
            db: Database instance with DynamoDB connection
        """
        self.table = db.DB.Table("Users")

    def create_user(self, user_id: uuid.UUID, Name: str, email: str):
        """Create a new user in the Users table.
        
        Args:
            user_id: Unique identifier for the user
            Name: User's full name
            email: User's email address
            
        Returns:
            None
            
        Raises:
            Exception: If DynamoDB put_item operation fails
        """
        try:
            self.table.put_item(
                Item={
                    'userId': user_id,
                    'channel': 'email',
                    'id': email,
                    'Name': Name,
                }
            )
            logging.info(f"User {user_id} created successfully.")
        except Exception as e:
            logging.error(f"Error occurred while creating user {user_id}: {e}")
    

    def getUser(self, user_id: uuid.UUID):
        """Retrieve user information from the Users table.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            dict: User data with keys 'Name' and 'Email', or None if not found
            Example: {"Name": "John Doe", "Email": "john@example.com"}
            
        Raises:
            Exception: If DynamoDB get_item operation fails
        """
        try:
            key = {'userId': user_id, 'channel': 'email'}
            response = self.table.get_item(Key=key)
            item = response.get('Item')

            if item:
                return {"Name": item.get('Name'), "Email": item.get('id')}
            else:
                logging.warning(f"User {user_id} not found.")
                return None
        except Exception as e:
            logging.error(f"Error occurred while retrieving user {user_id}: {e}")
            return None

class Templates():
    """Handles operations on the Templates DynamoDB table.
    
    Table Schema:
        - Partition Key: TemplateType (String)
        - Sort Key: Channel (String)
        - Attributes: Subject, Body
    
    Attributes:
        table: DynamoDB Table resource for Templates table
    """
    table = None

    def __init__(self, db: Database):
        """Initialize Templates table connection.
        
        Args:
            db: Database instance with DynamoDB connection
        """
        self.table = db.DB.Table("Templates")
    
    def getTemplate(self, TemplateType: str, Channel: str):
        """Retrieve notification template from the Templates table.
        
        Args:
            TemplateType: Type of template (e.g., 'ModuleCompletion', 'Welcome')
            Channel: Notification channel (e.g., 'email', 'apn', 'fcm')
            
        Returns:
            dict: Template data with keys 'Subject' and 'Body', or None if not found
            Example: {"Subject": "Welcome {Name}", "Body": "Hello {Name}..."}
            
        Raises:
            Exception: If DynamoDB get_item operation fails
        """
        try:
            key = {'TemplateType': TemplateType, 'Channel': Channel}
            response = self.table.get_item(Key=key)
            item = response.get('Item')

            if item:
                return {"Subject": item.get('Subject'), "Body": item.get('Body')}
            else:
                logging.warning(f"Template {TemplateType} for channel {Channel} not found.")
                return None
        except Exception as e:
            logging.error(f"Error occurred while retrieving template {TemplateType} for channel {Channel}: {e}")
            return None