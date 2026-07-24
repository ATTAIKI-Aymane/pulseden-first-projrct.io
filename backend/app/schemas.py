import json
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


# ---------- ICP ----------
class ICPCreate(BaseModel):
    industry: str
    company_size: str
    location: str
    job_titles: List[str]
    keywords: List[str]




class ICPResponse(BaseModel):
    id: int
    session_id: int
    industry: str
    company_size: str
    location: str
    job_titles: List[str]
    keywords: List[str]
    created_at: datetime

    class Config:
        from_attributes = True

    @field_validator("job_titles", "keywords", mode="before")
    @classmethod
    def parse_json_string(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value


# ---------- Session ----------
class SessionCreate(BaseModel):
    name: str = "New Session"


class SessionResponse(BaseModel):
    id: int
    name: str
    status: str
    current_step: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Account ----------
class AccountResponse(BaseModel):
    id: int
    company_name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None

    class Config:
        from_attributes = True


        # ---------- Contact ----------
class ContactResponse(BaseModel):
    id: int
    account_id: int
    full_name: str
    job_title: str
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    source: str

    class Config:
        from_attributes = True