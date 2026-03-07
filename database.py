import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime

# ─── Environment-Aware DB URL ─────────────────────────────────────────────────
# On AWS (Elastic Beanstalk): DATABASE_URL is set as an environment variable
#   e.g., postgresql://user:pass@rds-endpoint:5432/scamshield
# Locally: Falls back to SQLite for zero-config development
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./scam_shield.db"

# SQLAlchemy engine args differ between SQLite and PostgreSQL
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class MessageLog(Base):
    __tablename__ = "message_logs"
    id = Column(Integer, primary_key=True, index=True)
    original_message = Column(Text)
    detected_language = Column(String)
    comprehend_language = Column(String, nullable=True)   # Amazon Comprehend cross-check
    risk_score = Column(Integer)
    ai_base_score = Column(Integer, nullable=True)
    rule_boost = Column(Integer, nullable=True)
    scam_type = Column(String)
    psychological_trick = Column(String)
    model_used = Column(String, nullable=True)             # Which AI model was used
    confidence = Column(String, nullable=True)             # High / Medium / Low
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class HoneypotSession(Base):
    """Represents a honeypot engagement session with a scammer."""
    __tablename__ = "honeypot_sessions"
    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String(36), unique=True, index=True, nullable=False)  # UUID
    scan_log_id = Column(Integer, nullable=True)           # ref to message_logs.id
    scam_type = Column(String, nullable=True)
    risk_score = Column(Integer, nullable=True)
    source = Column(String, default="web")                 # "web" or "bot"
    status = Column(String, default="active")              # "active" | "closed"
    original_message = Column(Text, nullable=True)         # The scam msg that triggered this
    ai_honeypot_reply = Column(Text, nullable=True)        # AI-generated honeypot reply
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class HoneypotMessage(Base):
    """Individual message in a honeypot chat session."""
    __tablename__ = "honeypot_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String(36), index=True, nullable=False)
    sender = Column(String, nullable=False)                # "user" or "scammer"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)
    db_type = "PostgreSQL (AWS RDS)" if not DATABASE_URL.startswith("sqlite") else "SQLite (local)"
    print(f"[Database] ✅ Connected to {db_type}")
