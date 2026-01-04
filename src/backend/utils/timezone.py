# src/backend/utils/timezone.py
from __future__ import annotations

import os
import logging
from datetime import datetime, date
from dotenv import load_dotenv

# For Python 3.9+ you could use zoneinfo (built-in) instead of pytz
# from zoneinfo import ZoneInfo
import pytz

# -----------------------------------------------------------------------------
# Load environment variables
# -----------------------------------------------------------------------------
load_dotenv()

# Default to Dhaka time zone if not set in .env
_TZ_ENV = os.getenv("TIMEZONE", "Asia/Dhaka")

# -----------------------------------------------------------------------------
# Configure local timezone with fallback
# -----------------------------------------------------------------------------
try:
    LOCAL_TZ = pytz.timezone(_TZ_ENV)
    # If using zoneinfo in the future:
    # LOCAL_TZ = ZoneInfo(_TZ_ENV)
except Exception as exc:
    logging.getLogger(__name__).warning(
        "Invalid TIMEZONE '%s' in environment; falling back to Asia/Dhaka. Error: %s",
        _TZ_ENV,
        exc
    )
    LOCAL_TZ = pytz.timezone("Asia/Dhaka")
    # Or if using zoneinfo:
    # LOCAL_TZ = ZoneInfo("Asia/Dhaka")

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
def now_local() -> datetime:
    """
    Return the current time as a timezone-aware datetime in the configured local timezone.
    """
    return datetime.now(LOCAL_TZ) # 2025-10-04 13:40:15+06:00


def today_local() -> date:
    """
    Return the current date in the configured local timezone.
    """
    return now_local().date() # 2025-10-04


def now_str(fmt: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    """
    Return the current local time as a nicely formatted string.

    Default Example: "2025-10-04 14:25:37 +06"
    """
    return now_local().strftime(fmt) # '2025-10-04 13:40:15 +06'


def now_local_format_dtTime() -> str:
    """
    Return current local time in the format:
    'DD-Mon-YYYY h:MMAM/PM'
    Example: '04-Oct-2025 1:40PM'
    """
    dt = now_local()
    return dt.strftime("%d-%b-%Y ") + dt.strftime("%I:%M%p").lstrip("0")