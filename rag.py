"""
RAG (Retrieval-Augmented Generation) module.

Manages embeddings generation, vector database initialization,
document storage, and retrieval operations using ChromaDB.
"""

import os
from pathlib import Path
from typing import List, Optional
import chromadb
from sentence_transformers import SentenceTransformer


class RAGError(Exception):
    """Custom exception for RAG operations."""
    pass


class RAGPipeline:
    """
    RAG pipeline for managing document embeddings and retrieval.
    
    Attributes:
        embedding_model: SentenceTransformer model for generating embeddings
        chroma_client: ChromaDB persistent client
        collection: ChromaDB collection for storing embeddings
    """
    
    def __init__(
        self,
        embedding_model_name: str = "all-MiniLM-L6-v2",
        db_path: str = "./chroma_store",
        collection_name: str = "Humana_chat_docs"
    ):
        """
        Initialize RAG pipeline with embedding model and vector database.
        
        Args:
            embedding_model_name: Name of the SentenceTransformer model
            db_path: Path to ChromaDB persistence directory
            collection_name: Name of the ChromaDB collection
            
        Raises:
            RAGError: If initialization fails
        """
        try:
            print(f"Initializing RAG Pipeline...")
            
            # Initialize embedding model
            print(f"Loading embedding model: {embedding_model_name}")
            self.embedding_model = SentenceTransformer(embedding_model_name)
            print(f"✓ Embedding model loaded")
            
            # Create db_path if doesn't exist
            Path(db_path).mkdir(parents=True, exist_ok=True)
            
            # Initialize ChromaDB persistent client (new API)
            print(f"Initializing ChromaDB at: {db_path}")
            self.chroma_client = chromadb.PersistentClient(path=db_path)
            print(f"✓ ChromaDB client initialized")
            
            # Get or create collection with cosine similarity
            self.collection_name = collection_name
            self.collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"✓ Collection '{collection_name}' ready")
            
        except Exception as e:
            raise RAGError(f"Failed to initialize RAG pipeline: {str(e)}")
    
    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            RAGError: If embedding generation fails
        """
        try:
            if not texts:
                raise RAGError("Empty text list provided for embedding")
            
            embeddings = self.embedding_model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            return embeddings.tolist()
        except Exception as e:
            raise RAGError(f"Embedding generation failed: {str(e)}")
    
    def store_documents(
        self,
        chunks: List[str],
        metadata: Optional[dict] = None
    ) -> None:
        """
        Store document chunks with embeddings in ChromaDB.
        
        Args:
            chunks: List of text chunks to store
            metadata: Optional metadata dictionary to attach to all chunks
            
        Raises:
            RAGError: If storage operation fails
        """
        try:
            if not chunks:
                raise RAGError("No chunks provided for storage")
            
            print(f"Storing {len(chunks)} chunks in vector database...")
            
            # Generate embeddings
            embeddings = self._generate_embeddings(chunks)
            
            # Prepare metadata for each chunk
            if metadata is None:
                metadata = {}
            
            metadatas = [metadata.copy() for _ in chunks]
            
            # Create IDs for each chunk
            existing_count = self.collection.count()
            ids = [f"chunk_{existing_count + i}" for i in range(len(chunks))]
            
            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=chunks
            )
            
            print(f"✓ {len(chunks)} chunks stored successfully")
            
        except RAGError:
            raise
        except Exception as e:
            raise RAGError(f"Failed to store documents: {str(e)}")
    
    def retrieve_relevant_chunks(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0
    ) -> List[dict]:
        """
        Retrieve the most relevant document chunks for a query.
        
        Uses cosine similarity in the vector space for ranking.
        
        Args:
            query: User query string
            top_k: Number of top results to return
            score_threshold: Minimum similarity score (0.0-1.0) for inclusion
            
        Returns:
            List of dictionaries containing:
                - 'chunk': The text content
                - 'score': Similarity score
                - 'metadata': Associated metadata
                
        Raises:
            RAGError: If retrieval fails
        """
        try:
            if not query or not query.strip():
                raise RAGError("Query cannot be empty")
            
            if top_k <= 0:
                raise RAGError("top_k must be positive")
            
            if not 0.0 <= score_threshold <= 1.0:
                raise RAGError("score_threshold must be between 0.0 and 1.0")
            
            # Check if collection has documents
            collection_count = self.collection.count()
            if collection_count == 0:
                print("Warning: No documents in collection")
                return []
            
            print(f"Retrieving top {top_k} chunks for query: '{query[:50]}...'")
            
            # Generate query embedding
            query_embedding = self._generate_embeddings([query])[0]
            
            # Query the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Process results into readable format
            retrieved_chunks = []
            
            if results['documents'] and len(results['documents']) > 0:
                for i, (doc, metadata, distance) in enumerate(
                    zip(
                        results['documents'][0],
                        results['metadatas'][0],
                        results['distances'][0]
                    )
                ):
                    # Convert distance to similarity score (0-1)
                    # ChromaDB returns cosine distance; convert to similarity
                    similarity_score = 1 - distance
                    
                    if similarity_score >= score_threshold:
                        retrieved_chunks.append({
                            'chunk': doc,
                            'score': similarity_score,
                            'metadata': metadata,
                            'rank': i + 1
                        })
            
            print(f"✓ Retrieved {len(retrieved_chunks)} relevant chunks")
            return retrieved_chunks
            
        except RAGError:
            raise
        except Exception as e:
            raise RAGError(f"Chunk retrieval failed: {str(e)}")
    
    def get_collection_stats(self) -> dict:
        """
        Get statistics about the current collection.
        
        Returns:
            Dictionary containing collection statistics
        """
        try:
            count = self.collection.count()
            return {
                'collection_name': self.collection_name,
                'total_documents': count,
                'embedding_model': self.embedding_model.get_sentence_embedding_dimension()
            }
        except Exception as e:
            raise RAGError(f"Failed to get collection stats: {str(e)}")
    
    def clear_collection(self) -> None:
        """
        Clear all documents from the collection.
        
        Use with caution - this operation cannot be undone.
        
        Raises:
            RAGError: If clearing fails
        """
        try:
            # Delete the collection and recreate it
            self.chroma_client.delete_collection(self.collection_name)
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"✓ Collection '{self.collection_name}' cleared")
        except Exception as e:
            raise RAGError(f"Failed to clear collection: {str(e)}")


if __name__ == "__main__":
    # Example usage and testing
    try:
        rag = RAGPipeline()
        stats = rag.get_collection_stats()
        print("\n=== Collection Stats ===")
        print(f"Collection: {stats['collection_name']}")
        print(f"Documents: {stats['total_documents']}")
        print(f"Embedding Dimension: {stats['embedding_model']}")
    except RAGError as e:
        print(f"Error: {e}")
