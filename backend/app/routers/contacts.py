from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from faker import Faker
import random

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/sessions", tags=["Contacts"])
fake = Faker()

DECISION_MAKER_TITLES = ["CEO", "Founder", "Co-Founder", "Managing Director"]


def find_contact_mock(account: models.Account):
    """
    MOCKED pour la démo. En prod: remplacer par un vrai appel Apify
    (ex: LinkedIn Company Employees Scraper) basé sur account.company_name / account.domain.
    """
    first = fake.first_name()
    last = fake.last_name()
    slug = f"{first}-{last}".lower()

    return {
        "full_name": f"{first} {last}",
        "job_title": random.choice(DECISION_MAKER_TITLES),
        "linkedin_url": f"https://linkedin.com/in/{slug}-{random.randint(100,999)}",
        "email": f"{first.lower()}.{last.lower()}@{account.domain}" if account.domain else None,
        "source": "mock_contact_finder",
    }


@router.post("/{session_id}/contacts", response_model=list[schemas.ContactResponse])
def run_contact_discovery(session_id: int, db: DBSession = Depends(get_db)):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    accounts = db.query(models.Account).filter(models.Account.session_id == session_id).all()
    if not accounts:
        raise HTTPException(status_code=400, detail="No accounts found. Run sourcing first.")

    contacts = []
    for account in accounts:
        data = find_contact_mock(account)
        contact = models.Contact(account_id=account.id, **data)
        db.add(contact)
        contacts.append(contact)

    db.commit()
    for c in contacts:
        db.refresh(c)

    return contacts


@router.get("/{session_id}/contacts", response_model=list[schemas.ContactResponse])
def get_contacts(session_id: int, db: DBSession = Depends(get_db)):
    accounts = db.query(models.Account).filter(models.Account.session_id == session_id).all()
    account_ids = [a.id for a in accounts]
    return db.query(models.Contact).filter(models.Contact.account_id.in_(account_ids)).all()