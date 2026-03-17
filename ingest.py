"""
Document ingestion module for RAG application.

Handles PDF loading, text extraction, and chunking using LangChain's
RecursiveCharacterTextSplitter with comprehensive error handling.
"""

import os
from pathlib import Path
from typing import List
from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter


class DocumentIngestionError(Exception):
    """Custom exception for document ingestion errors."""
    pass


def validate_pdf_file(file_path: str, max_size_mb: int = 50) -> None:
    """
    Validate that a PDF file exists and meets size requirements.
    
    Args:
        file_path: Path to the PDF file
        max_size_mb: Maximum allowed file size in megabytes
        
    Raises:
        DocumentIngestionError: If file doesn't exist or exceeds size limit
    """
    if not os.path.exists(file_path):
        raise DocumentIngestionError(f"PDF file not found: {file_path}")
    
    if not file_path.lower().endswith('.pdf'):
        raise DocumentIngestionError(f"File is not a PDF: {file_path}")
    
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise DocumentIngestionError(
            f"PDF file exceeds size limit ({file_size_mb:.2f}MB > {max_size_mb}MB)"
        )


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text content from all pages of a PDF document.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text from all pages
        
    Raises:
        DocumentIngestionError: If PDF reading fails or no text is extracted
    """
    try:
        validate_pdf_file(file_path)
        
        pdf_reader = PdfReader(file_path)
        
        if len(pdf_reader.pages) == 0:
            raise DocumentIngestionError("PDF file contains no pages")
        
        extracted_text = ""
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            try:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += f"\n--- Page {page_num} ---\n{page_text}"
                else:
                    # Log warning but continue processing
                    print(f"Warning: No text extracted from page {page_num}")
            except Exception as e:
                raise DocumentIngestionError(
                    f"Failed to extract text from page {page_num}: {str(e)}"
                )
        
        if not extracted_text.strip():
            raise DocumentIngestionError("No text content extracted from PDF")
        
        return extracted_text
        
    except DocumentIngestionError:
        raise
    except Exception as e:
        raise DocumentIngestionError(f"Unexpected error during PDF extraction: {str(e)}")


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[str]:
    """
    Split text into chunks using RecursiveCharacterTextSplitter.
    
    This approach preserves semantic boundaries by splitting on paragraphs,
    sentences, and words in that order.
    
    Args:
        text: The text content to chunk
        chunk_size: Maximum size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
        
    Raises:
        DocumentIngestionError: If chunking fails or produces no chunks
    """
    try:
        if not text or not text.strip():
            raise DocumentIngestionError("Input text is empty")
        
        if chunk_size <= 0:
            raise DocumentIngestionError("chunk_size must be positive")
        
        if chunk_overlap >= chunk_size:
            raise DocumentIngestionError(
                "chunk_overlap must be less than chunk_size"
            )
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = splitter.split_text(text)
        
        if not chunks:
            raise DocumentIngestionError("No chunks produced from text splitting")
        
        return chunks
        
    except DocumentIngestionError:
        raise
    except Exception as e:
        raise DocumentIngestionError(f"Text chunking failed: {str(e)}")


def ingest_document(
    file_path: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    max_file_size_mb: int = 50
) -> List[str]:
    """
    Main ingestion pipeline: load PDF, extract text, and chunk document.
    
    Args:
        file_path: Path to the PDF file
        chunk_size: Maximum size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
        max_file_size_mb: Maximum allowed file size in megabytes
        
    Returns:
        List of processed text chunks ready for embedding
        
    Raises:
        DocumentIngestionError: If any step in the pipeline fails
    """
    try:
        print(f"Starting document ingestion: {file_path}")
        
        # Validate file
        validate_pdf_file(file_path, max_file_size_mb)
        print(f"✓ File validation passed")
        
        # Extract text
        text = extract_text_from_pdf(file_path)
        print(f"✓ Text extracted ({len(text)} characters)")
        
        # Chunk text
        chunks = chunk_text(text, chunk_size, chunk_overlap)
        print(f"✓ Text chunked into {len(chunks)} chunks")
        
        return chunks
        
    except DocumentIngestionError as e:
        print(f"✗ Ingestion failed: {str(e)}")
        raise
    except Exception as e:
        error_msg = f"Unexpected error during document ingestion: {str(e)}"
        print(f"✗ {error_msg}")
        raise DocumentIngestionError(error_msg)


if __name__ == "__main__":
    # Example usage
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        try:
            chunks = ingest_document(pdf_path)
            print(f"\nSuccessfully ingested {len(chunks)} chunks")
            print(f"First chunk preview: {chunks[0][:200]}...")
        except DocumentIngestionError as e:
            print(f"Error: {e}")
    else:
        print("Usage: python ingest.py <path_to_pdf>")
