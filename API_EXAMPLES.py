"""
Advanced API Usage Examples for RAG Healthcare Chat Application

This file contains comprehensive examples for using the RAG Chat API
at an advanced level.
"""

# ==================== Python Examples ====================

# Example 1: Using the API with Python requests
# ============================================

def example_python_client():
    """Example of using the RAG Chat API with Python requests library."""
    
    import requests
    import json
    
    # API base URL
    BASE_URL = "http://localhost:8000"
    
    # 1. Upload a PDF
    print("1. Uploading PDF document...")
    with open("healthcare_document.pdf", "rb") as f:
        files = {"file": f}
        response = requests.post(f"{BASE_URL}/ingest", files=files)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # 2. Chat with the document
    print("\n2. Asking a question...")
    chat_request = {
        "query": "What are the side effects of the medication?",
        "top_k": 5,
        "score_threshold": 0.3,
        "include_sources": True
    }
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json=chat_request,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    chat_response = response.json()
    print(f"Answer: {chat_response['answer']}")
    print(f"Confidence: {chat_response['confidence']:.2%}")
    print(f"Sources: {chat_response['sources_count']}")
    
    # 3. Get collection statistics
    print("\n3. Checking collection stats...")
    response = requests.get(f"{BASE_URL}/collection/stats")
    print(f"Stats: {json.dumps(response.json(), indent=2)}")
    
    # 4. Get conversation history
    print("\n4. Getting conversation history...")
    response = requests.get(f"{BASE_URL}/chat/history")
    history = response.json()
    print(f"Conversation length: {history['history_length']} messages")


# Example 2: Advanced Python client with context management
# =========================================================

