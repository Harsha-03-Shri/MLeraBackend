"""AWS Lambda handler for processing email notifications from SQS queue.

This Lambda function is triggered by SQS messages from the email queue.
It receives notification messages from SNS (via SQS), parses them,
and sends emails via SMTP using the smtp_client module.

Event Source: SQS Queue (email-queue)
Trigger: SQS messages with batch size of 10
Runtime: Python 3.11

Error Handling:
    Catches aiosmtplib.SMTPException from send_email for SMTP-specific failures.
    All other unexpected errors are caught by the outer Exception handler.
"""

import json
import logging
import asyncio
import aiosmtplib
from smtp_client import send_email

logging.basicConfig(level=logging.INFO)

def handler(event, context):
    """Lambda handler function for processing email notification messages.
    
    This function processes SQS messages containing email notifications.
    Each SQS message contains an SNS message with email details (recipient, subject, body).
    
    Args:
        event: Lambda event object containing SQS records
            Structure: {
                'Records': [
                    {
                        'body': '{"Message": "{\\"Email\\":\\"user@example.com\\",\\"Subject\\":\\"...\\",\\"Body\\":\\"...\\"}"}'  
                    }
                ]
            }
        context: Lambda context object with runtime information
        
    Returns:
        dict: Response with statusCode and body
            Success: {'statusCode': 200, 'body': 'Emails processed successfully'}
            Error: {'statusCode': 500, 'body': 'Error: <error message>'}
            
    Note:
        - Processes messages in batch (up to 10 messages per invocation)
        - Uses asyncio.run() to execute async send_email function
        - Skips messages with missing required fields (email, subject, body)
        - Catches aiosmtplib.SMTPException for SMTP-specific failures per record
        - Does not raise exceptions; returns error response instead
    """
    try:
        for record in event['Records']:
            body = json.loads(record['body'])
            message = json.loads(body['Message'])

            email = message.get('Email')
            subject = message.get('Subject')
            body_text = message.get('Body')

            if not email or not subject or not body_text:
                logging.warning(f"Missing required fields in message: {message}")
                continue

            asyncio.run(send_email(email, subject, body_text))
            logging.info(f"Email sent successfully to {email}.")
        
        return {'statusCode': 200, 'body': json.dumps('Emails processed successfully')}

    except aiosmtplib.SMTPException as e:
        logging.error(f"SMTP error while processing email message: {e}")
        return {'statusCode': 500, 'body': json.dumps(f'SMTP Error: {str(e)}')}
    except Exception as e:
        logging.error(f"Unexpected error while processing email message: {e}")
        return {'statusCode': 500, 'body': json.dumps(f'Error: {str(e)}')}
