from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, JSON, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, UTC
import os

# Create SQLite database engine
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./socratic.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    sessions = relationship("Session", back_populates="user")

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    started_at = Column(DateTime, default=lambda: datetime.now(UTC))
    concept_data = Column(JSON)  # Store current concept data
    next_q_idx = Column(Integer, default=0)
    hint_level = Column(Integer, default=0)
    
    user = relationship("User", back_populates="sessions")
    turns = relationship("Turn", back_populates="session")
    progress = relationship("Progress", back_populates="session", uselist=False)

class Turn(Base):
    __tablename__ = "turns"

    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))
    speaker = Column(String)  # "User" or "AI"
    text = Column(String)
    time_spent = Column(Float, nullable=True)  # Time spent on this turn in seconds
    
    session = relationship("Session", back_populates="turns")

class Progress(Base):
    __tablename__ = "progress"

    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id"), unique=True)
    questions_answered = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    concepts_covered = Column(JSON)  # List of concept titles
    times_per_question = Column(JSON)  # List of times in seconds
    
    session = relationship("Session", back_populates="progress")

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create all tables
def init_db():
    Base.metadata.create_all(bind=engine)