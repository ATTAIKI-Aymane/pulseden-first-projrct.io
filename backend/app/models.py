from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="New Session")
    status = Column(String, default="pending")  # pending, running, completed, failed
    current_step = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    icp_profile = relationship("ICPProfile", back_populates="session", uselist=False)
    accounts = relationship("Account", back_populates="session")


class ICPProfile(Base):
    __tablename__ = "icp_profiles"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    industry = Column(String)
    company_size = Column(String)
    location = Column(String)
    job_titles = Column(Text)   # JSON string: ["CTO", "VP Sales"]
    keywords = Column(Text)     # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="icp_profile")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    company_name = Column(String)
    domain = Column(String)
    industry = Column(String)
    size = Column(String)
    location = Column(String)
    source = Column(String)
    raw_data = Column(Text)     # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="accounts")
    enrichments = relationship("EnrichmentData", back_populates="account")
    contact = relationship("Contact", back_populates="account", uselist=False)
    signals = relationship("Signal", back_populates="account")
    score = relationship("Score", back_populates="account", uselist=False)
    sequence = relationship("Sequence", back_populates="account", uselist=False)
    contact = relationship("Contact", back_populates="account", uselist=False)


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    full_name = Column(String)
    job_title = Column(String)          # "CEO", "Founder", "Co-Founder"...
    linkedin_url = Column(String)
    email = Column(String, nullable=True)
    source = Column(String, default="mock_contact_finder")
    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="contact")


class EnrichmentData(Base):
    __tablename__ = "enrichment_data"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    source_name = Column(String)
    status = Column(String)     # success, failed, fallback_used
    data = Column(Text)         # JSON string
    attempt_order = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="enrichments")


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    signal_type = Column(String)   # hiring, funding_round, tech_change, leadership_change
    description = Column(Text)
    evidence_url = Column(String)
    confidence_score = Column(Float)
    detected_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="signals")


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    fit_score = Column(Float)
    signal_score = Column(Float)
    total_score = Column(Float)
    rank = Column(Integer)
    computed_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="score")


class Sequence(Base):
    __tablename__ = "sequences"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    channel = Column(String)     # email, linkedin
    subject = Column(String)
    message_body = Column(Text)
    personalization_notes = Column(Text)
    generated_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="sequence")


class Export(Base):
    __tablename__ = "exports"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    export_type = Column(String)   # csv, webhook
    destination = Column(String)
    status = Column(String)
    exported_at = Column(DateTime, default=datetime.utcnow)