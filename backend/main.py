"""
MELCO-Care FastAPI Application
Main entry point for the backend API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.config import settings
from backend.routers import chat, admin, pharmacy


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 MELCO-Care Backend Starting...")
    print(f"📡 Ollama URL: {settings.ollama_base_url}")
    print(f"🤖 Primary Model: {settings.ollama_primary_model}")
    yield
    # Shutdown
    print("👋 MELCO-Care Backend Shutting Down...")


# Create FastAPI application
app = FastAPI(
    title="MELCO-Care API",
    description="Agentic AI System for Indian Healthcare",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(pharmacy.router, prefix="/api", tags=["Pharmacy"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to MELCO-Care API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "ollama_url": settings.ollama_base_url,
        "model": settings.ollama_primary_model
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
