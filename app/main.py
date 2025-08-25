from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

from app.api import chat, chats, leads, kpis, funnel, objections
from app.middleware.request_logger import RequestLoggerMiddleware
from app.api import agent, chat_events

# ---- Logging config ---------------------------------------------------------
LOG_LEVEL = os.getenv("ACE_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s:%(lineno)d - %(message)s",
)
logger = logging.getLogger("ace.main")
logger.info("Starting Omsoft ACE Backend with LOG_LEVEL=%s", LOG_LEVEL)

# ---- FastAPI app ------------------------------------------------------------
app = FastAPI(title="Omsoft ACE Backend")
app.add_middleware(RequestLoggerMiddleware)

# ---- CORS -------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:4400",
        "http://127.0.0.1:4400",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Routers ----------------------------------------------------------------
app.include_router(chat.router,        prefix="/chat",  tags=["Chat"])
app.include_router(chats.router,       prefix="/chats", tags=["Chats"])
app.include_router(leads.router,       prefix="/leads", tags=["Leads"])
app.include_router(kpis.router,        prefix="/kpis",  tags=["KPIs"])
app.include_router(funnel.router,      prefix="/funnel", tags=["Funnel"])
app.include_router(objections.router,  prefix="/objections", tags=["Objections"])
app.include_router(agent.router,       prefix="/agent", tags=["Agent"])
app.include_router(chat_events.router, prefix="/chat",  tags=["ChatEvents"])

logger.info("Routers registered.")
