"""
Vector Store Module

Manages storage and retrieval of document embeddings
using ChromaDB for efficient similarity search.
Falls back to simple in-memory store for Python 3.14+ compatibility.
"""

import os
import json
import math
from typing import List, Dict, Any, Optional
from pathlib import Path


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


class SimpleVectorStore:
    """Simple in-memory vector store fallback for Python 3.14+ compatibility."""
    
    def __init__(self, persist_path: str):
        self.persist_path = Path(persist_path)
        self.documents: Dict[str, Dict] = {}
        self._load()
    
    def _load(self):
        """Load from disk if exists."""
        if self.persist_path.exists():
            try:
                with open(self.persist_path, 'r') as f:
                    self.documents = json.load(f)
            except:
                self.documents = {}
    
    def _save(self):
        """Save to disk."""
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.persist_path, 'w') as f:
            json.dump(self.documents, f)
    
    def add(self, ids: List[str], embeddings: List[List[float]], 
            documents: List[str], metadatas: List[Dict]):
        """Add documents to store."""
        for id_, emb, doc, meta in zip(ids, embeddings, documents, metadatas):
            self.documents[id_] = {
                "embedding": emb,
                "document": doc,
                "metadata": meta
            }
        self._save()
    
    def query(self, query_embeddings: List[List[float]], n_results: int = 5,
              where: Optional[Dict] = None) -> Dict:
        """Query similar documents."""
        results = {"ids": [], "documents": [], "metadatas": [], "distances": []}
        
        for query_emb in query_embeddings:
            # Calculate similarities
            scored = []
            for id_, data in self.documents.items():
                # Check filter
                if where:
                    match = True
                    for k, v in where.items():
                        if data["metadata"].get(k) != v:
                            match = False
                            break
                    if not match:
                        continue
                
                similarity = cosine_similarity(query_emb, data["embedding"])
                scored.append((id_, data, similarity))
            
            # Sort by similarity (highest first)
            scored.sort(key=lambda x: x[2], reverse=True)
            top = scored[:n_results]
            
            results["ids"].append([x[0] for x in top])
            results["documents"].append([x[1]["document"] for x in top])
            results["metadatas"].append([x[1]["metadata"] for x in top])
            results["distances"].append([1 - x[2] for x in top])  # Convert to distance
        
        return results
    
    def delete(self, ids: List[str]):
        """Delete documents by ID."""
        for id_ in ids:
            self.documents.pop(id_, None)
        self._save()
    
    def count(self) -> int:
        """Return document count."""
        return len(self.documents)


