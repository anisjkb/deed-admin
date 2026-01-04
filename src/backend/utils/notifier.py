# src/backend/utils/notifier.py
# Purpose: Send Email, Telegram & WhatsApp notifications
import os
import asyncio
from dotenv import load_dotenv
from telegram import Bot
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import HTTPException

load_dotenv()

# ---------------- Email ----------------
def send_email(subject, body, attachment=None, to=None):
    try:
        # Set up SMTP server and send email (example using Gmail SMTP)
        msg = MIMEMultipart()
        msg['From'] = os.getenv('EMAIL_USER')
        msg['To'] = to
        msg['Subject'] = "Password Reset Request"
        contents = [body]
        if attachment:
            contents.append(attachment)
        msg.attach(MIMEText(body, 'plain'))
        
        # Set up your SMTP server

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(os.getenv('EMAIL_USER'), os.getenv('EMAIL_PASS'))
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        print(f"📧 Email sent to {to}")
        server.quit()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to send email")
    
# Add functions to send the reset link and username.

def send_password_reset_email(email: str, reset_link: str):
    # Send the email with the password reset link
    try:
        # Set up SMTP server and send email (example using Gmail SMTP)
        msg = MIMEMultipart()
        msg['From'] = os.getenv('EMAIL_USER')
        msg['To'] = email
        msg['Subject'] = "Password Reset Request"
        body = f"Click the link to reset your password: {reset_link}"
        msg.attach(MIMEText(body, 'plain'))

        # Set up your SMTP server

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(os.getenv('EMAIL_USER'), os.getenv('EMAIL_PASS'))
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        print(f"📧 Email sent to {email}")
        server.quit()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to send reset email")

def send_username_email(email: str, username: str):
    # Send the username to the user's email
    try:
        msg = MIMEMultipart()
        msg['From'] = "no-reply@yourapp.com"
        msg['To'] = email
        msg['Subject'] = "Username Retrieval"
        body = f"Your username is: {username}"
        msg.attach(MIMEText(body, 'plain'))
        
        # Set up your SMTP server
        server = smtplib.SMTP('smtp.yourapp.com', 587)
        server.starttls()
        server.login("your_email", "your_password")
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        server.quit()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to send username email")

# ---------------- Telegram ----------------
async def send_telegram_async(pdf_path=None):
    token = os.getenv("TELEGRAM_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("❌ Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
        return

    bot = Bot(token=token)

    if pdf_path:
        with open(pdf_path, 'rb') as f:
            await bot.send_document(chat_id=chat, document=f, filename=os.path.basename(pdf_path))
            print("📱 Sent report via Telegram")
    else:
        await bot.send_message(chat_id=chat, text="✅ Telegram test successful from Agentic AI.")
        print("📨 Test message sent via Telegram.")

def send_telegram(pdf_path=None):
    asyncio.run(send_telegram_async(pdf_path))

# ---------------- WhatsApp via Twilio ----------------
def send_whatsapp(pdf_path, to_whatsapp=None):
    client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
    from_wh = os.getenv('TWILIO_WHATSAPP_FROM')  # 'whatsapp:+1415...'
    to_wh = to_whatsapp or os.getenv('WHATSAPP_TO')
    body = "📊 Your Agentic AI Trend Report is ready. Please check your email or web dashboard."

    # Twilio WhatsApp API does not support direct PDF file attachments
    message = client.messages.create(
        from_=from_wh,
        to=to_wh,
        body=body
    )
    print(f"📲 WhatsApp notification sent, SID: {message.sid}")