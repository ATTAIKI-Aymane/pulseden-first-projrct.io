from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from openai import OpenAI
from dotenv import load_dotenv
import os

from app.database import get_db
from app import models

load_dotenv()

router = APIRouter(prefix="/sessions", tags=["AI Outreach"])

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)


def generate_outreach_message(account: models.Account, contact, signals: list[models.Signal], score):
    signal_context = ""
    if signals:
        signal_context = "Recent signals: " + "; ".join([s.description for s in signals[:2]])
    else:
        signal_context = "No specific recent signals detected."

    contact_first_name = contact.full_name.split()[0] if contact else None
    contact_title = contact.job_title if contact else None

    recipient_line = (
        f"Recipient: {contact_first_name}, {contact_title} at {account.company_name}"
        if contact else
        f"Recipient: a decision-maker at {account.company_name}"
    )

    prompt = f"""Write a short, personalized B2B cold outreach email (max 80 words) for a sales rep reaching out to a prospect.

{recipient_line}
Industry: {account.industry}
{signal_context}
Fit score: {score}/100

The email should:
- Address the recipient by first name if provided, acknowledging their role
- Reference the signal naturally if available
- Be professional but conversational
- End with a soft call-to-action (e.g. asking for 15 min call)
- NOT use generic phrases like "I hope this email finds you well"

Output ONLY the email body, no subject line, no explanation."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Error generating message: {str(e)}] Fallback: Hi, I noticed {account.company_name} might benefit from our solution. Would you be open to a quick call?"


@router.post("/{session_id}/outreach")
def run_outreach_generation(session_id: int, db: DBSession = Depends(get_db)):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    accounts = db.query(models.Account).filter(models.Account.session_id == session_id).all()
    if not accounts:
        raise HTTPException(status_code=400, detail="No accounts found")

    generated = 0
    for account in accounts:
        signals = db.query(models.Signal).filter(models.Signal.account_id == account.id).all()
        score = db.query(models.Score).filter(models.Score.account_id == account.id).first()
        contact = db.query(models.Contact).filter(models.Contact.account_id == account.id).first()
        total_score = score.total_score if score else 50

        message = generate_outreach_message(account, contact, signals, total_score)

        subject = (
            f"Quick question, {contact.full_name.split()[0]}"
            if contact else
            f"Quick question for {account.company_name}"
        )

        sequence = models.Sequence(
            account_id=account.id,
            channel="email",
            subject=subject,
            message_body=message,
            personalization_notes=(
                f"Targeted {contact.job_title} ({contact.full_name}) — "
                f"based on {len(signals)} signal(s) and fit score {total_score}"
                if contact else
                f"No contact found — based on {len(signals)} signal(s) and fit score {total_score}"
            ),
        )
        db.add(sequence)
        generated += 1

    session.current_step = 7
    db.commit()

    return {"message": f"Outreach sequences generated for {generated} accounts"}


@router.get("/{session_id}/outreach")
def get_outreach_sequences(session_id: int, db: DBSession = Depends(get_db)):
    accounts = db.query(models.Account).filter(models.Account.session_id == session_id).all()
    results = []
    for account in accounts:
        seq = db.query(models.Sequence).filter(models.Sequence.account_id == account.id).first()
        if seq:
            results.append({
                "account_id": account.id,
                "company_name": account.company_name,
                "channel": seq.channel,
                "subject": seq.subject,
                "message": seq.message_body,
            })
    return results