class VectorStore:
    """Vector database interface for storing and querying embeddings."""
    
    def __init__(
        self, 
        collection_name: str = "financial_docs",
        persist_directory: Optional[str] = None
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory or "./data/embeddings/chroma"
        self._client = None
        self._collection = None
        self._initialized = False
        self._use_simple = False
    
    def initialize(self):
        """Initialize vector store (ChromaDB or fallback)."""
        # Ensure persist directory exists
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Try ChromaDB first, fallback to simple store
        try:
            import chromadb
            from chromadb.config import Settings
            
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
            
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            self._use_simple = False
            print(f"Vector store initialized (ChromaDB): {self.collection_name}")
            
        except Exception as e:
            # Fallback to simple vector store
            print(f"ChromaDB unavailable ({e}), using simple vector store")
            persist_path = Path(self.persist_directory) / f"{self.collection_name}.json"
            self._collection = SimpleVectorStore(str(persist_path))
            self._use_simple = True
            print(f"Vector store initialized (Simple): {self.collection_name}")
        
        self._initialized = True
    
    def _ensure_initialized(self):
        """Ensure the vector store is initialized."""
        if not self._initialized:
            self.initialize()
    
    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents with their embeddings to the vector store.
        
        Args:
            documents: List of document dicts with 'content' and 'metadata' keys
            embeddings: List of embedding vectors
            ids: Optional list of unique identifiers
            
        Returns:
            List of document IDs that were added
        """
        self._ensure_initialized()
        
        if len(documents) != len(embeddings):
            raise ValueError("Number of documents must match number of embeddings")
        
        # Generate IDs if not provided
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in documents]
        
        # Extract contents and metadata
        contents = [doc.get('content', '') for doc in documents]
        metadatas = [doc.get('metadata', {}) for doc in documents]
        
        # Ensure metadata values are valid types for ChromaDB
        cleaned_metadatas = []
        for metadata in metadatas:
            cleaned = {}
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    cleaned[k] = v
                elif isinstance(v, list):
                    cleaned[k] = str(v)  # Convert lists to strings
                elif v is None:
                    cleaned[k] = ""
                else:
                    cleaned[k] = str(v)
            cleaned_metadatas.append(cleaned)
        
        # Add to collection
        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=cleaned_metadatas
        )
        
        return ids
    
    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        include_distances: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filters: Optional metadata filters (ChromaDB where clause)
            include_distances: Whether to include similarity scores
            
        Returns:
            List of similar documents with scores
        """
        self._ensure_initialized()
        
        # Build query parameters based on backend
        if self._use_simple:
            # SimpleVectorStore interface
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": top_k,
            }
            if filters:
                query_params["where"] = filters
        else:
            # ChromaDB interface
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"]
            }
            if filters:
                query_params["where"] = filters
        
        # Execute query
        results = self._collection.query(**query_params)
        
        # Format results
        documents = []
        if results and results.get('ids') and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                doc = {
                    "id": doc_id,
                    "content": results['documents'][0][i] if results.get('documents') else "",
                    "metadata": results['metadatas'][0][i] if results.get('metadatas') else {}
                }
                
                if include_distances and results.get('distances'):
                    # Convert distance to similarity score (cosine)
                    distance = results['distances'][0][i]
                    doc["similarity_score"] = 1 - distance  # Cosine distance to similarity
                    doc["distance"] = distance
                
                documents.append(doc)
        
        return documents
    
    def search_by_text(
        self,
        query_text: str,
        embedding_service,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search using text query (generates embedding automatically).
        
        Args:
            query_text: Text query
            embedding_service: Service to generate query embedding
            top_k: Number of results
            filters: Optional metadata filters
            
        Returns:
            List of similar documents
        """
        query_embedding = embedding_service.generate_query_embedding(query_text)
        return self.similarity_search(query_embedding, top_k, filters)
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID."""
        self._ensure_initialized()
        
        results = self._collection.get(ids=[doc_id], include=["documents", "metadatas"])
        
        if results and results['ids']:
            return {
                "id": results['ids'][0],
                "content": results['documents'][0] if results['documents'] else "",
                "metadata": results['metadatas'][0] if results['metadatas'] else {}
            }
        return None
    
    def update_document(
        self,
        doc_id: str,
        content: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Update an existing document."""
        self._ensure_initialized()
        
        update_params = {"ids": [doc_id]}
        
        if content is not None:
            update_params["documents"] = [content]
        if embedding is not None:
            update_params["embeddings"] = [embedding]
        if metadata is not None:
            update_params["metadatas"] = [metadata]
        
        self._collection.update(**update_params)
    
    def delete_documents(self, doc_ids: List[str]):
        """Delete documents by IDs."""
        self._ensure_initialized()
        self._collection.delete(ids=doc_ids)
    
    def delete_by_filter(self, filters: Dict[str, Any]):
        """Delete documents matching filter criteria."""
        self._ensure_initialized()
        self._collection.delete(where=filters)
    
    def clear_collection(self):
        """Delete all documents in the collection."""
        self._ensure_initialized()
        
        # Get all IDs and delete
        all_docs = self._collection.get()
        if all_docs and all_docs['ids']:
            self._collection.delete(ids=all_docs['ids'])
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        self._ensure_initialized()
        
        return {
            "collection_name": self.collection_name,
            "document_count": self._collection.count(),
            "persist_directory": self.persist_directory
        }
    
    def list_collections(self) -> List[str]:
        """List all collections in the database."""
        self._ensure_initialized()
        collections = self._client.list_collections()
        return [c.name for c in collections]
    
    def delete_collection(self):
        """Delete the entire collection."""
        self._ensure_initialized()
        self._client.delete_collection(self.collection_name)
        self._collection = None
        self._initialized = False
