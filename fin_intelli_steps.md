
# Fin_Intelli Project Setup & Token Management

## Overview
This document outlines the setup and resolution steps for the "fin_intelli" project, which uses FastAPI, PostgreSQL, JWT authentication, and refresh token management. The system incorporates AI-driven monitoring, geolocation tracking, and proper token hashing for security.

## Table of Contents
1. [Project Setup](#project-setup)
2. [Model Definitions](#model-definitions)
3. [Token Management](#token-management)
4. [Login and Refresh Token Implementation](#login-and-refresh-token-implementation)
5. [Geolocation Handling](#geolocation-handling)
6. [Error Handling](#error-handling)
7. [Security Best Practices](#security-best-practices)
8. [Steps to Run the Project](#steps-to-run-the-project)
9. [Troubleshooting](#troubleshooting)

---

## Project Setup
- **FastAPI** is the framework used for the backend development.
- **PostgreSQL** is used for data storage.
- **JWT Tokens** for user authentication and authorization.
- **Geolocation** is tracked during login and stored in the `user_activity_logs` table.
- **AI-driven monitoring** checks for IP/device anomalies in refresh token operations.

### Dependencies
1. FastAPI
2. Uvicorn (ASGI server)
3. SQLAlchemy (for ORM)
4. psycopg2 (PostgreSQL adapter)
5. passlib (password hashing)
6. JWT (for token encoding/decoding)
7. dotenv (for environment variable management)

---

## Model Definitions

### User Model
Defines the user table with basic fields like username, email, password, active status, and role (admin/user).

```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
```

### Refresh Token Model
The `refresh_tokens` table stores the hashed refresh token, device information, IP address, and expiration details.

```python
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False)
    device_info = Column(String(255), default="Unknown")
    ip_address = Column(String(50), default="0.0.0.0")
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    user = relationship("User", back_populates="refresh_tokens")
```

### User Activity Log Model
Logs user events with fields like IP address, device information, geolocation, and risk score.

```python
class UserActivityLog(Base):
    __tablename__ = "user_activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    event_type = Column(String)
    ip_address = Column(String)
    device_info = Column(String)
    risk_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="activity_logs")
```

---

## Token Management

### Access Token
The access token is a short-lived JWT used to authenticate users. It has an expiration time, usually set to 15 minutes.

```python
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

### Refresh Token
The refresh token is stored in the `refresh_tokens` table, hashed with a secure random token.

```python
def create_refresh_token(db: Session, user: User, request: Request):
    random_token = secrets.token_urlsafe(64)
    hashed_token = hashlib.sha256(random_token.encode()).hexdigest()
    device_info = request.headers.get("user-agent", "Unknown")
    ip_address = request.client.host
    expires_at = datetime.utcnow() + timedelta(days=30)
    refresh_token_db = RefreshToken(
        user_id=user.id,
        token_hash=hashed_token,
        device_info=device_info,
        ip_address=ip_address,
        expires_at=expires_at
    )
    db.add(refresh_token_db)
    db.commit()
    db.refresh(refresh_token_db)
    return random_token
```

---

## Login and Refresh Token Implementation

### Login Endpoint
The login endpoint authenticates the user and generates both access and refresh tokens.

```python
@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token_expires = timedelta(minutes=15)
    access_token = create_access_token(
        data={"sub": user.username, "role": "admin" if user.is_admin else "user"},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(db, user, request)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": "admin" if user.is_admin else "user"
    }
```

---

## Geolocation Handling

Geolocation is logged in the `user_activity_logs` table using the IP address and device info.

```python
class UserActivityLog(Base):
    __tablename__ = "user_activity_logs"
    ...
    geolocation_country = Column(String(50))
    geolocation_city = Column(String(50))
    ...
```

---

## Error Handling

Make sure you handle cases like invalid credentials, expired tokens, and invalid geolocation:

```python
@app.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token}
```

---

## Security Best Practices

1. **Store Passwords Securely**: Always hash passwords with a strong algorithm like bcrypt.
2. **Use HTTP-Only Cookies**: For refresh tokens, use HTTP-only cookies to reduce risk from XSS attacks.
3. **Secure Random Token Generation**: Use `secrets.token_urlsafe(64)` to generate secure tokens.
4. **Token Expiry and Revocation**: Set short expiration times for access tokens and allow manual revocation of refresh tokens.

---

## Steps to Run the Project

1. Clone the repository and set up the virtual environment:
   ```
   python -m venv env
   source env/bin/activate  # Linux/MacOS
   .\env\Scriptsctivate  # Windows
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the FastAPI server:
   ```
   uvicorn src.backend.app:app --reload
   ```

4. Open the application in a web browser at `http://127.0.0.1:8000`.

---

## Troubleshooting

1. **Error: `TypeError: 'geolocation' is an invalid keyword argument for RefreshToken`**
   - Solution: Ensure `geolocation` is handled in the `user_activity_logs` table, not the `refresh_tokens` table.

2. **Error: `SyntaxError: Unexpected token`**
   - Solution: Make sure all responses from the backend are in valid JSON format. Check if any raw string is being sent where JSON is expected.

---

**End of Document**

