"""SMTP client module for sending emails via Gmail.

This module provides async email sending functionality using aiosmtplib.
It's used by the Lambda consumer to send notification emails to users.

Error Handling:
    Uses aiosmtplib.SMTPException for precise SMTP-specific error reporting
    instead of generic Exception, preserving full SMTP error context.
"""

import logging
import aiosmtplib
from email.message import EmailMessage
import os

logging.basicConfig(level=logging.INFO, format="%(filename)s - %(levelname)s - %(message)s")

GMAILFROM = os.getenv("GMAILFROM")
GMAILPASSWORD = os.getenv("GMAILPASSWORD")

async def send_email(email: str, subject: str, body: str):
    """Send an email using Gmail SMTP server.
    
    This async function sends an email via Gmail's SMTP server using TLS encryption.
    It's designed to be called from the Lambda function handler.
    
    Args:
        email: Recipient's email address
        subject: Email subject line
        body: Email body content (plain text)
        
    Returns:
        None
        
    Raises:
        aiosmtplib.SMTPException: Raised for all SMTP-specific failures including:
            - SMTPConnectError: Cannot connect to smtp.gmail.com:587
            - SMTPAuthenticationError: Invalid GMAILFROM or GMAILPASSWORD credentials
            - SMTPRecipientsRefused: Recipient email address rejected by server
            - SMTPSenderRefused: Sender address rejected by server
            Using SMTPException (instead of generic Exception) preserves the
            specific SMTP error code and server response for easier debugging.
        
    Environment Variables:
        GMAILFROM: Gmail sender email address
        GMAILPASSWORD: Gmail app password (not regular account password)
        
    Note:
        - Uses port 587 with STARTTLS for secure connection
        - Requires a Gmail app-specific password, not the regular account password
        - Gmail may block sign-ins without app passwords; generate one at myaccount.google.com
    """
    try:
        message = EmailMessage()
        message["To"] = email
        message["From"] = GMAILFROM
        message["Subject"] = subject
        message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname="smtp.gmail.com",
            port=587,
            username=GMAILFROM,
            password=GMAILPASSWORD,
            start_tls=True,
        )
    except aiosmtplib.SMTPException as e:
        logging.error(f"Error occurred while sending email to {email}: {e}")
        raise aiosmtplib.SMTPException(f"Failed to send email to {email}: {str(e)}")