# src/backend/utils/email_notifier.py
# Purpose: Universal email sender function with all parameters optional
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import HTTPException
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

def send_email(
    to: str = None,
    subject: str = None,
    body: str = None,
    attachment: str = None,
    from_email: str = None,
    from_password: str = None,
    smtp_server: str = None,
    smtp_port: int = None
):
    """
    Universal email sender function.
    Reads SMTP config from .env if not passed as parameters.
    """

    try:
        # Defaults (from .env if not provided)
        from_email = from_email or os.getenv("EMAIL_USER")
        from_password = from_password or os.getenv("EMAIL_PASS")
        smtp_server = smtp_server or os.getenv("SMTP_SERVER")
        smtp_port = smtp_port or int(os.getenv("SMTP_PORT"))

        if not to:
            raise ValueError("Recipient email (to) is required.")
        if not subject:
            subject = "No Subject"
        if not body:
            body = ""

        # Create message
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Optional text attachment
        if attachment:
            msg.attach(MIMEText(attachment, "plain"))

        # Setup server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(from_email, from_password)
        server.sendmail(msg["From"], msg["To"], msg.as_string())
        server.quit()

        print(f"📧 Email sent to {to} with subject '{subject}'")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")