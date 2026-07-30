import os
import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from faker import Faker
import random
import json

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/sessions", tags=["Sourcing"])
fake = Faker()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
LEADS_FINDER_ACTOR = "code_crafter~leads-finder"

TECH_KEYWORDS = ["AI", "Cloud", "Data", "Sync", "Flow", "Stack", "Labs", "Hub", "Wave", "Core"]
SUFFIXES = ["Inc", "Technologies", "Solutions", "Group", "Systems"]


def generate_company_mock(icp: models.ICPProfile):
    """Mode demo — donnees generees (Faker), utilise si use_real_data=false."""
    keyword = random.choice(TECH_KEYWORDS)
    suffix = random.choice(SUFFIXES)
    company_name = f"{fake.last_name()}{keyword} {suffix}"
    domain = f"{company_name.lower().replace(' ', '')}.com"

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


def fetch_real_leads(icp: models.ICPProfile, count: int) -> list[dict]:
    """
    Appelle l'actor Apify 'Leads Finder' avec les filtres de l'ICP.
    Chaque lead retourne contient a la fois les donnees company ET contact
    (nom, poste, email verifie, LinkedIn) en un seul appel.
    """
    if not APIFY_TOKEN:
        raise HTTPException(status_code=500, detail="APIFY_TOKEN manquant dans backend/.env")

    job_titles = json.loads(icp.job_titles) if icp.job_titles else []

    payload = {
        "contact_job_title": job_titles,
        "company_industry": [icp.industry] if icp.industry else [],
        "contact_location": [icp.location] if icp.location else [],
        "size": [icp.company_size] if icp.company_size else [],
        "email_status": ["validated", "unknown"],
        "fetch_count": count,
    }

    url = f"https://api.apify.com/v2/acts/{LEADS_FINDER_ACTOR}/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    resp = requests.post(url, json=payload, timeout=180)
    resp.raise_for_status()
    return resp.json()


@router.post("/{session_id}/sourcing", response_model=list[schemas.AccountResponse])
def run_sourcing(
    session_id: int,
    count: int = 15,
    use_real_data: bool = True,
    db: DBSession = Depends(get_db),
):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    icp = db.query(models.ICPProfile).filter(models.ICPProfile.session_id == session_id).first()
    if not icp:
        raise HTTPException(status_code=400, detail="Define an ICP first before sourcing")

    accounts = []

    if use_real_data:
        leads = fetch_real_leads(icp, count)
        if not leads:
            raise HTTPException(
                status_code=404,
                detail="Aucun lead reel trouve pour cet ICP. Essaie d'elargir les filtres (industry/location/job_titles).",
            )

        for lead in leads:
            account = models.Account(
                session_id=session_id,
                company_name=lead.get("company_name") or "Unknown",
                domain=lead.get("company_domain"),
                industry=lead.get("industry") or icp.industry,
                size=lead.get("company_size") or icp.company_size,
                location=lead.get("city") or icp.location,
                source="apify_leads_finder",
                raw_data=json.dumps({
                    "company_website": lead.get("company_website"),
                    "company_linkedin": lead.get("company_linkedin"),
                    "founded_year": lead.get("company_founded_year"),
                    "revenue": lead.get("company_annual_revenue"),
                }),
            )
            db.add(account)
            db.flush()

            if lead.get("full_name"):
                contact = models.Contact(
                    account_id=account.id,
                    full_name=lead.get("full_name"),
                    job_title=lead.get("job_title") or "Unknown",
                    linkedin_url=lead.get("linkedin"),
                    email=lead.get("email"),
                    source="apify_leads_finder",
                )
                db.add(contact)

            accounts.append(account)
    else:
        for _ in range(count):
            data = generate_company_mock(icp)
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