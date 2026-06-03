from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
from ..config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), default=1)
    filename = Column(String, nullable=False)
    original_filename = Column(String, default="")
    raw_text = Column(Text, default="")
    skills = Column(JSON, default=list)
    experience = Column(JSON, default=list)  # 工作经历
    projects = Column(JSON, default=list)    # 项目经历
    education = Column(JSON, default=list)
    personal_info = Column(JSON, default=dict)  # {name, phone, email, awards, certs}
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), default=1)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True, default=None)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class JobListing(Base):
    __tablename__ = "job_listings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    company = Column(String, default="")
    description = Column(Text, default="")
    requirements = Column(Text, default="")
    source = Column(String, default="manual")
    source_url = Column(String, default="")
    salary = Column(String, default="")
    city = Column(String, default="")
    location = Column(String, default="")
    posted_date = Column(String, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class MatchResult(Base):
    __tablename__ = "match_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    job_id = Column(Integer, ForeignKey("job_listings.id"))
    score = Column(Float, default=0.0)
    is_recommended = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class UserJobProfile(Base):
    __tablename__ = "user_job_profiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), default=1)
    desired_position = Column(String, default="")
    desired_salary = Column(String, default="")
    desired_cities = Column(JSON, default=list)
    skills_extra = Column(JSON, default=list)


def init_db():
    import os
    import sqlite3
    db_path = DATABASE_URL.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    # Migrate existing DB: add new columns if missing
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Resume new columns
        cursor.execute("PRAGMA table_info(resumes)")
        resume_cols = [row[1] for row in cursor.fetchall()]
        if 'projects' not in resume_cols:
            cursor.execute("ALTER TABLE resumes ADD COLUMN projects TEXT DEFAULT '[]'")
        if 'personal_info' not in resume_cols:
            cursor.execute("ALTER TABLE resumes ADD COLUMN personal_info TEXT DEFAULT '{}'")
        if 'original_filename' not in resume_cols:
            cursor.execute("ALTER TABLE resumes ADD COLUMN original_filename VARCHAR DEFAULT ''")
        # ChatMessage new column
        cursor.execute("PRAGMA table_info(chat_messages)")
        chat_cols = [row[1] for row in cursor.fetchall()]
        if 'resume_id' not in chat_cols:
            cursor.execute("ALTER TABLE chat_messages ADD COLUMN resume_id INTEGER")
        # JobListing new columns
        cursor.execute("PRAGMA table_info(job_listings)")
        job_cols = [row[1] for row in cursor.fetchall()]
        if 'posted_date' not in job_cols:
            cursor.execute("ALTER TABLE job_listings ADD COLUMN posted_date VARCHAR DEFAULT ''")
        conn.commit()
        conn.close()
    # ensure default user exists
    db = SessionLocal()
    if not db.query(User).first():
        db.add(User())
        db.commit()
    db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
