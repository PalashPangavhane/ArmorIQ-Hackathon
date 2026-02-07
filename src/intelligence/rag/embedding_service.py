"""
Embedding Service Module

Generates vector embeddings for document chunks
to enable semantic search and retrieval using Google Gemini.
"""

import os
from pathlib import Path
from typing import List, Optional

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

from google import genai
from google.genai import types


class EmbeddingService:
    """Generates embeddings for text chunks using Google Gemini."""
    
    def __init__(self, model_name: str = "gemini-embedding-001"):
        self.model_name = model_name
        self._client = None
        self._initialized = False
    
    def initialize(self):
        """Initialize the Gemini embedding client."""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        self._client = genai.Client(api_key=api_key)
        self._initialized = True
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        if not self._initialized:
            self.initialize()
        
        result = self._client.models.embed_content(
            model=self.model_name,
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )
        return result.embeddings[0].values
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        if not self._initialized:
            self.initialize()
        
        embeddings = []
        for text in texts:
            result = self._client.models.embed_content(
                model=self.model_name,
                contents=text,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )
            embeddings.append(result.embeddings[0].values)
        return embeddings
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        
        Args:
            query: Search query text
            
        Returns:
            Embedding vector for query
        """
        if not self._initialized:
            self.initialize()
        
        result = self._client.models.embed_content(
            model=self.model_name,
            contents=query,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
        )
        return result.embeddings[0].values
