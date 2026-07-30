from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
import json

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/sessions", tags=["Sessions & ICP"])


# ---------- Créer une nouvelle session ----------
@router.post("/", response_model=schemas.SessionResponse)
def create_session(payload: schemas.SessionCreate, db: DBSession = Depends(get_db)):
    new_session = models.Session(name=payload.name, status="pending", current_step=1)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


# ---------- Récupérer une session ----------
@router.get("/{session_id}", response_model=schemas.SessionResponse)
def get_session(session_id: int, db: DBSession = Depends(get_db)):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ---------- Lister toutes les sessions ----------
@router.get("/", response_model=list[schemas.SessionResponse])
def list_sessions(db: DBSession = Depends(get_db)):
    return db.query(models.Session).all()


# ---------- Définir l'ICP pour une session ----------
@router.post("/{session_id}/icp", response_model=schemas.ICPResponse)
def create_icp(session_id: int, payload: schemas.ICPCreate, db: DBSession = Depends(get_db)):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    icp = models.ICPProfile(
        session_id=session_id,
        industry=payload.industry,
        company_size=payload.company_size,
        location=payload.location,
        job_titles=json.dumps(payload.job_titles),
        keywords=json.dumps(payload.keywords),
    )
    db.add(icp)

    # Update session status/step
    session.status = "running"
    session.current_step = 2

    db.commit()
    db.refresh(icp)
    return icp


# ---------- Récupérer l'ICP d'une session ----------
@router.get("/{session_id}/icp", response_model=schemas.ICPResponse)
def get_icp(session_id: int, db: DBSession = Depends(get_db)):
    icp = db.query(models.ICPProfile).filter(models.ICPProfile.session_id == session_id).first()
    if not icp:
        raise HTTPException(status_code=404, detail="ICP not found for this session")
    return icp