# src/backend/utils/email_notifier.py
import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "smtp").lower()

def send_email(
    to: str,
    subject: str = "",
    body: str = "",
):
    """
    Universal email sender.
    - Railway → HTTPS (Resend)
    - VPS → SMTP (Gmail / any)
    """

    try:
        if EMAIL_PROVIDER == "resend":
            _send_resend(to, subject, body)
        else:
            _send_smtp(to, subject, body)

    except Exception as e:
        print(f"❌ Email error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Email service is temporarily unavailable. Please try again later."
        )


# ─────────────────────────────────────────────────────────
# RESEND (HTTPS — Railway safe)
# ─────────────────────────────────────────────────────────
def _send_resend(to: str, subject: str, body: str):
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("EMAIL_FROM", "onboarding@resend.dev")

    if not api_key:
        raise RuntimeError("RESEND_API_KEY not set")

    res = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": from_email,
            "to": [to],
            "subject": subject,
            "text": body,
        },
        timeout=10,
    )

    if res.status_code >= 400:
        raise RuntimeError(f"Resend error: {res.text}")

    print(f"📧 Email sent via Resend to {to}")


# ─────────────────────────────────────────────────────────
# SMTP (VPS / Local)
# ─────────────────────────────────────────────────────────
def _send_smtp(to: str, subject: str, body: str):
    from_email = os.getenv("EMAIL_USER")
    from_password = os.getenv("EMAIL_PASS")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not all([from_email, from_password, smtp_server]):
        raise RuntimeError("SMTP credentials not configured")

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
    server.starttls()
    server.login(from_email, from_password)
    server.sendmail(from_email, to, msg.as_string())
    server.quit()

    print(f"📧 Email sent via SMTP to {to}")