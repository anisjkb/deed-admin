# src/backend/monitoring.py
from datetime import datetime
import requests
from geoip2.database import Reader  # MaxMind GeoLite2 (free database)
from backend.model import User, UserActivityLog
from src.backend.utils.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import insert
import json
import math

# Initialize GeoIP reader (download GeoLite2 City DB and provide path)
GEOIP_DB_PATH = "GeoLite2-City.mmdb"
geo_reader = Reader(GEOIP_DB_PATH)

def get_geolocation(ip_address: str):
    try:
        response = geo_reader.city(ip_address)
        return response.country.name, response.city.name
    except:
        return None, None

def compute_risk_score(activity: dict) -> float:
    """
    Simple AI-driven risk scoring (production: replace with ML model)
    Factors considered:
    - Login success/failure
    - Geolocation vs usual location
    - Device fingerprint
    - Impossible travel
    """
    score = 0
    if not activity.get("login_success", True):
        score += 50  # failed login attempts are high risk

    # Geolocation anomaly (example: first time in a new country)
    usual_countries = activity.get("usual_countries", [])
    country = activity.get("geolocation_country")
    if country and country not in usual_countries:
        score += 30

    # Device anomaly
    usual_devices = activity.get("usual_devices", [])
    device = activity.get("device_info")
    if device and device not in usual_devices:
        score += 20

    # Time-based anomaly (non-business hours)
    hour = activity.get("timestamp").hour
    if hour < 6 or hour > 23:
        score += 5

    return min(score, 100)

def log_user_activity(db: Session, user: User, ip_address: str, device_info: str,
                      user_agent: str, login_success: bool, event_type: str = "login",
                      extra_info: dict = None):
    extra_info = extra_info or {}

    country, city = get_geolocation(ip_address)

    # Build activity dictionary
    activity = {
        "user_id": user.id,
        "ip_address": ip_address,
        "geolocation_country": country,
        "geolocation_city": city,
        "device_info": device_info,
        "user_agent": user_agent,
        "login_success": login_success,
        "timestamp": datetime.utcnow(),
        "event_type": event_type,
        "extra_info": extra_info,
        # Placeholder for risk scoring
        "usual_countries": extra_info.get("usual_countries", []),
        "usual_devices": extra_info.get("usual_devices", [])
    }

    risk_score = compute_risk_score(activity)

    db.execute(
        insert(UserActivityLog).values(
            user_id=user.id,
            ip_address=ip_address,
            geolocation_country=country,
            geolocation_city=city,
            device_info=device_info,
            user_agent=user_agent,
            login_success=login_success,
            timestamp=datetime.utcnow(),
            risk_score=risk_score,
            event_type=event_type,
            extra_info=json.dumps(extra_info)
        )
    )
    db.commit()
    return risk_score