class RAGChatClient:
    """Advanced client for RAG Chat API with error handling and retry logic."""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        """
        Initialize RAG Chat client.
        
        Args:
            base_url: API base URL
            timeout: Request timeout in seconds
        """
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        self.base_url = base_url
        self.timeout = timeout
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def health_check(self) -> dict:
        """Check API health status."""
        response = self.session.get(
            f"{self.base_url}/health",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def upload_document(self, file_path: str) -> dict:
        """
        Upload a PDF document.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Ingestion response
        """
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = self.session.post(
                f"{self.base_url}/ingest",
                files=files,
                timeout=300  # Longer timeout for file upload
            )
        response.raise_for_status()
        return response.json()
    
    def chat(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.3,
        include_sources: bool = True
    ) -> dict:
        """
        Send a query and get response.
        
        Args:
            query: User query
            top_k: Number of relevant chunks to retrieve
            score_threshold: Minimum relevance score
            include_sources: Whether to include source chunks
            
        Returns:
            Chat response with answer and sources
        """
        payload = {
            "query": query,
            "top_k": top_k,
            "score_threshold": score_threshold,
            "include_sources": include_sources
        }
        
        response = self.session.post(
            f"{self.base_url}/chat",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def get_history(self) -> list:
        """Get conversation history."""
        response = self.session.get(
            f"{self.base_url}/chat/history",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json().get("messages", [])
    
    def clear_history(self) -> dict:
        """Clear conversation history."""
        response = self.session.post(
            f"{self.base_url}/chat/clear",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def get_stats(self) -> dict:
        """Get collection statistics."""
        response = self.session.get(
            f"{self.base_url}/collection/stats",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def clear_collection(self) -> dict:
        """Clear all documents from collection."""
        response = self.session.post(
            f"{self.base_url}/collection/clear",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()


def example_advanced_client():
    """Example using the advanced client."""
    
    try:
        # Initialize client
        client = RAGChatClient()
        
        # Check health
        health = client.health_check()
        print(f"API Health: {health['status']}")
        
        # Upload document
        result = client.upload_document("healthcare_doc.pdf")
        print(f"Uploaded: {result['chunks_count']} chunks")
        
        # Chat with document
        response = client.chat(
            "What is the treatment plan?",
            top_k=5,
            include_sources=True
        )
        
        print(f"\nAnswer: {response['answer']}")
        print(f"Confidence: {response['confidence']:.2%}")
        
        # Print sources
        if response.get('sources'):
            print(f"\nSources ({response['sources_count']}):")
            for i, source in enumerate(response['sources'], 1):
                print(f"\n{i}. Relevance: {source['relevance_score']:.2%}")
                print(f"   {source['content'][:150]}...")
        
        # Get history
        history = client.get_history()
        print(f"\nConversation history: {len(history)} messages")
        
    except Exception as e:
        print(f"Error: {e}")


# ==================== cURL Examples ====================

# Example: Using cURL for API calls
# ===================================

"""
# 1. Health Check
curl -X GET "http://localhost:8000/health" \
  -H "accept: application/json"

# 2. Upload PDF
curl -X POST "http://localhost:8000/ingest" \
  -H "accept: application/json" \
  -F "file=@document.pdf"

# 3. Chat with Advanced Parameters
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the recommended treatments?",
    "top_k": 5,
    "score_threshold": 0.4,
    "include_sources": true
  }'

# 4. Get Collection Stats
curl -X GET "http://localhost:8000/collection/stats" \
  -H "accept: application/json"

# 5. Get Conversation History
curl -X GET "http://localhost:8000/chat/history" \
  -H "accept: application/json"

# 6. Clear History
curl -X POST "http://localhost:8000/chat/clear" \
  -H "accept: application/json"

# 7. Clear Collection
curl -X POST "http://localhost:8000/collection/clear" \
  -H "accept: application/json"
"""


# ==================== JavaScript/Node.js Examples ====================

# Example: Using JavaScript/Node.js with fetch
# ==============================================

javascript_example = """
// Initialize API client
const BASE_URL = 'http://localhost:8000';

// 1. Health Check
async function checkHealth() {
    const response = await fetch(`${BASE_URL}/health`);
    const data = await response.json();
    console.log('API Health:', data.status);
    return data;
}

// 2. Upload Document
async function uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${BASE_URL}/ingest`, {
        method: 'POST',
        body: formData
    });
    
    const data = await response.json();
    console.log(`Uploaded: ${data.chunks_count} chunks`);
    return data;
}

// 3. Chat with Document
async function chat(query, topK = 5) {
    const response = await fetch(`${BASE_URL}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            query: query,
            top_k: topK,
            score_threshold: 0.3,
            include_sources: true
        })
    });
    
    const data = await response.json();
    
    console.log('Answer:', data.answer);
    console.log('Confidence:', (data.confidence * 100).toFixed(2) + '%');
    
    if (data.sources) {
        console.log(`\\nSources (${data.sources_count}):`);
        data.sources.forEach((source, index) => {
            console.log(`${index + 1}. ${source.content.substring(0, 100)}...`);
        });
    }
    
    return data;
}

// 4. Get Collection Stats
async function getStats() {
    const response = await fetch(`${BASE_URL}/collection/stats`);
    const data = await response.json();
    console.log('Collection Stats:', data.data);
    return data;
}

// 5. Get Chat History
async function getHistory() {
    const response = await fetch(`${BASE_URL}/chat/history`);
    const data = await response.json();
    console.log(`History: ${data.history_length} messages`);
    return data.messages;
}

// Example usage
async function main() {
    try {
        // Check health
        await checkHealth();
        
        // Upload file
        const fileInput = document.getElementById('file-input');
        if (fileInput.files.length > 0) {
            await uploadDocument(fileInput.files[0]);
        }
        
        // Chat
        const response = await chat('What is the diagnosis?');
        
        // Get history
        const history = await getHistory();
        console.log('Full history:', history);
        
    } catch (error) {
        console.error('Error:', error);
    }
}

// Run on page load
document.addEventListener('DOMContentLoaded', main);
"""


# ==================== Advanced Usage Scenarios ====================

def example_batch_processing():
    """Example: Processing multiple documents in batch."""
    
    import os
    from pathlib import Path
    
    client = RAGChatClient()
    documents_folder = "./documents"
    
    # Upload all PDFs
    pdf_files = list(Path(documents_folder).glob("*.pdf"))
    
    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file.name}")
        try:
            result = client.upload_document(str(pdf_file))
            print(f"  ✓ {result['chunks_count']} chunks ingested")
        except Exception as e:
            print(f"  ✗ Error: {e}")


def example_multi_query_analysis():
    """Example: Running multiple queries and analyzing responses."""
    
    client = RAGChatClient()
    
    queries = [
        "What is the treatment plan?",
        "What are the side effects?",
        "What is the dosage?",
        "How long is the treatment?",
        "Are there any contraindications?"
    ]
    
    print("Running multi-query analysis...\n")
    
    results = []
    for query in queries:
        print(f"Q: {query}")
        response = client.chat(query, include_sources=False)
        results.append({
            "query": query,
            "answer": response['answer'],
            "confidence": response['confidence']
        })
        print(f"A: {response['answer'][:100]}...")
        print(f"Confidence: {response['confidence']:.2%}\n")
    
    # Analyze results
    avg_confidence = sum(r['confidence'] for r in results) / len(results)
    print(f"\nAnalysis Summary:")
    print(f"Average Confidence: {avg_confidence:.2%}")
    print(f"Queries Processed: {len(results)}")


# ==================== Run Examples ====================

if __name__ == "__main__":
    print("RAG Healthcare Chat API - Advanced Usage Examples\n")
    
    print("1. Basic Python Client")
    print("-" * 40)
    try:
        example_python_client()
    except Exception as e:
        print(f"Could not run: {e}")
    
    print("\n\n2. Advanced Python Client")
    print("-" * 40)
    try:
        example_advanced_client()
    except Exception as e:
        print(f"Could not run: {e}")
    
    print("\n\n3. Batch Processing Example")
    print("-" * 40)
    try:
        example_batch_processing()
    except Exception as e:
        print(f"Could not run: {e}")
    
    print("\n\n4. Multi-Query Analysis")
    print("-" * 40)
    try:
        example_multi_query_analysis()
    except Exception as e:
        print(f"Could not run: {e}")
