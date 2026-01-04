# src/backend/utils/crud.py
from sqlalchemy.orm import Session
from src.backend.models.user import User
from src.backend.models.refresh_token import RefreshToken

def get_all_users(db: Session):
    return db.query(User).all()

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, username: str, email: str, hashed_password: str):
    user = User(username=username, email=email, hashed_password=hashed_password)
    db.add(user); db.commit(); db.refresh(user)
    return user

def get_refresh_token(db: Session, token_hash: str):
    return db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

def add_refresh_token(db: Session, token: RefreshToken):
    db.add(token); db.commit(); db.refresh(token)
    return token