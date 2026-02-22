import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Default to a local PostgreSQL instance; can be overridden via DATABASE_URL env var
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://scraper:secret@localhost:5433/scraper_jobs')

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Yield a SQLAlchemy session; to be used with context manager or FastAPI style dependencies."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
