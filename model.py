from datatime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

from sqlmodel import Field, SQLModel, Relationship 

def _uuid() -> str:
    return str(uuid4())

def _now() -> datetime:
    return datetime.now(timezone.utc)

class Thumbnail(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    job_id: str = Field(foreign_key="job_id")
    style: str = Field(default="")
    status: str = Field(default="pending")
    error_message:Optional[str] =Field(default=None)
    created_at: datetime = Field(default_factory=_now)

    job: Optional["Job"] = Relationship(back_populates="thumbnails")

class Job(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    prompt:str = Field(default="")
    num_thumnails: int = Field(default=1, ge=1, le=3)
    headshot_url:str = Field(default="")
    status:str = Field(default="pending")
    created_at: datetime = Field(default_factory=_now)
    Thumbnails: List[Thumbnail] = Relationship(back_populates="job")
    