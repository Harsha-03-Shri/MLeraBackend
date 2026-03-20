"""Utility functions for message formatting and template processing.

This module provides helper functions for formatting notification messages
by combining user data with message templates.
"""

from pydantic import BaseModel
import logging  
import uuid

logging.basicConfig(level=logging.INFO, format="%(filename)s - %(levelname)s - %(message)s")

class SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"

def formMessage(templateData: dict, UserData: dict):
    """Format notification message by combining template with user data.
    
    This function takes a message template with placeholders and user data,
    then formats the template by replacing placeholders with actual user values.
    
    Args:
        templateData: Dictionary containing 'Subject' and 'Body' template strings
            Example: {"Subject": "Hello {Name}", "Body": "Your score: {QuizPercentage}%"}
        UserData: Dictionary containing user information for template substitution
            Example: {"Name": "John", "Email": "john@example.com", "QuizPercentage": 85}
            
    Returns:
        dict: Formatted message with Subject, Body, and Email, or None if formatting fails
        Example: {"Subject": "Hello John", "Body": "Your score: 85%", "Email": "john@example.com"}
        
    Raises:
        Exception: If template formatting fails (e.g., missing placeholder values)
        
    Note:
        Uses Python's str.format() method for template substitution.
        All placeholders in template must have corresponding keys in UserData.
    """
    try:
        if templateData is None or UserData is None:
            raise HTTPException(status_code=500, detail="Template/User data missing")

        if not UserData.get("Email"):
            raise HTTPException(status_code=400, detail="User email missing")

        Subject = templateData.get("Subject", "No Subject")
        Body = templateData.get("Body", "No Body")

        Subject = Subject.format_map(SafeDict(UserData))
        Body = Body.format_map(SafeDict(UserData))

        return {
            "Subject": Subject,
            "Body": Body,
            "Email": UserData["Email"]
        }

    except Exception as e:
        logging.error(f"Error formatting message: {e}")
        raise

if __name__ == "__main__":
    pass