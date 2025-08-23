from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api import chat, chats, leads, kpis, funnel, objections
from app.middleware.request_logger import RequestLoggerMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
logger = logging.getLogger("ace")

app = FastAPI(title="Omsoft ACE Backend")
app.add_middleware(RequestLoggerMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:4400",
        "http://127.0.0.1:4400"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(chats.router, prefix="/chats", tags=["Chats"]) 
app.include_router(leads.router, prefix="/leads", tags=["Leads"])
app.include_router(kpis.router, prefix="/kpis", tags=["KPIs"])
app.include_router(funnel.router, prefix="/funnel", tags=["Funnel"])
app.include_router(objections.router, prefix="/objections", tags=["Objections"])
