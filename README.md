# 🏥 RAG-Powered Healthcare Chat Application

A production-grade Retrieval-Augmented Generation (RAG) chatbot for healthcare document analysis. Upload PDF documents and chat with them via REST API — all answers grounded **ONLY** in document content to eliminate hallucinations.

---

## 🎯 Key Features

| Feature | Description |
|---------|-------------|
| 📄 PDF Upload | Validates and extracts text from healthcare PDFs |
| 🧠 Semantic Chunking | Intelligent text splitting with overlap using LangChain |
| 🔍 Vector Embeddings | HuggingFace SentenceTransformer (all-MiniLM-L6-v2) |
| 💾 Persistent Vector DB | ChromaDB with cosine similarity search |
| 🎯 RAG Pipeline | Answers grounded ONLY in document — no hallucinations |
| 💬 Conversation Memory | Context-aware multi-turn chat with full history |
| 🔌 REST API | FastAPI with Pydantic validation |
| ⚡ Production Ready | Docker support, error handling, full documentation |

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|------------|
| Web API | FastAPI |
| Server | Uvicorn |
| Validation | Pydantic |
| Embeddings | SentenceTransformer (all-MiniLM-L6-v2) |
| Vector DB | ChromaDB (persistent, cosine similarity) |
| PDF Processing | PyPDF |
| Chunking | LangChain RecursiveCharacterTextSplitter |
| LLM | Google Gemini (gemini-pro) |
| Container | Docker & Docker Compose |

---

## 📁 Project Structure
```
humanaproj/
├── main.py                 # FastAPI REST API — all endpoints
├── ingest.py               # PDF reading and text chunking
├── rag.py                  # Embeddings and ChromaDB vector storage
├── chat.py                 # Gemini chat with conversation memory
├── .env                    # Environment variables (API keys)
├── requirements.txt        # Python dependencies
├── setup.bat               # Windows automated setup
├── setup.sh                # Linux/Mac automated setup
├── quickstart.py           # Installation verification
├── test_integration.py     # Integration tests
├── API_EXAMPLES.py         # Advanced usage examples
├── Dockerfile              # Container image
├── docker-compose.yml      # Container orchestration
├── data/                   # Uploaded PDFs stored here
└── chroma_store/           # ChromaDB vectors stored here
```

---

## ⚡ Quick Start

### Windows
```powershell
# 1. Activate virtual environment
venv\Scripts\activate

# 2. Verify installation
python quickstart.py

# 3. Start the API
python main.py
```

### Linux/Mac
```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Verify installation
python quickstart.py

# 3. Start the API
python main.py
```

---

## 🔑 Environment Setup

Create a `.env` file in the root directory:
```env
# Google Gemini API Key
GOOGLE_API_KEY=your_gemini_api_key_here

# Embeddings
EMBEDDING_MODEL=all-MiniLM-L6-v2

# ChromaDB
CHROMA_DB_PATH=./chroma_store
COLLECTION_NAME=humana_chat_docs

# API
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=False

# PDF
PDF_DATA_FOLDER=./data
MAX_PDF_SIZE_MB=50

# Chunking
CHUNK_SIZE=500
CHUNK_OVERLAP=50
```

Get your free Gemini API key at: https://aistudio.google.com/app/apikey

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Check API is running |
| POST | `/ingest` | Upload and process a PDF |
| POST | `/chat` | Ask a question about the document |
| POST | `/reset` | Clear conversation history |
| GET | `/chat/history` | View full conversation history |
| GET | `/collection/stats` | View ChromaDB statistics |

---

## 📖 API Usage

### Interactive Docs
Start the server and open:
```
http://localhost:8000/docs
```

### Example Workflow
```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Upload PDF
curl -X POST "http://localhost:8000/ingest" \
  -F "file=@healthcare_document.pdf"

# 3. Chat with document
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the Medicare coverage?"}'

# 4. Reset conversation
curl -X POST "http://localhost:8000/reset"
```

---

## 🔄 How It Works
```
User uploads PDF
      ↓
ingest.py — reads, cleans, chunks text
      ↓
rag.py — generates embeddings, stores in ChromaDB
      ↓
User asks a question via /chat endpoint
      ↓
rag.py — embeds question, finds top 3 similar chunks
      ↓
chat.py — builds prompt with context + conversation history
      ↓
Google Gemini — generates grounded answer
      ↓
FastAPI — returns answer + source pages to user
```

---

## 🐳 Docker Deployment
```bash
# Build image
docker build -t rag-healthcare-chat:latest .

# Run with Docker Compose
docker-compose up -d

# Access API
http://localhost:8000/docs
```

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| Max PDF Size | 50 MB |
| Chunk Size | 500 chars |
| Chunk Overlap | 50 chars |
| Embedding Dimensions | 384 |
| Default Results (top_k) | 3 chunks |
| Similarity Metric | Cosine Distance |

---

## 🔐 Security

- Environment-based API key management (never hardcoded)
- PDF file type and size validation
- Pydantic request/response validation
- HTTP exception handling with meaningful errors
- CORS middleware support

---

## 🔧 Troubleshooting

**Module not found error**
```bash
pip install -r requirements.txt --force-reinstall
```

**ChromaDB ProcessPoolExecutor warning**
Normal on first run — ChromaDB handles it automatically.

**Slow first run**
Expected — downloads embedding model (~100MB). Cached on subsequent runs.

**API key error**
Check your `.env` file has a valid `GOOGLE_API_KEY`

---

## ✅ Quality Standards

- 100% function docstring coverage
- All edge cases handled
- Meaningful error messages throughout
- Integration tests included
- Production-ready Docker support
- Clean, commented, readable code

---

## 🚀 Production Deployment
```bash
# Using Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

For full deployment guide see [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 📝 Version

**v1.0.0** — March 17, 2026
Python 3.9+ | Status: ✅ Production Ready

---

Built with ❤️ for healthcare document analysis