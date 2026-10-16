import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import (
    ai_chat,
    api_keys,
    audit,
    auth,
    gateway,
    servers,
)
from app.services.unified_mcp import session_manager, unified_mcp_app


# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifecycle of the unified MCP session manager."""
    async with session_manager.run():
        yield


app = FastAPI(
    title="Urumi MCP Gateway",
    description=(
        "Authenticated gateway for multiple upstream MCP servers "
        "with local Ollama AI chat."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


# Frontend origins allowed to access the API
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "service": "urumi-mcp-gateway",
    }


# Register existing REST API routers
app.include_router(auth.router)
app.include_router(api_keys.router)
app.include_router(servers.router)
app.include_router(gateway.router)
app.include_router(audit.router)
app.include_router(ai_chat.router)


# Unified MCP endpoint.
# Clients must provide Authorization: Bearer <API_KEY>.
app.mount("/mcp", unified_mcp_app)