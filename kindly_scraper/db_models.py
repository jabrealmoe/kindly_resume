from .db import Base
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.dialects.postgresql import ARRAY

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=True)
    location = Column(String, nullable=True)
    link = Column(String, unique=True, nullable=False)
    query = Column(String, nullable=True)
    posted_date = Column(String, nullable=True)
    full_description = Column(Text, nullable=True)
    embedding = Column(ARRAY(Float), nullable=True)  # pgvector‑style embedding
    company_url = Column(String, nullable=True)
    is_workday = Column(Boolean, default=False)
    applied_at = Column(DateTime, nullable=True)
    generated_resume = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Job id={self.id} title={self.title!r} company={self.company!r}>"
