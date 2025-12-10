"""
MELCO-Care Database Connection Manager
Handles SQLite database creation and session management
"""

import os
from pathlib import Path
from sqlmodel import SQLModel, Session, create_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_DIR = Path(__file__).parent
DATABASE_PATH = DATABASE_DIR / "melco_care.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine with connection pooling disabled for SQLite
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    connect_args={"check_same_thread": False}  # Required for SQLite with FastAPI
)


def create_db_and_tables():
    """Create all database tables"""
    # Import models to register them with SQLModel
    from database.models import (
        User, Hospital, Department, Doctor, 
        Appointment, ChatSession, ChatMessage
    )
    SQLModel.metadata.create_all(engine)
    print(f"✅ Database created at: {DATABASE_PATH}")


def get_session():
    """Get a database session (dependency injection for FastAPI)"""
    with Session(engine) as session:
        yield session


def get_db_session() -> Session:
    """Get a database session (direct usage)"""
    return Session(engine)


# Utility functions for common queries
def get_engine():
    """Return the database engine"""
    return engine


if __name__ == "__main__":
    # Run directly to create tables
    create_db_and_tables()
