"""
Document ingestion module for RAG application.
Handles PDF loading, text extraction, and chunking.
No LangChain dependency — custom text splitter implementation.
"""

import os
from pathlib import Path
from typing import List
from pypdf import PdfReader


class DocumentIngestionError(Exception):
    """Custom exception for document ingestion errors."""
    pass


def validate_pdf_file(file_path: str, max_size_mb: int = 50) -> None:
    """
    Validate PDF file exists and meets size requirements.
    
    Args:
        file_path: Path to PDF file
        max_size_mb: Maximum allowed file size in MB
        
    Raises:
        DocumentIngestionError: If validation fails
    """
    # Check file exists
    if not os.path.exists(file_path):
        raise DocumentIngestionError(f"PDF file not found: {file_path}")
    
    # Check file is PDF
    if not file_path.lower().endswith('.pdf'):
        raise DocumentIngestionError(f"File is not a PDF: {file_path}")
    
    # Check file size
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise DocumentIngestionError(
            f"PDF exceeds size limit ({file_size_mb:.2f}MB > {max_size_mb}MB)"
        )


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from all pages of a PDF document.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Full extracted text string
        
    Raises:
        DocumentIngestionError: If extraction fails
    """
    try:
        validate_pdf_file(file_path)
        
        reader = PdfReader(file_path)
        
        # Check PDF has pages
        if len(reader.pages) == 0:
            raise DocumentIngestionError("PDF contains no pages")
        
        extracted_text = ""
        
        # Loop through every page and extract text
        for page_num, page in enumerate(reader.pages, 1):
            try:
                page_text = page.extract_text()
                if page_text:
                    # Add page marker for context
                    extracted_text += f"\n--- Page {page_num} ---\n{page_text}"
                else:
                    print(f"Warning: No text on page {page_num}")
            except Exception as e:
                raise DocumentIngestionError(
                    f"Failed to extract page {page_num}: {str(e)}"
                )
        
        # Validate we got something
        if not extracted_text.strip():
            raise DocumentIngestionError("No text extracted from PDF")
        
        return extracted_text
        
    except DocumentIngestionError:
        raise
    except Exception as e:
        raise DocumentIngestionError(f"PDF extraction error: {str(e)}")


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[str]:
    """
    Split text into overlapping chunks.
    Custom implementation — no LangChain needed.
    
    Args:
        text: Text to split
        chunk_size: Max characters per chunk
        chunk_overlap: Overlapping characters between chunks
        
    Returns:
        List of text chunks
        
    Raises:
        DocumentIngestionError: If chunking fails
    """
    try:
        # Validate inputs
        if not text or not text.strip():
            raise DocumentIngestionError("Input text is empty")
        
        if chunk_size <= 0:
            raise DocumentIngestionError("chunk_size must be positive")
        
        if chunk_overlap >= chunk_size:
            raise DocumentIngestionError(
                "chunk_overlap must be less than chunk_size"
            )
        
        chunks = []
        start = 0
        text_length = len(text)
        
        # Slide through text with overlap
        while start < text_length:
            # Get end position of this chunk
            end = start + chunk_size
            
            # Get the chunk
            chunk = text[start:end]
            
            # Only add non-empty chunks
            if chunk.strip():
                chunks.append(chunk.strip())
            
            # Move start forward by chunk_size minus overlap
            # This creates the overlap between consecutive chunks
            start += chunk_size - chunk_overlap
        
        if not chunks:
            raise DocumentIngestionError("No chunks produced")
        
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
    Main pipeline — load PDF, extract text, chunk it.
    
    Args:
        file_path: Path to PDF file
        chunk_size: Max characters per chunk
        chunk_overlap: Overlap between chunks
        max_file_size_mb: Max allowed file size
        
    Returns:
        List of text chunks ready for embedding
        
    Raises:
        DocumentIngestionError: If any step fails
    """
    try:
        print(f"Starting ingestion: {file_path}")
        
        # Step 1 — validate file
        validate_pdf_file(file_path, max_file_size_mb)
        print(f"✓ File validated")
        
        # Step 2 — extract text
        text = extract_text_from_pdf(file_path)
        print(f"✓ Text extracted ({len(text)} characters)")
        
        # Step 3 — chunk text
        chunks = chunk_text(text, chunk_size, chunk_overlap)
        print(f"✓ Created {len(chunks)} chunks")
        
        return chunks
        
    except DocumentIngestionError as e:
        print(f"✗ Ingestion failed: {str(e)}")
        raise
    except Exception as e:
        error_msg = f"Unexpected ingestion error: {str(e)}"
        print(f"✗ {error_msg}")
        raise DocumentIngestionError(error_msg)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        try:
            chunks = ingest_document(sys.argv[1])
            print(f"\n✓ Successfully created {len(chunks)} chunks")
            print(f"Preview: {chunks[0][:200]}...")
        except DocumentIngestionError as e:
            print(f"Error: {e}")
    else:
        print("Usage: python ingest.py <path_to_pdf>")