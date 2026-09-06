from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.models.database import init_db
from app.api.endpoints import auth, ingestion, pipeline, graph, attribution, audit, reliability, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite/PostgreSQL schema on startup
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="TRACE-X — Threat Relationship & Attribution Correlation Engine API",
    version="1.0.0",
    lifespan=lifespan
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Endpoints
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(ingestion.router, prefix=f"{settings.API_V1_STR}/ingestion", tags=["Ingestion & Provenance"])
app.include_router(pipeline.router, prefix=f"{settings.API_V1_STR}/pipeline", tags=["Pipeline & SSE Stream"])
app.include_router(reliability.router, prefix=f"{settings.API_V1_STR}/reliability", tags=["Source Reliability"])
app.include_router(graph.router, prefix=f"{settings.API_V1_STR}/graph", tags=["Graph Intelligence"])
app.include_router(attribution.router, prefix=f"{settings.API_V1_STR}/attribution", tags=["Evidence Fusion & Attribution"])
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}/audit", tags=["Analyst Review & Tamper-Evident Audit"])
app.include_router(reports.router, prefix=f"{settings.API_V1_STR}/reports", tags=["Forensic Reporting & Dossier Exports"])


@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "system": "TRACE-X CTI Platform",
        "mode": "SIH26151 NTRO Benchmark Ready",
        "identity_scope": "REAL-WORLD IDENTITY: NOT ESTABLISHED"
    }
