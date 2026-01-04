# src/backend/utils/logger.py
from fastapi import Request
from sqlalchemy.orm import Session
from src.backend.models.user_activity_log import UserActivityLog
from src.backend.utils.database import get_db

async def log_user_activity(request: Request, event_type="access"):
    # Skip logging for static files (e.g., images, css, js)
    if request.url.path.startswith('/static/'):
        return

    # Check if the request has an Authorization header to identify authenticated users
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return  # Skip logging if there's no Authorization header

    # Get user info from the request state (after attaching user via middleware)
    user = getattr(request.state, "user", None)
    if not user:
        return  # If there's no user object, skip logging

    db = next(get_db())  # Get the database session
    ip = request.client.host if request.client else "0.0.0.0"  # Get the client's IP address

    # Create a new user activity log entry
    log = UserActivityLog(
        user_id=user.id,
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),  # User agent from headers
        device_info="unknown",  # Placeholder for device info, can be updated as needed
        event_type=event_type  # Type of event (e.g., access, login, etc.)
    )

    # Save the log entry in the database
    db.add(log)
    db.commit()