"""Halo Backend - Main FastAPI Application"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import generate
from app.api.routes import protocols

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Text-to-DApp Engine for Stellar/Soroban",
    version=settings.app_version,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(generate.router, prefix="/api/v1", tags=["generate"])
app.include_router(protocols.router, prefix="/api/v1", tags=["protocols"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "llm": "openai",
        "model": settings.openai_model,
        "stellar_network": settings.stellar_network,
    }
