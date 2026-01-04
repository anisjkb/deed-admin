# utils/security.py
import os
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

# ---- JWT config (single source of truth) ----
# We accept SECRET_KEY for backward compatibility, but JWT_SECRET is canonical.
JWT_SECRET = (
    os.getenv("JWT_SECRET")
    or os.getenv("SECRET_KEY")  # fallback if old envs still set this
    or "change-this-secret-in-dev-only"
)
JWT_ALG = os.getenv("JWT_ALG") or os.getenv("ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))

# ---- Cookies / session flags (used by auth helpers) ----
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("1", "true", "yes")
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN") or None

# ---- Password hashing (bcrypt; switch to argon2 if you want) ----
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False

# ---- Access token creation (always signs with JWT_SECRET/JWT_ALG) ----
def create_access_token(payload: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = dict(payload)
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALG)