"""
FastAPI application for RAG-powered healthcare chat.
Provides REST API endpoints for document upload, ingestion, and chat.
"""

from contextlib import asynccontextmanager  # required for lifespan events
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

from ingest import ingest_document, DocumentIngestionError
from rag import RAGPipeline, RAGError
from chat import RAGChat, ChatError

# Load environment variables from .env file
load_dotenv()


# ==================== Pydantic Models ====================

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    query: str = Field(..., min_length=1, max_length=5000)
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    include_sources: bool = Field(default=True)


class SourceChunk(BaseModel):
    """Source document chunk returned with answer."""
    content: str
    relevance_score: float
    rank: int


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    answer: str
    sources_count: int
    confidence: float
    sources: Optional[List[SourceChunk]] = None


class IngestResponse(BaseModel):
    """Response model for document ingestion."""
    filename: str
    chunks_count: int
    status: str
    message: str


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    rag_initialized: bool
    collection_stats: Optional[dict] = None


class HistoryClearResponse(BaseModel):
    """Response model for clearing history."""
    status: str
    message: str


# ==================== Global State ====================

class AppState:
    """Holds global application state."""
    rag_pipeline: Optional[RAGPipeline] = None
    chat_engine: Optional[RAGChat] = None
    initialized: bool = False


# Single global instance of app state
app_state = AppState()


