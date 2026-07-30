from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
import random

from app.database import get_db
from app import models

router = APIRouter(prefix="/sessions", tags=["Signal Detection"])


SIGNAL_TEMPLATES = [
    {
        "type": "hiring",
        "descriptions": [
            "Company posted {n} new job openings in Sales/Engineering in the last 30 days",
            "Rapid headcount growth detected: {n} new positions opened this quarter",
        ],
        "evidence": "linkedin.com/company/jobs (simulated snapshot)",
    },
    {
        "type": "funding_round",
        "descriptions": [
            "Company raised a Series {series} funding round of ${amount}M",
            "New investment announced: ${amount}M in Series {series}",
        ],
        "evidence": "crunchbase.com/funding-rounds (simulated snapshot)",
    },
    {
        "type": "tech_change",
        "descriptions": [
            "Detected migration to a new cloud provider in the last 60 days",
            "New technology stack adoption identified (BuiltWith signal)",
        ],
        "evidence": "builtwith.com/tech-history (simulated snapshot)",
    },
    {
        "type": "leadership_change",
        "descriptions": [
            "New {title} appointed in the last 90 days",
            "Executive leadership change detected: new {title} hired",
        ],
        "evidence": "linkedin.com/company/people (simulated snapshot)",
    },
]


def generate_signals_for_account():
    """Génère 0 à 3 signaux aléatoires pour un compte"""
    num_signals = random.choices([0, 1, 2, 3], weights=[15, 35, 35, 15])[0]
    signals = []

    chosen_templates = random.sample(SIGNAL_TEMPLATES, min(num_signals, len(SIGNAL_TEMPLATES)))

    for template in chosen_templates:
        desc_template = random.choice(template["descriptions"])
        description = desc_template.format(
            n=random.randint(3, 20),
            series=random.choice(["A", "B", "C"]),
            amount=random.randint(2, 80),
            title=random.choice(["CTO", "VP Sales", "CRO", "Head of Growth"]),
        )
        signals.append({
            "signal_type": template["type"],
            "description": description,
            "evidence_url": template["evidence"],
            "confidence_score": round(random.uniform(60, 98), 1),
        })

    return signals


@router.post("/{session_id}/signals")
def run_signal_detection(session_id: int, db: DBSession = Depends(get_db)):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    accounts = db.query(models.Account).filter(models.Account.session_id == session_id).all()
    if not accounts:
        raise HTTPException(status_code=400, detail="No accounts found. Run sourcing first.")

    total_signals = 0
    for account in accounts:
        signals_data = generate_signals_for_account()
        for sig in signals_data:
            signal = models.Signal(account_id=account.id, **sig)
            db.add(signal)
            total_signals += 1

    session.current_step = 5
    db.commit()

    return {"message": f"Signal detection completed. {total_signals} signals found across {len(accounts)} accounts"}


@router.get("/{session_id}/signals")
def get_signals(session_id: int, db: DBSession = Depends(get_db)):
    accounts = db.query(models.Account).filter(models.Account.session_id == session_id).all()
    results = []
    for account in accounts:
        signals = db.query(models.Signal).filter(models.Signal.account_id == account.id).all()
        results.append({
            "account_id": account.id,
            "company_name": account.company_name,
            "signals": [
                {
                    "type": s.signal_type,
                    "description": s.description,
                    "evidence": s.evidence_url,
                    "confidence_score": s.confidence_score,
                }
                for s in signals
            ]
        })
    return results