"""
FastAPI application for RAG-powered healthcare chat.

Provides REST API endpoints for document upload, ingestion, and chat interactions.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

from ingest import ingest_document, DocumentIngestionError
from rag import RAGPipeline, RAGError
from chat import RAGChat, ChatError


# Load environment variables
load_dotenv()


# ==================== Pydantic Models ====================

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    query: str = Field(..., min_length=1, max_length=5000)
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    include_sources: bool = Field(default=True)
    
    class Config:
        example = {
            "query": "What are the medication side effects?",
            "top_k": 5,
            "score_threshold": 0.3,
            "include_sources": True
        }


class SourceChunk(BaseModel):
    """Source document chunk from retrieval."""
    content: str
    relevance_score: float
    rank: int


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    answer: str
    sources_count: int
    confidence: float
    sources: Optional[List[SourceChunk]] = None
    
    class Config:
        example = {
            "answer": "The medication has the following side effects...",
            "sources_count": 3,
            "confidence": 0.85,
            "sources": [
                {
                    "content": "Example content...",
                    "relevance_score": 0.92,
                    "rank": 1
                }
            ]
        }


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
    """Response model for clear history endpoint."""
    status: str
    message: str


# ==================== Application Setup ====================

app = FastAPI(
    title="RAG Healthcare Chat API",
    description="A retrieval-augmented generation (RAG) chatbot for healthcare documents",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Global State ====================

class AppState:
    """Application state holder."""
    rag_pipeline: Optional[RAGPipeline] = None
    chat_engine: Optional[RAGChat] = None
    initialized: bool = False


app_state = AppState()


# ==================== Initialization ====================

@app.on_event("startup")
async def startup_event():
    """
    Initialize RAG pipeline and chat engine on application startup.
    
    Raises:
        Exception: If initialization fails
    """
    try:
        print("\n" + "="*50)
        print("🚀 Starting RAG Healthcare Chat Application")
        print("="*50)
        
        # Get configuration from environment
        embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        db_path = os.getenv("CHROMA_DB_PATH", "./chroma_store")
        collection_name = os.getenv("COLLECTION_NAME", "Humana_chat_docs")
        
        # Initialize RAG pipeline
        print(f"\n📊 Initializing RAG Pipeline...")
        app_state.rag_pipeline = RAGPipeline(
            embedding_model_name=embedding_model,
            db_path=db_path,
            collection_name=collection_name
        )
        
        # Initialize Chat engine (without LLM for now)
        print(f"\n💬 Initializing Chat Engine...")
        app_state.chat_engine = RAGChat(
            rag_pipeline=app_state.rag_pipeline,
            llm_model=None  # LLM to be integrated
        )
        
        app_state.initialized = True
        
        print("\n" + "="*50)
        print("✓ Application ready for requests")
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"\n✗ Startup failed: {str(e)}")
        raise


# ==================== Health Check ====================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        HealthResponse with application status
    """
    try:
        if not app_state.initialized or app_state.rag_pipeline is None:
            return HealthResponse(
                status="not_ready",
                rag_initialized=False
            )
        
        stats = app_state.rag_pipeline.get_collection_stats()
        
        return HealthResponse(
            status="healthy",
            rag_initialized=True,
            collection_stats=stats
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )


# ==================== Document Ingestion ====================

