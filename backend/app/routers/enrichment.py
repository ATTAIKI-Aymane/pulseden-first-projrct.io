from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
import random
import json

from app.database import get_db
from app import models

router = APIRouter(prefix="/sessions", tags=["Enrichment"])


def try_source_1(account: models.Account):
    """Simule une API premium (ex: Clearbit) - succès ~70%"""
    if random.random() < 0.7:
        return {
            "success": True,
            "data": {
                "employee_count": random.randint(50, 500),
                "annual_revenue": f"${random.randint(1,50)}M",
                "tech_stack": random.choice([["React", "AWS"], ["Vue", "GCP"], ["Angular", "Azure"]]),
            }
        }
    return {"success": False, "data": None}


def try_source_2(account: models.Account):
    """Simule Apify LinkedIn Actor - succès ~80%"""
    if random.random() < 0.8:
        return {
            "success": True,
            "data": {
                "linkedin_employees": random.randint(40, 600),
                "recent_hires": random.randint(0, 15),
                "company_page_followers": random.randint(500, 20000),
            }
        }
    return {"success": False, "data": None}


def try_source_3(account: models.Account):
    """Fallback final - toujours réussi (données basiques déjà connues)"""
    return {
        "success": True,
        "data": {
            "company_name": account.company_name,
            "domain": account.domain,
            "note": "Basic fallback data - limited enrichment available",
        }
    }


CASCADE = [
    ("source_1_premium_api", try_source_1),
    ("source_2_apify_linkedin", try_source_2),
    ("source_3_fallback_basic", try_source_3),
]


def enrich_account(account: models.Account, db: DBSession):
    """Exécute la cascade pour un compte, s'arrête au premier succès"""
    for attempt_order, (source_name, source_func) in enumerate(CASCADE, start=1):
        result = source_func(account)
        status = "success" if result["success"] else "failed"

        enrichment = models.EnrichmentData(
            account_id=account.id,
            source_name=source_name,
            status=status,
            data=json.dumps(result["data"]) if result["data"] else None,
            attempt_order=attempt_order,
        )
        db.add(enrichment)

        if result["success"]:
            # Marque les tentatives précédentes comme ayant mené à ce fallback
            if attempt_order > 1:
                enrichment.status = "fallback_used"
            break

    return


@router.post("/{session_id}/enrichment")
def run_enrichment(session_id: int, db: DBSession = Depends(get_db)):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    accounts = db.query(models.Account).filter(models.Account.session_id == session_id).all()
    if not accounts:
        raise HTTPException(status_code=400, detail="No accounts found. Run sourcing first.")

    for account in accounts:
        enrich_account(account, db)

    session.current_step = 4
    db.commit()

    return {"message": f"Enrichment completed for {len(accounts)} accounts"}


@router.get("/{session_id}/enrichment")
def get_enrichment_results(session_id: int, db: DBSession = Depends(get_db)):
    accounts = db.query(models.Account).filter(models.Account.session_id == session_id).all()
    results = []
    for account in accounts:
        enrichments = db.query(models.EnrichmentData).filter(
            models.EnrichmentData.account_id == account.id
        ).order_by(models.EnrichmentData.attempt_order).all()

        results.append({
            "account_id": account.id,
            "company_name": account.company_name,
            "cascade_history": [
                {
                    "source": e.source_name,
                    "status": e.status,
                    "attempt_order": e.attempt_order,
                    "data": json.loads(e.data) if e.data else None,
                }
                for e in enrichments
            ]
        })
    return results