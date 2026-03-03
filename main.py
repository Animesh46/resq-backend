"""
ResQ Backend — FastAPI
AI-Powered Multi-Disaster Early Warning & Survival System
"""

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio

from routers import alerts, risk, distress, translate, shelter
from modules.ingestion import run_ingestion_loop



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background ingestion on startup
    task = asyncio.create_task(run_ingestion_loop())
    yield
    task.cancel()

app = FastAPI(
    title="ResQ API",
    description="AI-Powered Disaster Intelligence Backend",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(risk.router, prefix="/api/risk", tags=["Risk Engine"])
app.include_router(distress.router, prefix="/api/distress", tags=["Distress"])
app.include_router(translate.router, prefix="/api/translate", tags=["Translation"])
app.include_router(shelter.router, prefix="/api/shelter", tags=["Shelters"])

@app.get("/health")
async def health():
    return {"status": "ok", "service": "ResQ API v1.0"}
from routers import chat
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])