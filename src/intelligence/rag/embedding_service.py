"""
Embedding Service Module

Generates vector embeddings for document chunks
to enable semantic search and retrieval using Ollama (local).
"""

import os
import requests
from pathlib import Path
from typing import List, Optional

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")


class EmbeddingService:
    """Generates embeddings for text chunks using Ollama (local)."""
    
    def __init__(self, model_name: str = "nomic-embed-text", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self._initialized = False
    
    def initialize(self):
        """Initialize the Ollama embedding service and pull model if needed."""
        # Check if Ollama is running
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                raise ConnectionError("Ollama is not responding properly")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                "Ollama is not running. Start it with: ollama serve"
            )
        
        # Check if embedding model is available, pull if not
        models = response.json().get("models", [])
        model_names = [m.get("name", "").split(":")[0] for m in models]
        
        if self.model_name.split(":")[0] not in model_names:
            print(f"Pulling embedding model: {self.model_name}...")
            pull_response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model_name},
                timeout=300
            )
            if pull_response.status_code != 200:
                raise RuntimeError(f"Failed to pull model: {self.model_name}")
            print(f"Model {self.model_name} pulled successfully")
        
        self._initialized = True
    
    def generate_embedding(self, text: str, max_chars: int = 2000) -> List[float]:
        """
        Generate embedding vector for a single text.
        
        Args:
            text: Input text to embed
            max_chars: Maximum characters to embed (truncates if exceeded)
            
        Returns:
            Embedding vector as list of floats
        """
        if not self._initialized:
            self.initialize()
        
        # Truncate text if too long for embedding model
        if len(text) > max_chars:
            text = text[:max_chars]
        
        response = requests.post(
            f"{self.base_url}/api/embeddings",
            json={
                "model": self.model_name,
                "prompt": text
            },
            timeout=60
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Embedding request failed: {response.text}")
        
        return response.json()["embedding"]
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        if not self._initialized:
            self.initialize()
        
        embeddings = []
        for text in texts:
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        
        Args:
            query: Search query text
            
        Returns:
            Embedding vector for query
        """
        return self.generate_embedding(query)
