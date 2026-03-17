"""
Chat module for RAG-powered conversational interface.

Orchestrates interactions between user queries, document retrieval,
and LLM responses with a focus on grounding answers in retrieved documents.
"""

import os
from typing import List, Optional, Dict, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ChatError(Exception):
    """Custom exception for chat operations."""
    pass


class RAGChat:
    """
    RAG-powered chat orchestrator.
    
    Combines document retrieval with LLM inference to provide
    grounded, document-based responses.
    
    Attributes:
        llm: Language model for generating responses
        rag_pipeline: RAG pipeline for document retrieval
        context_window: Number of previous messages to keep in context
    """
    
    def __init__(self, rag_pipeline, llm_model=None, context_window: int = 3):
        """
        Initialize chat interface with RAG pipeline and LLM.
        
        Args:
            rag_pipeline: Initialized RAGPipeline instance
            llm_model: Language model instance (uses Llama if None)
            context_window: Number of previous messages to maintain
            
        Raises:
            ChatError: If initialization fails
        """
        try:
            self.rag_pipeline = rag_pipeline
            self.llm_model = llm_model
            self.context_window = context_window
            self.conversation_history: List[Dict[str, str]] = []
            
            print("✓ RAG Chat initialized")
            
        except Exception as e:
            raise ChatError(f"Failed to initialize chat: {str(e)}")
    
    def _format_context(self, retrieved_chunks: List[dict]) -> str:
        """
        Format retrieved chunks into a context string for the LLM.
        
        Args:
            retrieved_chunks: List of retrieved document chunks
            
        Returns:
            Formatted context string
        """
        if not retrieved_chunks:
            return "No relevant information found in the document."
        
        context_parts = ["Based on the document:\n"]
        
        for chunk in retrieved_chunks:
            score = chunk.get('score', 0)
            content = chunk.get('chunk', '')
            context_parts.append(f"[Relevance: {score:.2%}]\n{content}\n")
        
        return "\n---\n".join(context_parts)
    
    def _build_prompt(
        self,
        query: str,
        context: str,
        use_history: bool = True
    ) -> str:
        """
        Build a prompt for the LLM including context and conversation history.
        
        Args:
            query: User's question
            context: Retrieved document context
            use_history: Whether to include conversation history
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        # Add system instruction
        prompt_parts.append(
            "You are a healthcare assistant. Answer questions ONLY based on "
            "the provided document content. If the answer is not in the document, "
            "respond with: 'This information is not available in the document.'\n"
        )
        
        # Add document context
        prompt_parts.append(f"=== Document Context ===\n{context}\n")
        
        # Add conversation history if enabled
        if use_history and self.conversation_history:
            prompt_parts.append("=== Conversation History ===\n")
            for msg in self.conversation_history[-self.context_window:]:
                role = msg['role'].upper()
                prompt_parts.append(f"{role}: {msg['content']}\n")
        
        # Add current query
        prompt_parts.append(f"\n=== Current Question ===\nUSER: {query}\n\nASSISTANT:")
        
        return "".join(prompt_parts)
    
    def _call_llm(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Call the LLM with a prepared prompt.
        
        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum tokens in the response
            
        Returns:
            LLM generated response
            
        Raises:
            ChatError: If LLM call fails
        """
        try:
            if self.llm_model is None:
                raise ChatError(
                    "LLM model not initialized. Please provide an LLM instance."
                )
            
            # Call LLM (implementation depends on LLM library)
            # For Llama, this would typically use llama-cpp-python or similar
            # Placeholder for LLM inference
            response = self.llm_model.generate(
                prompt,
                max_tokens=max_tokens,
                temperature=float(os.getenv("TEMPERATURE", "0.7"))
            )
            
            return response.strip()
            
        except ChatError:
            raise
        except Exception as e:
            raise ChatError(f"LLM inference failed: {str(e)}")
    
    def answer_query(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.3,
        include_sources: bool = True
    ) -> Dict[str, any]:
        """
        Answer a user query using RAG pipeline and LLM.
        
        This is the main entry point for chat interactions.
        
        Args:
            query: User's question
            top_k: Number of document chunks to retrieve
            score_threshold: Minimum relevance score for retrieved chunks
            include_sources: Whether to include source references in response
            
        Returns:
            Dictionary containing:
                - 'answer': LLM generated response
                - 'sources': Retrieved document chunks (if include_sources=True)
                - 'sources_count': Number of sources used
                - 'confidence': Based on source relevance scores
                
        Raises:
            ChatError: If query processing fails
        """
        try:
            if not query or not query.strip():
                raise ChatError("Query cannot be empty")
            
            print(f"\n📝 Processing query: '{query}'")
            
            # Retrieve relevant chunks from documents
            retrieved_chunks = self.rag_pipeline.retrieve_relevant_chunks(
                query,
                top_k=top_k,
                score_threshold=score_threshold
            )
            
            # Format context
            context = self._format_context(retrieved_chunks)
            
            # Build prompt
            prompt = self._build_prompt(query, context)
            
            # Generate response
            print("🤖 Generating response...")
            response = self._call_llm(prompt)
            
            # Calculate confidence based on source scores
            confidence = (
                sum(chunk['score'] for chunk in retrieved_chunks) / len(retrieved_chunks)
                if retrieved_chunks
                else 0.0
            )
            
            # Add to conversation history
            self.conversation_history.append({
                'role': 'user',
                'content': query
            })
            self.conversation_history.append({
                'role': 'assistant',
                'content': response
            })
            
            # Prepare response
            result = {
                'answer': response,
                'sources_count': len(retrieved_chunks),
                'confidence': confidence
            }
            
            if include_sources:
                result['sources'] = [
                    {
                        'content': chunk['chunk'],
                        'relevance_score': chunk['score'],
                        'rank': chunk['rank']
                    }
                    for chunk in retrieved_chunks
                ]
            
            print(f"✓ Response generated (confidence: {confidence:.2%})")
            return result
            
        except ChatError:
            raise
        except Exception as e:
            raise ChatError(f"Failed to process query: {str(e)}")
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
        print("✓ Conversation history cleared")
    
    def get_history(self) -> List[Dict[str, str]]:
        """
        Get current conversation history.
        
        Returns:
            List of conversation messages
        """
        return self.conversation_history.copy()
    
    def get_context_summary(self) -> Dict:
        """
        Get summary of current chat context.
        
        Returns:
            Dictionary with context information
        """
        return {
            'history_length': len(self.conversation_history),
            'context_window': self.context_window,
            'collection_stats': self.rag_pipeline.get_collection_stats(),
            'has_llm': self.llm_model is not None
        }


if __name__ == "__main__":
    # Example usage
    print("RAG Chat module loaded")
    print("Use this module within FastAPI application for production")
