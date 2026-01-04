import os
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
import logging

# Configure logging for better error tracing
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Load environment variables from .env file
load_dotenv()

# Database credentials and configuration loaded from environment variables
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_DRIVER = os.getenv("DB_DRIVER", "postgresql+asyncpg")

DB_ECHO = os.getenv("DB_ECHO", "False").lower() in ("true", "1", "yes")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_TIMEOUT = int(os.getenv("DB_TIMEOUT", "30"))

# If DATABASE_URL is not directly defined in .env, construct it using individual components
DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or f"{DB_DRIVER}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Create the asynchronous engine with connection pooling and timeout handling
try:
    engine = create_async_engine(
        DATABASE_URL,
        echo=DB_ECHO,  # Logs all SQL queries if True
        pool_size=DB_POOL_SIZE,  # Pool size for database connections
        max_overflow=DB_MAX_OVERFLOW,  # Max connections that can exceed pool_size
        connect_args={"timeout": DB_TIMEOUT},  # Connection timeout
        pool_pre_ping=True,  # Ensures the connections are valid before using them
    )
    logger.info(f"Successfully connected to database: {DATABASE_URL}")
except SQLAlchemyError as e:
    logger.error(f"Error creating database engine: {e}")
    raise Exception(f"Database connection failed: {e}")

# Use async_sessionmaker to create sessionmaker for async SQLAlchemy session
AsyncSessionLocal = async_sessionmaker(
    engine,  # The async engine created above
    class_=AsyncSession,  # The session class
    autoflush=False,  # To avoid flushing automatically
    autocommit=False,  # To manually commit transactions
    expire_on_commit=False,  # Don't expire objects after commit
)

# Base class for SQLAlchemy ORM models (for declarative base models)
Base = declarative_base()

# Dependency to retrieve a database session in FastAPI
# Ensures the session is properly closed after use
async def get_db():
    try:
        # Use async context manager to handle session lifecycle
        async with AsyncSessionLocal() as session:
            # Yield the session to the request handler
            yield session
    except SQLAlchemyError as e:
        logger.error(f"Error: while interacting with the database: {e}")
        raise HTTPException(status_code=500, detail=f"Database operation failed: {e}")