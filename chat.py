"""
Chat module for RAG-powered conversational interface.

Orchestrates interactions between user queries, document retrieval,
and LLM responses with a focus on grounding answers in retrieved documents.
"""

import os
from typing import List, Optional, Dict
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
    """

    def __init__(self, rag_pipeline, llm_model=None, context_window: int = 3):
        """
        Initialize chat interface with RAG pipeline and LLM.

        Args:
            rag_pipeline: Initialized RAGPipeline instance
            llm_model: Not used — Ollama is called directly
            context_window: Number of previous messages to maintain

        Raises:
            ChatError: If initialization fails
        """
        try:
            self.rag_pipeline = rag_pipeline
            self.llm_model = None  # Using Ollama directly
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
            Formatted context string with relevance scores
        """
        if not retrieved_chunks:
            return "No relevant information found in the document."

        context_parts = ["Based on the document:\n"]

        for chunk in retrieved_chunks:
            score = chunk.get('score', 0)
            content = chunk.get('chunk', '')
            context_parts.append(f"[Relevance: {score:.2%}]\n{content}\n")

        return "\n---\n".join(context_parts)

    def _build_prompt(self, query: str, context: str, use_history: bool = True) -> str:
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

        # System instruction — ONLY prevents hallucination
        prompt_parts.append(
            "You are a healthcare assistant. Answer questions ONLY based on "
            "the provided document content. If the answer is not in the document, "
            "respond with: 'This information is not available in the document.'\n"
        )

        # Document context retrieved from ChromaDB
        prompt_parts.append(f"=== Document Context ===\n{context}\n")

        # Conversation history for multi-turn awareness
        if use_history and self.conversation_history:
            prompt_parts.append("=== Conversation History ===\n")
            for msg in self.conversation_history[-self.context_window:]:
                role = msg['role'].upper()
                prompt_parts.append(f"{role}: {msg['content']}\n")

        # Current user query
        prompt_parts.append(f"\n=== Current Question ===\nUSER: {query}\n\nASSISTANT:")

        return "".join(prompt_parts)

    def _call_llm(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Call Ollama LLaMA 3.2 model with prepared prompt.

        Args:
            prompt: Full prompt including context and question
            max_tokens: Maximum response length

        Returns:
            LLM generated response string

        Raises:
            ChatError: If Ollama call fails
        """
        try:
            import ollama  # installed from previous project setup

            response = ollama.chat(
                model="llama3.2",
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Extract text content from Ollama response
            return response["message"]["content"].strip()

        except Exception as e:
            raise ChatError(f"LLM inference failed: {str(e)}")

    def answer_query(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.3,
        include_sources: bool = True
    ) -> Dict:
        """
        Main entry point — process user query through full RAG pipeline.

        Steps:
        1. Retrieve relevant chunks from ChromaDB
        2. Format chunks into context
        3. Build prompt with context + history
        4. Call Ollama LLM
        5. Return grounded answer with sources

        Args:
            query: User's question string
            top_k: Number of document chunks to retrieve
            score_threshold: Minimum similarity score for chunks
            include_sources: Whether to return source chunks

        Returns:
            Dict with answer, sources_count, confidence, and sources

        Raises:
            ChatError: If query processing fails
        """
        try:
            if not query or not query.strip():
                raise ChatError("Query cannot be empty")

            print(f"\n📝 Processing query: '{query}'")

            # Step 1 — retrieve relevant chunks from ChromaDB via cosine similarity
            retrieved_chunks = self.rag_pipeline.retrieve_relevant_chunks(
                query,
                top_k=top_k,
                score_threshold=score_threshold
            )

            # Step 2 — format chunks into readable context block
            context = self._format_context(retrieved_chunks)

            # Step 3 — build full prompt with context + history
            prompt = self._build_prompt(query, context)

            # Step 4 — send to Ollama LLaMA 3.2 and get grounded answer
            print("🤖 Sending to Ollama...")
            response = self._call_llm(prompt)

            # Step 5 — calculate confidence from average chunk similarity scores
            confidence = (
                sum(chunk['score'] for chunk in retrieved_chunks) / len(retrieved_chunks)
                if retrieved_chunks else 0.0
            )

            # Save to conversation history for multi-turn awareness
            self.conversation_history.append({'role': 'user', 'content': query})
            self.conversation_history.append({'role': 'assistant', 'content': response})

            print(f"✅ Answer generated (confidence: {confidence:.2%})")

            # Build result dictionary
            result = {
                'answer': response,
                'sources_count': len(retrieved_chunks),
                'confidence': confidence
            }

            # Optionally include source chunks in response
            if include_sources:
                result['sources'] = [
                    {
                        'content': chunk['chunk'],
                        'relevance_score': chunk['score'],
                        'rank': chunk['rank']
                    }
                    for chunk in retrieved_chunks
                ]

            return result

        except ChatError:
            raise
        except Exception as e:
            raise ChatError(f"Failed to process query: {str(e)}")

    def clear_history(self) -> None:
        """
        Clear conversation history.
        Call this to start a fresh chat session.
        """
        self.conversation_history = []
        print("✓ Conversation history cleared")

    def get_history(self) -> List[Dict[str, str]]:
        """
        Get current conversation history.

        Returns:
            List of message dicts with role and content keys
        """
        return self.conversation_history.copy()

    def get_context_summary(self) -> Dict:
        """
        Get summary of current chat context state.

        Returns:
            Dict with history length, context window, and collection stats
        """
        return {
            'history_length': len(self.conversation_history),
            'context_window': self.context_window,
            'collection_stats': self.rag_pipeline.get_collection_stats(),
            'has_llm': self.llm_model is not None
        }


if __name__ == "__main__":
    print("RAG Chat module loaded")
    print("Use this module within FastAPI application for production")