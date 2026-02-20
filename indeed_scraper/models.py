from dataclasses import dataclass
from typing import Optional

@dataclass
class Job:
    title: str
    company: str
    location: str
    posted: str
    summary: str
    link: str
    full_description: Optional[str] = None
    company_url: Optional[str] = None
    is_workday: str = "No"
    
    def to_dict(self):
        return {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "posted": self.posted,
            "summary": self.summary,
            "link": self.link,
            "full_description": self.full_description,
            "company_url": self.company_url,
            "is_workday": self.is_workday
        }
