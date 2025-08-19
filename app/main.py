from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, leads, kpis, funnel, objections

app = FastAPI(title="Omsoft ACE Backend")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(leads.router, prefix="/leads", tags=["Leads"])
app.include_router(kpis.router, prefix="/kpis", tags=["KPIs"])
app.include_router(funnel.router, prefix="/funnel", tags=["Funnel"])
app.include_router(objections.router, prefix="/objections", tags=["Objections"])