@app.post("/ingest", response_model=IngestResponse)
async def ingest_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Upload and ingest a PDF document.
    
    Args:
        file: PDF file to ingest
        background_tasks: Background task handler
        
    Returns:
        IngestResponse with ingestion status
        
    Raises:
        HTTPException: If file is invalid or ingestion fails
    """
    try:
        # Validate RAG pipeline
        if not app_state.initialized or app_state.rag_pipeline is None:
            raise HTTPException(
                status_code=503,
                detail="RAG pipeline not initialized"
            )
        
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required"
            )
        
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported"
            )
        
        # Create data directory if it doesn't exist
        data_dir = os.getenv("PDF_DATA_FOLDER", "./data")
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        
        # Save uploaded file
        file_path = os.path.join(data_dir, file.filename)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        print(f"\n📄 Ingesting file: {file.filename}")
        
        # Ingest document
        chunks = ingest_document(
            file_path,
            chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
            max_file_size_mb=int(os.getenv("MAX_PDF_SIZE_MB", "50"))
        )
        
        # Store in RAG pipeline
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
        raise HTTPException(
            status_code=400,
            detail=f"Document ingestion error: {str(e)}"
        )
    except RAGError as e:
        raise HTTPException(
            status_code=500,
            detail=f"RAG pipeline error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


# ==================== Chat Endpoints ====================

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a user query using RAG pipeline.
    
    Query is answered based ONLY on ingested documents.
    No hallucination - if answer not in document, model states so.
    
    Args:
        request: ChatRequest with user query
        
    Returns:
        ChatResponse with answer and sources
        
    Raises:
        HTTPException: If chat fails or RAG not initialized
    """
    try:
        # Validate RAG pipeline and chat engine
        if not app_state.initialized or app_state.chat_engine is None:
            raise HTTPException(
                status_code=503,
                detail="Chat engine not initialized"
            )
        
        # Check if documents are loaded
        stats = app_state.rag_pipeline.get_collection_stats()
        if stats['total_documents'] == 0:
            raise HTTPException(
                status_code=400,
                detail="No documents ingested yet. Please upload a PDF first."
            )
        
        # Process query
        result = app_state.chat_engine.answer_query(
            query=request.query,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            include_sources=request.include_sources
        )
        
        # Build response
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
        raise HTTPException(
            status_code=500,
            detail=f"Chat error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@app.get("/chat/history")
async def get_history():
    """
    Get conversation history.
    
    Returns:
        List of messages in conversation
    """
    try:
        if not app_state.initialized or app_state.chat_engine is None:
            raise HTTPException(
                status_code=503,
                detail="Chat engine not initialized"
            )
        
        history = app_state.chat_engine.get_history()
        return {
            "status": "success",
            "history_length": len(history),
            "messages": history
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving history: {str(e)}"
        )


@app.post("/chat/clear", response_model=HistoryClearResponse)
async def clear_history():
    """
    Clear conversation history.
    
    Returns:
        HistoryClearResponse with status
    """
    try:
        if not app_state.initialized or app_state.chat_engine is None:
            raise HTTPException(
                status_code=503,
                detail="Chat engine not initialized"
            )
        
        app_state.chat_engine.clear_history()
        
        return HistoryClearResponse(
            status="success",
            message="Conversation history cleared"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing history: {str(e)}"
        )


# ==================== Collection Management ====================

@app.post("/collection/clear")
async def clear_collection():
    """
    Clear all documents from the vector collection.
    
    ⚠️ WARNING: This operation cannot be undone.
    
    Returns:
        Status response
    """
    try:
        if not app_state.initialized or app_state.rag_pipeline is None:
            raise HTTPException(
                status_code=503,
                detail="RAG pipeline not initialized"
            )
        
        app_state.rag_pipeline.clear_collection()
        
        # Clear chat history as well
        if app_state.chat_engine:
            app_state.chat_engine.clear_history()
        
        return {
            "status": "success",
            "message": "Collection cleared successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing collection: {str(e)}"
        )


@app.get("/collection/stats")
async def collection_stats():
    """
    Get statistics about the vector collection.
    
    Returns:
        Collection statistics
    """
    try:
        if not app_state.initialized or app_state.rag_pipeline is None:
            raise HTTPException(
                status_code=503,
                detail="RAG pipeline not initialized"
            )
        
        stats = app_state.rag_pipeline.get_collection_stats()
        
        return {
            "status": "success",
            "data": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting stats: {str(e)}"
        )


# ==================== Info Endpoints ====================

@app.get("/info")
async def info():
    """
    Get application information.
    
    Returns:
        Application info and configuration
    """
    return {
        "name": "RAG Healthcare Chat Application",
        "version": "1.0.0",
        "status": "running",
        "initialized": app_state.initialized,
        "endpoints": {
            "health": "GET /health",
            "ingest_document": "POST /ingest",
            "chat": "POST /chat",
            "chat_history": "GET /chat/history",
            "clear_history": "POST /chat/clear",
            "collection_stats": "GET /collection/stats",
            "clear_collection": "POST /collection/clear"
        }
    }


# ==================== Root Endpoint ====================

@app.get("/")
async def root():
    """Root endpoint with documentation link."""
    return {
        "name": "RAG Healthcare Chat API",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


# ==================== Run Application ====================

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    debug = os.getenv("API_DEBUG", "False").lower() == "true"
    
    print(f"\n📡 Starting FastAPI server on {host}:{port}")
    print(f"📖 Docs available at http://{host}:{port}/docs")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        debug=debug
    )
