from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import session, sourcing, enrichment, signals, scoring, outreach, export

app = FastAPI(title="PulseDev B2B GTM Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session.router)
app.include_router(sourcing.router)
app.include_router(enrichment.router)
app.include_router(signals.router)
app.include_router(scoring.router)
app.include_router(outreach.router)
app.include_router(export.router)


@app.get("/")
def root():
    return {"message": "PulseDev API is running 🚀"}