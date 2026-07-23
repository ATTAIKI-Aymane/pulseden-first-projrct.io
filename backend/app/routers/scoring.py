from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app import models

router = APIRouter(prefix="/sessions", tags=["Scoring"])


def calculate_fit_score(account: models.Account, icp: models.ICPProfile):
    """Calcule le score de correspondance ICP (0-100)"""
    score = 40  # base score

    if account.industry == icp.industry:
        score += 35
    if account.location == icp.location:
        score += 25

    return min(score, 100)


def calculate_signal_score(signals: list[models.Signal]):
    """Calcule le score basé sur les signaux détectés (0-100)"""
    if not signals:
        return 0

    # Poids par type de signal (funding et leadership = signaux plus forts)
    weights = {
        "funding_round": 30,
        "leadership_change": 25,
        "hiring": 20,
        "tech_change": 15,
    }

    total = 0
    for s in signals:
        base_weight = weights.get(s.signal_type, 10)
        # Pondéré par la confiance du signal
        total += base_weight * (s.confidence_score / 100)

    return min(round(total, 1), 100)


@router.post("/{session_id}/scoring")
def run_scoring(session_id: int, db: DBSession = Depends(get_db)):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    icp = db.query(models.ICPProfile).filter(models.ICPProfile.session_id == session_id).first()
    if not icp:
        raise HTTPException(status_code=400, detail="ICP not found")

    accounts = db.query(models.Account).filter(models.Account.session_id == session_id).all()
    if not accounts:
        raise HTTPException(status_code=400, detail="No accounts found")

    scored_accounts = []
    for account in accounts:
        signals = db.query(models.Signal).filter(models.Signal.account_id == account.id).all()

        fit = calculate_fit_score(account, icp)
        signal = calculate_signal_score(signals)
        total = round((fit * 0.5) + (signal * 0.5), 1)  # 50/50 weighting

        scored_accounts.append({"account": account, "fit": fit, "signal": signal, "total": total})

    # Trier par total_score décroissant pour attribuer le rank
    scored_accounts.sort(key=lambda x: x["total"], reverse=True)

    for rank, item in enumerate(scored_accounts, start=1):
        score_entry = models.Score(
            account_id=item["account"].id,
            fit_score=item["fit"],
            signal_score=item["signal"],
            total_score=item["total"],
            rank=rank,
        )
        db.add(score_entry)

    session.current_step = 6
    db.commit()

    return {"message": f"Scoring completed for {len(accounts)} accounts"}


@router.get("/{session_id}/scoring")
def get_scores(session_id: int, db: DBSession = Depends(get_db)):
    accounts = db.query(models.Account).filter(models.Account.session_id == session_id).all()

    results = []
    for account in accounts:
        score = db.query(models.Score).filter(models.Score.account_id == account.id).first()
        if score:
            results.append({
                "account_id": account.id,
                "company_name": account.company_name,
                "fit_score": score.fit_score,
                "signal_score": score.signal_score,
                "total_score": score.total_score,
                "rank": score.rank,
            })

    results.sort(key=lambda x: x["rank"])
    return results