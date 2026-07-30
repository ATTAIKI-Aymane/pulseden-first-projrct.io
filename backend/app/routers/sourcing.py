import os
import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from faker import Faker
import random
import json

from app.database import get_db
from app import models, schemas

load_dotenv()

router = APIRouter(prefix="/sessions", tags=["Sourcing"])
fake = Faker()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
LEADS_FINDER_ACTOR = "code_crafter~leads-finder"

TECH_KEYWORDS = ["AI", "Cloud", "Data", "Sync", "Flow", "Stack", "Labs", "Hub", "Wave", "Core"]
SUFFIXES = ["Inc", "Technologies", "Solutions", "Group", "Systems"]

ALLOWED_SIZES = ["1-10", "11-20", "21-50", "51-100", "101-200", "201-500",
                  "501-1000", "1001-2000", "2001-5000", "5001-10000",
                  "10001-20000", "20001-50000", "50000+"]


def normalize_company_size(raw_size: str) -> list[str]:
    """Convertit une taille libre (ex: '50-200') vers les tranches acceptees par Apify."""
    if not raw_size:
        return []
    try:
        low = int("".join(c for c in raw_size.split("-")[0] if c.isdigit()))
        high_part = raw_size.split("-")[-1]
        high = int("".join(c for c in high_part if c.isdigit())) if any(c.isdigit() for c in high_part) else 999999
    except (ValueError, IndexError):
        return []

    matched = []
    for bucket in ALLOWED_SIZES:
        if bucket == "50000+":
            b_low, b_high = 50000, 10**9
        else:
            b_low, b_high = [int(x) for x in bucket.split("-")]
        if b_low <= high and b_high >= low:
            matched.append(bucket)
    return matched


ALLOWED_INDUSTRIES = {
    "information technology & services", "construction", "marketing & advertising", "real estate",
    "health, wellness & fitness", "management consulting", "computer software", "internet", "retail",
    "financial services", "consumer services", "hospital & health care", "automotive", "restaurants",
    "education management", "food & beverages", "design", "hospitality", "accounting", "events services",
    "nonprofit organization management", "entertainment", "electrical/electronic manufacturing",
    "leisure, travel & tourism", "professional training & coaching", "transportation/trucking/railroad",
    "law practice", "apparel & fashion", "architecture & planning", "mechanical or industrial engineering",
    "insurance", "telecommunications", "human resources", "staffing & recruiting", "sports",
    "legal services", "oil & energy", "media production", "machinery", "wholesale", "consumer goods",
    "biotechnology", "pharmaceuticals", "banking", "e-learning", "computer & network security",
    "computer games", "computer hardware", "computer networking", "market research",
}

INDUSTRY_SYNONYMS = {
    "saas": "computer software",
    "software": "computer software",
    "tech": "information technology & services",
    "technology": "information technology & services",
    "it": "information technology & services",
    "fintech": "financial services",
    "healthtech": "hospital & health care",
    "ai": "computer software",
    "ecommerce": "internet",
    "e-commerce": "internet",
}


def normalize_industry(raw_industry: str) -> list[str]:
    """Mappe une industrie libre vers une valeur acceptee par Apify. Si aucune correspondance, ne filtre pas (liste vide)."""
    if not raw_industry:
        return []
    key = raw_industry.strip().lower()
    if key in ALLOWED_INDUSTRIES:
        return [key]
    if key in INDUSTRY_SYNONYMS:
        return [INDUSTRY_SYNONYMS[key]]
    return []




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
        "company_industry": normalize_industry(icp.industry),
        "contact_location": [icp.location.lower()] if icp.location else [],
        "size": normalize_company_size(icp.company_size),
        "email_status": ["validated", "unknown"],
        "fetch_count": count + 10,  # marge pour compenser les leads sans company_name
    }

    url = f"https://api.apify.com/v2/acts/{LEADS_FINDER_ACTOR}/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    print("=== DEBUG: PAYLOAD SENT TO APIFY ===")
    print(payload)
    resp = requests.post(url, json=payload, timeout=180)
    if not resp.ok:
        print("=== DEBUG: APIFY ERROR RESPONSE ===")
        print(resp.status_code, resp.text)
    resp.raise_for_status()
    results = resp.json()

    with_name = sum(1 for r in results if r.get("company_name"))
    print(f"=== DEBUG: {len(results)} leads total, {with_name} have company_name ===")
    if results:
        print("=== DEBUG: sample lead keys ===", list(results[0].keys()))
        if "error" in results[0]:
            print("=== DEBUG: ACTOR ERROR CONTENT ===")
            print(results[0])

    return results


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
            if not lead.get("company_name"):
                continue  # skip les leads sans nom d'entreprise reel

            account = models.Account(
                session_id=session_id,
                company_name=lead.get("company_name"),
                domain=lead.get("company_domain"),
                industry=lead.get("industry") or icp.industry,
                size=str(lead.get("company_size")) if lead.get("company_size") else icp.company_size,
                location=lead.get("company_city") or lead.get("city") or icp.location,
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