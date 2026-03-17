"""
Quick start guide and testing script for RAG Healthcare Chat Application.

Run this script to verify the installation and test basic functionality.
"""

import os
import sys
from pathlib import Path


def print_header(text: str):
    """Print formatted header."""
    print(f"\n{'='*60}")
    print(f"{'█ ' + text:^60}")
    print(f"{'='*60}\n")


def check_python_version():
    """Check Python version."""
    print_header("Checking Python Version")
    
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    print(f"Python Version: {version}")
    
    if sys.version_info.major >= 3 and sys.version_info.minor >= 9:
        print("✓ Python version is compatible")
        return True
    else:
        print("✗ Python 3.9+ required")
        return False


def check_dependencies():
    """Check if all required dependencies are installed."""
    print_header("Checking Dependencies")
    
    dependencies = {
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'pydantic': 'Pydantic',
        'pypdf': 'PyPDF',
        'sentence_transformers': 'SentenceTransformer',
        'chromadb': 'ChromaDB',
        'langchain': 'LangChain',
        'dotenv': 'python-dotenv'
    }
    
    missing = []
    installed = []
    
    for module, name in dependencies.items():
        try:
            __import__(module)
            installed.append(name)
            print(f"✓ {name}")
        except ImportError:
            missing.append(name)
            print(f"✗ {name}")
    
    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print("\nRun: pip install -r requirements.txt")
        return False
    
    print(f"\n✓ All {len(installed)} dependencies installed")
    return True


def check_project_structure():
    """Check if project structure is correct."""
    print_header("Checking Project Structure")
    
    required_files = {
        'ingest.py': 'Document ingestion module',
        'rag.py': 'RAG pipeline module',
        'chat.py': 'Chat orchestration module',
        'main.py': 'FastAPI application',
        '.env': 'Environment configuration',
        'requirements.txt': 'Python dependencies'
    }
    
    required_dirs = {
        'data': 'PDF storage directory',
        'chroma_store': 'Vector database directory'
    }
    
    all_ok = True
    
    # Check files
    print("Files:")
    for file, description in required_files.items():
        if os.path.exists(file):
            print(f"✓ {file:20} ({description})")
        else:
            print(f"✗ {file:20} ({description})")
            all_ok = False
    
    # Check directories
    print("\nDirectories:")
    for dir_name, description in required_dirs.items():
        if os.path.isdir(dir_name):
            print(f"✓ {dir_name:20} ({description})")
        else:
            print(f"✗ {dir_name:20} ({description})")
            # Create if missing
            Path(dir_name).mkdir(parents=True, exist_ok=True)
            print(f"  → Created")
    
    return all_ok


def test_imports():
    """Test if core modules can be imported."""
    print_header("Testing Module Imports")
    
    modules = {
        'ingest': 'Document ingestion',
        'rag': 'RAG pipeline',
        'chat': 'Chat engine',
        'main': 'FastAPI app'
    }
    
    all_ok = True
    
    for module, description in modules.items():
        try:
            __import__(module)
            print(f"✓ {module:15} ({description})")
        except Exception as e:
            print(f"✗ {module:15} ({description})")
            print(f"  Error: {str(e)}")
            all_ok = False
    
    return all_ok


def test_rag_pipeline():
    """Test RAG pipeline initialization."""
    print_header("Testing RAG Pipeline")
    
    try:
        from rag import RAGPipeline, RAGError
        
        print("Initializing RAG pipeline...")
        rag = RAGPipeline(
            embedding_model_name="all-MiniLM-L6-v2",
            db_path="./chroma_store",
            collection_name="Humana_chat_docs"
        )
        
        stats = rag.get_collection_stats()
        
        print(f"✓ RAG pipeline initialized")
        print(f"\n  Collection Stats:")
        print(f"  - Name: {stats['collection_name']}")
        print(f"  - Documents: {stats['total_documents']}")
        print(f"  - Embedding Dimension: {stats['embedding_model']}")
        
        return True
        
    except Exception as e:
        print(f"✗ RAG pipeline test failed: {str(e)}")
        return False


def test_document_ingestion():
    """Test document ingestion with sample text."""
    print_header("Testing Document Ingestion")
    
    try:
        from ingest import chunk_text
        
        sample_text = """
        This is a sample healthcare document.
        It contains information about patients and medical procedures.
        """ * 50
        
        print(f"Input text size: {len(sample_text)} characters")
        
        chunks = chunk_text(sample_text, chunk_size=1000, chunk_overlap=200)
        
        print(f"✓ Text successfully chunked")
        print(f"\n  Chunking Stats:")
        print(f"  - Number of chunks: {len(chunks)}")
        print(f"  - Avg chunk size: {sum(len(c) for c in chunks) // len(chunks)} chars")
        print(f"  - First chunk: {chunks[0][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ Document ingestion test failed: {str(e)}")
        return False


def display_next_steps():
    """Display next steps."""
    print_header("Next Steps")
    
    print("""
1. Upload a PDF document:
   curl -X POST "http://localhost:8000/ingest" \\
     -F "file=@your_document.pdf"

2. Query the document:
   curl -X POST "http://localhost:8000/chat" \\
     -H "Content-Type: application/json" \\
     -d '{"query": "Your question here"}'

3. View interactive API docs:
   http://localhost:8000/docs

4. Check application health:
   curl http://localhost:8000/health
    """)


def main():
    """Run all checks and tests."""
    print("\n")
    print("╔" + "═"*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "RAG Healthcare Chat Application - Setup Verification".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "═"*58 + "╝")
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Project Structure", check_project_structure),
        ("Module Imports", test_imports),
        ("RAG Pipeline", test_rag_pipeline),
        ("Document Ingestion", test_document_ingestion),
    ]
    
    results = []
    
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Unexpected error: {str(e)}")
            results.append((name, False))
    
    # Summary
    print_header("Verification Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:10} | {name}")
    
    print(f"\n{'─'*40}")
    print(f"{'Result:':10} | {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✓ All checks passed! Ready to run the application.")
        
        display_next_steps()
        
        print("\nTo start the server, run:")
        print("  python main.py")
        
        return 0
    else:
        print("\n✗ Some checks failed. Please review the errors above.")
        print("\nFor help, check README.md or troubleshooting section.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
