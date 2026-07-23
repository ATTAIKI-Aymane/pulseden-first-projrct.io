from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from faker import Faker
import random
import json

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/sessions", tags=["Sourcing"])
fake = Faker()

TECH_KEYWORDS = ["AI", "Cloud", "Data", "Sync", "Flow", "Stack", "Labs", "Hub", "Wave", "Core"]
SUFFIXES = ["Inc", "Technologies", "Solutions", "Group", "Systems"]


def generate_company(icp: models.ICPProfile):
    keyword = random.choice(TECH_KEYWORDS)
    suffix = random.choice(SUFFIXES)
    company_name = f"{fake.last_name()}{keyword} {suffix}"
    domain = f"{company_name.lower().replace(' ', '')}.com"

    # 70% chance the company matches the ICP industry exactly (simulate real filtering)
    industry = icp.industry if random.random() < 0.7 else fake.job().split()[0]

    return {
        "company_name": company_name,
        "domain": domain,
        "industry": industry,
        "size": icp.company_size,
        "location": icp.location if random.random() < 0.8 else fake.country(),
        "source": "mock_sourcing_engine",
        "raw_data": json.dumps({
            "employees_estimate": random.randint(20, 500),
            "founded_year": random.randint(2005, 2022),
        }),
    }


@router.post("/{session_id}/sourcing", response_model=list[schemas.AccountResponse])
def run_sourcing(session_id: int, count: int = 15, db: DBSession = Depends(get_db)):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    icp = db.query(models.ICPProfile).filter(models.ICPProfile.session_id == session_id).first()
    if not icp:
        raise HTTPException(status_code=400, detail="Define an ICP first before sourcing")

    accounts = []
    for _ in range(count):
        data = generate_company(icp)
        account = models.Account(session_id=session_id, **data)
        db.add(account)
        accounts.append(account)

    session.current_step = 3
    db.commit()
    for a in accounts:
        db.refresh(a)

    return accounts


@router.get("/{session_id}/accounts", response_model=list[schemas.AccountResponse])
def get_accounts(session_id: int, db: DBSession = Depends(get_db)):
    return db.query(models.Account).filter(models.Account.session_id == session_id).all()