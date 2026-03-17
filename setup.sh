#!/bin/bash

# Setup script for RAG Healthcare Chat Application on Linux/Mac

set -e  # Exit on error

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║   RAG Healthcare Chat Application - Setup Script       ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Check Python
echo "[1/4] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    exit 1
fi
python3 --version
echo "✓ Python found"
echo ""

# Create virtual environment
echo "[2/4] Setting up virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists, skipping creation"
else python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment"
        exit 1
    fi
fi
echo "✓ Virtual environment ready"
echo ""

# Activate virtual environment
echo "[3/4] Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment"
    exit 1
fi
echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "[4/4] Installing dependencies..."
pip install --upgrade pip setuptools wheel > /dev/null
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi
echo "✓ Dependencies installed"
echo ""

# Create necessary directories
echo "Creating required directories..."
mkdir -p data
mkdir -p chroma_store
echo "✓ Directories created"
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << 'EOF'
# RAG Healthcare Chat Application Configuration

# LLM Configuration
LLAMA_MODEL_PATH=./models/llama-model
TEMPERATURE=0.7
MAX_TOKENS=500

# Embeddings Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2

# ChromaDB Configuration
CHROMA_DB_PATH=./chroma_store
COLLECTION_NAME=Humana_chat_docs

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=False

# PDF Configuration
PDF_DATA_FOLDER=./data
MAX_PDF_SIZE_MB=50

# Chunking Configuration
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
EOF
fi
echo "✓ Configuration ready"
echo ""

echo "╔════════════════════════════════════════════════════════╗"
echo "║         Setup Complete! Next Steps:                   ║"
echo "║                                                        ║"
echo "║  1. Activate the virtual environment (if needed):     ║"
echo "║     source venv/bin/activate                          ║"
echo "║                                                        ║"
echo "║  2. Run the quick verification:                       ║"
echo "║     python quickstart.py                              ║"
echo "║                                                        ║"
echo "║  3. Start the application:                            ║"
echo "║     python main.py                                    ║"
echo "║                                                        ║"
echo "║  4. Access the API docs:                              ║"
echo "║     http://localhost:8000/docs                        ║"
echo "║                                                        ║"
echo "║  5. Upload a PDF document to test                     ║"
echo "║                                                        ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
