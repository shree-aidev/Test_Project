"""
Integration tests for RAG Healthcare Chat Application.

Tests core functionality of ingest, RAG, and chat modules.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from ingest import (
    ingest_document,
    extract_text_from_pdf,
    chunk_text,
    validate_pdf_file,
    DocumentIngestionError
)
from rag import RAGPipeline, RAGError
from chat import RAGChat, ChatError


# ==================== Ingest Tests ====================

class TestDocumentIngestion:
    """Tests for document ingestion module."""
    
    def test_chunk_text_basic(self):
        """Test basic text chunking."""
        text = "This is a sample text. " * 100
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert all(len(chunk) <= 150 for chunk in chunks)  # With overlap
    
    def test_chunk_text_empty_text(self):
        """Test chunking with empty text."""
        with pytest.raises(DocumentIngestionError):
            chunk_text("")
    
    def test_chunk_text_invalid_parameters(self):
        """Test chunking with invalid parameters."""
        text = "Sample text" * 10
        
        # Invalid chunk_size
        with pytest.raises(DocumentIngestionError):
            chunk_text(text, chunk_size=-1)
        
        # Invalid overlap
        with pytest.raises(DocumentIngestionError):
            chunk_text(text, chunk_size=100, chunk_overlap=150)
    
    def test_validate_pdf_file_nonexistent(self):
        """Test validation with non-existent file."""
        with pytest.raises(DocumentIngestionError):
            validate_pdf_file("nonexistent.pdf")
    
    def test_validate_pdf_file_wrong_extension(self):
        """Test validation with wrong file extension."""
        with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
            with pytest.raises(DocumentIngestionError):
                validate_pdf_file(tmp.name)


# ==================== RAG Tests ====================

class TestRAGPipeline:
    """Tests for RAG pipeline module."""
    
    @patch('rag.SentenceTransformer')
    @patch('rag.chromadb.Client')
    def test_rag_initialization(self, mock_client, mock_transformer):
        """Test RAG pipeline initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rag = RAGPipeline(db_path=tmpdir)
            
            assert rag.embedding_model is not None
            assert rag.chroma_client is not None
            assert rag.collection is not None
    
    @patch('rag.SentenceTransformer')
    @patch('rag.chromadb.Client')
    def test_rag_store_documents(self, mock_client, mock_transformer):
        """Test storing documents in RAG."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rag = RAGPipeline(db_path=tmpdir)
            
            # Mock the collection methods
            rag.collection.add = Mock()
            rag.collection.count = Mock(return_value=0)
            
            chunks = ["Sample chunk 1", "Sample chunk 2"]
            rag.store_documents(chunks, metadata={"filename": "test.pdf"})
            
            rag.collection.add.assert_called_once()
    
    @patch('rag.SentenceTransformer')
    @patch('rag.chromadb.Client')
    def test_rag_retrieve_chunks_empty(self, mock_client, mock_transformer):
        """Test retrieval from empty collection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rag = RAGPipeline(db_path=tmpdir)
            
            # Mock empty collection
            rag.collection.count = Mock(return_value=0)
            rag.collection.query = Mock(return_value={'documents': [[]], 'metadatas': [[]], 'distances': [[]]})
            
            result = rag.retrieve_relevant_chunks("test query")
            
            # Should return empty list for empty collection
            assert isinstance(result, list)


# ==================== Chat Tests ====================

class TestRAGChat:
    """Tests for chat module."""
    
    @patch('rag.SentenceTransformer')
    @patch('rag.chromadb.Client')
    def test_chat_initialization(self, mock_client, mock_transformer):
        """Test chat engine initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rag = RAGPipeline(db_path=tmpdir)
            chat = RAGChat(rag)
            
            assert chat.rag_pipeline is not None
            assert chat.conversation_history == []
    
    @patch('rag.SentenceTransformer')
    @patch('rag.chromadb.Client')
    def test_chat_empty_query(self, mock_client, mock_transformer):
        """Test chat with empty query."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rag = RAGPipeline(db_path=tmpdir)
            chat = RAGChat(rag)
            
            with pytest.raises(ChatError):
                chat.answer_query("")
    
    @patch('rag.SentenceTransformer')
    @patch('rag.chromadb.Client')
    def test_chat_history_management(self, mock_client, mock_transformer):
        """Test conversation history management."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rag = RAGPipeline(db_path=tmpdir)
            chat = RAGChat(rag)
            
            # Add messages
            chat.conversation_history.append({'role': 'user', 'content': 'Hello'})
            chat.conversation_history.append({'role': 'assistant', 'content': 'Hi'})
            
            # Check history
            history = chat.get_history()
            assert len(history) == 2
            
            # Clear history
            chat.clear_history()
            assert len(chat.get_history()) == 0


# ==================== Run Tests ====================

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
