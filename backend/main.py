"""
AI Knowledge Assistant API
RAG (Retrieval-Augmented Generation) backend with FastAPI
"""
import uvicorn
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import db_manager


async def _background_model_loading():
    """Load embedding model in background without blocking startup."""
    try:
        from app.services.embedding_service import load_embedding_model_async
        await load_embedding_model_async()
        print("✅ Background model loading completed")
    except Exception as e:
        print(f"⚠️ Background model loading failed: {e}")
        print("⚠️ Will use TF-IDF fallback for embeddings")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown tasks."""
    # Startup
    print("🚀 Starting AI Knowledge Assistant API...")

    try:
        # Initialize database connection
        await db_manager.connect()
        print("✅ Database connection established")

        # Enable pgvector extension
        await db_manager.enable_pgvector_extension()
        print("✅ pgvector extension enabled")

        # Create embeddings table
        from app.services.vector_search import create_embeddings_table, create_chat_tables
        await create_embeddings_table()
        print("✅ Embeddings table created")

        # Create chat tables
        await create_chat_tables()
        print("✅ Chat tables created")

        # Try to load embedding model in background (non-blocking)
        print("🔄 Attempting to load embedding model in background...")
        asyncio.create_task(_background_model_loading())

    except Exception as e:
        print(f"❌ Startup failed: {e}")
        # Don't raise here to allow API to start even if DB is not available

    yield

    # Shutdown
    print("🛑 Shutting down AI Knowledge Assistant API...")
    await db_manager.disconnect()
    print("✅ Database connection closed")


# Create FastAPI application with lifespan management
app = FastAPI(
    title=settings.app_name,
    description="RAG-based document chat API with vector similarity search",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://docchat-production-171b.up.railway.app"
        # Add your production frontend URL here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoints
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "AI Knowledge Assistant API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        async with db_manager.get_connection() as conn:
            await conn.fetchval("SELECT 1")

        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": "now()"
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )


@app.get("/api/hello")
def hello():
    """Legacy hello endpoint."""
    return {"message": "Hello from FastAPI backend"}


# Import and include API routers
from app.api import documents, chat
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )