import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/sessions", tags=["Import"])


@router.post("/{session_id}/accounts/import-csv", response_model=list[schemas.AccountResponse])
async def import_accounts_csv(
    session_id: int,
    file: UploadFile = File(...),
    db: DBSession = Depends(get_db),
):
    """
    Importe un CSV exporte manuellement depuis Apify Console (dataset d'un run
    'Leads Finder'). Contourne la restriction API du plan gratuit tout en
    utilisant de vraies donnees.
    """
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    raw = await file.read()
    text = raw.decode("utf-8-sig")  # utf-8-sig gere le BOM des exports Excel/Apify
    reader = csv.DictReader(io.StringIO(text))

    accounts = []
    skipped = 0

    for row in reader:
        company_name = (row.get("company_name") or "").strip()
        if not company_name:
            skipped += 1
            continue

        account = models.Account(
            session_id=session_id,
            company_name=company_name,
            domain=row.get("company_domain") or None,
            industry=row.get("industry") or None,
            size=row.get("company_size") or None,
            location=row.get("company_city") or row.get("city") or None,
            source="apify_leads_finder_csv_import",
        )
        db.add(account)
        db.flush()

        full_name = (row.get("full_name") or "").strip()
        if full_name:
            contact = models.Contact(
                account_id=account.id,
                full_name=full_name,
                job_title=row.get("job_title") or "Unknown",
                linkedin_url=row.get("linkedin") or None,
                email=row.get("email") or None,
                source="apify_leads_finder_csv_import",
            )
            db.add(contact)

        accounts.append(account)

    if not accounts:
        raise HTTPException(
            status_code=400,
            detail=f"Aucune ligne valide trouvee dans le CSV ({skipped} lignes ignorees sans company_name).",
        )

    session.current_step = 3
    db.commit()
    for a in accounts:
        db.refresh(a)

    return accounts