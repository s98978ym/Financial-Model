"""FastAPI application — PL Generator API.

This is the single source of truth for all PL calculations.
The Next.js frontend communicates exclusively through this API.
"""

from __future__ import annotations

import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import projects, documents, phases, recalc, export, jobs

logger = logging.getLogger(__name__)

app = FastAPI(
    title="PL Generator API",
    version="0.2.0",
    description="Financial model generation API — 6-phase pipeline with LLM extraction",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
ALLOWED_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,https://plgenerator.vercel.app",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(projects.router, prefix="/v1", tags=["projects"])
app.include_router(documents.router, prefix="/v1", tags=["documents"])
app.include_router(phases.router, prefix="/v1", tags=["phases"])
app.include_router(recalc.router, prefix="/v1", tags=["recalc"])
app.include_router(export.router, prefix="/v1", tags=["export"])
app.include_router(jobs.router, prefix="/v1", tags=["jobs"])


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}


@app.get("/")
async def root():
    return {"message": "PL Generator API", "docs": "/docs"}