# ==================== Lifespan ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown.
    Initializes RAG pipeline and chat engine on startup.
    """
    # ── STARTUP ──
    try:
        print("\n" + "="*50)
        print("🚀 Starting RAG Healthcare Chat Application")
        print("="*50)

        # Get config from .env
        embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        db_path = os.getenv("CHROMA_DB_PATH", "./chroma_store")
        collection_name = os.getenv("COLLECTION_NAME", "humana_chat_docs")

        # Initialize RAG pipeline
        print("\n📊 Initializing RAG Pipeline...")
        app_state.rag_pipeline = RAGPipeline(
            embedding_model_name=embedding_model,
            db_path=db_path,
            collection_name=collection_name
        )

        # Initialize Chat engine with Ollama
        print("\n💬 Initializing Chat Engine...")
        app_state.chat_engine = RAGChat(
            rag_pipeline=app_state.rag_pipeline,
            llm_model=None  # Using Ollama directly inside chat.py
        )

        app_state.initialized = True

        print("\n" + "="*50)
        print("✓ Application ready for requests!")
        print("="*50 + "\n")

    except Exception as e:
        print(f"\n✗ Startup failed: {str(e)}")
        raise

    yield  # App runs here

    # ── SHUTDOWN ──
    print("\n👋 Shutting down application...")


# ==================== App Setup ====================

app = FastAPI(
    title="RAG Healthcare Chat API",
    description="RAG chatbot for healthcare document analysis",
    version="1.0.0",
    lifespan=lifespan  # use modern lifespan instead of on_event
)

# Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Health Check ====================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Returns API health status and collection stats."""
    try:
        if not app_state.initialized or app_state.rag_pipeline is None:
            return HealthResponse(
                status="not_ready",
                rag_initialized=False
            )

        # Get vector DB stats
        stats = app_state.rag_pipeline.get_collection_stats()

        return HealthResponse(
            status="healthy",
            rag_initialized=True,
            collection_stats=stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


# ==================== Ingest Document ====================

@app.post("/ingest", response_model=IngestResponse)
async def ingest_file(file: UploadFile = File(...)):
    """
    Upload and process a PDF document.
    Chunks it, embeds it, stores in ChromaDB.
    """
    try:
        # Check RAG is ready
        if not app_state.initialized or app_state.rag_pipeline is None:
            raise HTTPException(status_code=503, detail="RAG pipeline not initialized")

        # Validate filename exists
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        # Validate PDF only
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        # Create data folder if missing
        data_dir = os.getenv("PDF_DATA_FOLDER", "./data")
        Path(data_dir).mkdir(parents=True, exist_ok=True)

        # Save uploaded file to disk
        file_path = os.path.join(data_dir, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        print(f"\n📄 Ingesting: {file.filename}")

        # Process document into chunks
        chunks = ingest_document(
            file_path,
            chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
            max_file_size_mb=int(os.getenv("MAX_PDF_SIZE_MB", "50"))
        )

        # Store embeddings in ChromaDB
        app_state.rag_pipeline.store_documents(
            chunks,
            metadata={"filename": file.filename}
        )

        return IngestResponse(
            filename=file.filename,
            chunks_count=len(chunks),
            status="success",
            message=f"Successfully ingested {len(chunks)} chunks"
        )

    except DocumentIngestionError as e:
        raise HTTPException(status_code=400, detail=f"Ingestion error: {str(e)}")
    except RAGError as e:
        raise HTTPException(status_code=500, detail=f"RAG error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ==================== Chat ====================

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Ask a question about the uploaded document.
    Answer is grounded ONLY in document content — no hallucinations.
    """
    try:
        # Check chat engine is ready
        if not app_state.initialized or app_state.chat_engine is None:
            raise HTTPException(status_code=503, detail="Chat engine not initialized")

        # Check documents exist
        stats = app_state.rag_pipeline.get_collection_stats()
        if stats['total_documents'] == 0:
            raise HTTPException(
                status_code=400,
                detail="No documents ingested yet. Please upload a PDF first."
            )

        # Run RAG pipeline and get answer
        result = app_state.chat_engine.answer_query(
            query=request.query,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            include_sources=request.include_sources
        )

        # Build source chunks for response
        sources = None
        if request.include_sources and 'sources' in result:
            sources = [
                SourceChunk(
                    content=s['content'],
                    relevance_score=s['relevance_score'],
                    rank=s['rank']
                )
                for s in result['sources']
            ]

        return ChatResponse(
            answer=result['answer'],
            sources_count=result['sources_count'],
            confidence=result['confidence'],
            sources=sources
        )

    except HTTPException:
        raise
    except ChatError as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ==================== Chat History ====================

@app.get("/chat/history")
async def get_history():
    """Returns full conversation history."""
    try:
        if not app_state.initialized or app_state.chat_engine is None:
            raise HTTPException(status_code=503, detail="Chat engine not initialized")

        history = app_state.chat_engine.get_history()
        return {
            "status": "success",
            "history_length": len(history),
            "messages": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/chat/clear", response_model=HistoryClearResponse)
async def clear_history():
    """Clears conversation history for a fresh session."""
    try:
        if not app_state.initialized or app_state.chat_engine is None:
            raise HTTPException(status_code=503, detail="Chat engine not initialized")

        app_state.chat_engine.clear_history()
        return HistoryClearResponse(
            status="success",
            message="Conversation history cleared"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ==================== Collection Management ====================

@app.post("/collection/clear")
async def clear_collection():
    """Clears all documents from vector database. Cannot be undone."""
    try:
        if not app_state.initialized or app_state.rag_pipeline is None:
            raise HTTPException(status_code=503, detail="RAG pipeline not initialized")

        app_state.rag_pipeline.clear_collection()

        # Also clear chat history when collection is cleared
        if app_state.chat_engine:
            app_state.chat_engine.clear_history()

        return {"status": "success", "message": "Collection cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/collection/stats")
async def collection_stats():
    """Returns ChromaDB collection statistics."""
    try:
        if not app_state.initialized or app_state.rag_pipeline is None:
            raise HTTPException(status_code=503, detail="RAG pipeline not initialized")

        stats = app_state.rag_pipeline.get_collection_stats()
        return {"status": "success", "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ==================== Info & Root ====================

@app.get("/info")
async def info():
    """Returns application info and available endpoints."""
    return {
        "name": "RAG Healthcare Chat Application",
        "version": "1.0.0",
        "initialized": app_state.initialized,
        "endpoints": {
            "health": "GET /health",
            "ingest": "POST /ingest",
            "chat": "POST /chat",
            "history": "GET /chat/history",
            "clear_history": "POST /chat/clear",
            "stats": "GET /collection/stats",
            "clear_collection": "POST /collection/clear"
        }
    }


@app.get("/")
async def root():
    """Root endpoint — points to docs."""
    return {
        "name": "RAG Healthcare Chat API",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


# ==================== Run ====================

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))

    print(f"\n📡 Starting server on {host}:{port}")
    print(f"📖 Docs at http://localhost:{port}/docs")

    # reload=True auto restarts on code changes during development
    uvicorn.run("main:app", host=host, port=port, reload=True)