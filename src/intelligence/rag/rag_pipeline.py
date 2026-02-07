"""
RAG Pipeline Module

Main orchestrator for the complete RAG pipeline.
Handles document ingestion, embedding generation, storage, and retrieval.
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from .document_processor import DocumentProcessor, ProcessedDocument, DocumentChunk
from .embedding_service import EmbeddingService
from .vector_store import VectorStore
from .retriever import FinancialRetriever, RetrievalResult, ContextType


class RAGPipeline:
    """
    Complete RAG (Retrieval-Augmented Generation) Pipeline.
    
    This class orchestrates the entire RAG workflow:
    1. Document ingestion and processing
    2. Embedding generation
    3. Vector storage
    4. Contextual retrieval
    
    Usage:
        pipeline = RAGPipeline()
        pipeline.initialize()
        
        # Ingest documents
        pipeline.ingest_documents("./data/documents")
        
        # Query for context
        results = pipeline.query("What is the budget for Engineering?")
    """
    
    def __init__(
        self,
        collection_name: str = "financial_docs",
        persist_directory: str = "./data/embeddings/chroma",
        chunk_size: int = 256,  # Reduced for local embedding models
        chunk_overlap: int = 30,
        embedding_model: str = "nomic-embed-text"  # Local Ollama embedding model
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model
        
        # Components (initialized lazily)
        self._document_processor: Optional[DocumentProcessor] = None
        self._embedding_service: Optional[EmbeddingService] = None
        self._vector_store: Optional[VectorStore] = None
        self._retriever: Optional[FinancialRetriever] = None
        
        self._initialized = False
        self._ingestion_stats = {
            "total_documents": 0,
            "total_chunks": 0,
            "last_ingestion": None
        }
    
    def initialize(self):
        """Initialize all pipeline components."""
        # Initialize document processor
        self._document_processor = DocumentProcessor(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        
        # Initialize embedding service
        self._embedding_service = EmbeddingService(model_name=self.embedding_model)
        self._embedding_service.initialize()
        
        # Initialize vector store
        self._vector_store = VectorStore(
            collection_name=self.collection_name,
            persist_directory=self.persist_directory
        )
        self._vector_store.initialize()
        
        # Initialize retriever
        self._retriever = FinancialRetriever(
            embedding_service=self._embedding_service,
            vector_store=self._vector_store
        )
        
        self._initialized = True
        print(f"RAG Pipeline initialized successfully")
        print(f"  - Collection: {self.collection_name}")
        print(f"  - Persist directory: {self.persist_directory}")
        print(f"  - Embedding model: {self.embedding_model}")
    
    def _ensure_initialized(self):
        """Ensure pipeline is initialized before operations."""
        if not self._initialized:
            self.initialize()
    
    def ingest_documents(
        self, 
        source_path: str,
        context_type: Optional[str] = None,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Ingest documents from a directory or single file.
        
        Args:
            source_path: Path to directory or file
            context_type: Optional context type tag for all documents
            batch_size: Number of chunks to embed at once
            
        Returns:
            Ingestion statistics
        """
        self._ensure_initialized()
        
        path = Path(source_path)
        
        if path.is_file():
            documents = [self._document_processor.process_file(path)]
            documents = [d for d in documents if d is not None]
        elif path.is_dir():
            documents = self._document_processor.process_directory(source_path)
        else:
            raise FileNotFoundError(f"Path not found: {source_path}")
        
        if not documents:
            return {"error": "No documents found to process", "documents_processed": 0}
        
        # Process each document
        total_chunks = 0
        for doc in documents:
            chunks_added = self._ingest_document(doc, context_type, batch_size)
            total_chunks += chunks_added
        
        # Update stats
        self._ingestion_stats["total_documents"] += len(documents)
        self._ingestion_stats["total_chunks"] += total_chunks
        self._ingestion_stats["last_ingestion"] = datetime.utcnow().isoformat()
        
        return {
            "documents_processed": len(documents),
            "chunks_created": total_chunks,
            "timestamp": self._ingestion_stats["last_ingestion"]
        }
    
    def _ingest_document(
        self, 
        document: ProcessedDocument,
        context_type: Optional[str] = None,
        batch_size: int = 10
    ) -> int:
        """Ingest a single processed document."""
        if not document.chunks:
            return 0
        
        # Process chunks in batches
        for i in range(0, len(document.chunks), batch_size):
            batch = document.chunks[i:i + batch_size]
            
            # Prepare documents for storage
            docs_to_store = []
            for chunk in batch:
                metadata = {
                    **chunk.metadata,
                    "document_id": document.document_id,
                    "filename": document.filename,
                    "document_type": document.document_type.value
                }
                if context_type:
                    metadata["context_type"] = context_type
                
                docs_to_store.append({
                    "content": chunk.content,
                    "metadata": metadata
                })
            
            # Generate embeddings
            contents = [d["content"] for d in docs_to_store]
            embeddings = self._embedding_service.generate_embeddings_batch(contents)
            
            # Store in vector database
            ids = [chunk.chunk_id for chunk in batch]
            self._vector_store.add_documents(
                documents=docs_to_store,
                embeddings=embeddings,
                ids=ids
            )
        
        print(f"  Ingested: {document.filename} ({len(document.chunks)} chunks)")
        return len(document.chunks)
    
    def ingest_text(
        self,
        text: str,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        context_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest raw text directly.
        
        Args:
            text: Raw text content
            document_id: Unique identifier for this document
            metadata: Optional metadata
            context_type: Optional context type
            
        Returns:
            Ingestion result
        """
        self._ensure_initialized()
        
        metadata = metadata or {}
        if context_type:
            metadata["context_type"] = context_type
        
        # Create chunks
        chunks = self._document_processor.process_text_directly(
            text=text,
            document_id=document_id,
            metadata=metadata
        )
        
        if not chunks:
            return {"error": "No chunks created from text", "chunks_created": 0}
        
        # Prepare for storage
        docs_to_store = [{"content": c.content, "metadata": c.metadata} for c in chunks]
        contents = [c.content for c in chunks]
        
        # Generate embeddings and store
        embeddings = self._embedding_service.generate_embeddings_batch(contents)
        ids = [c.chunk_id for c in chunks]
        
        self._vector_store.add_documents(
            documents=docs_to_store,
            embeddings=embeddings,
            ids=ids
        )
        
        return {
            "document_id": document_id,
            "chunks_created": len(chunks)
        }
    
    def query(
        self,
        query: str,
        top_k: int = 5,
        context_type: Optional[ContextType] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> RetrievalResult:
        """
        Query the RAG system for relevant context.
        
        Args:
            query: Natural language query
            top_k: Number of results to return
            context_type: Optional context type filter
            filters: Additional metadata filters
            
        Returns:
            RetrievalResult with relevant documents
        """
        self._ensure_initialized()
        return self._retriever.retrieve(
            query=query,
            top_k=top_k,
            context_type=context_type,
            filters=filters
        )
    
    def get_budget_context(self, department: str) -> RetrievalResult:
        """Get budget context for a department."""
        self._ensure_initialized()
        return self._retriever.get_budget_context(department)
    
    def get_vendor_context(
        self, 
        vendor_id: Optional[str] = None,
        vendor_name: Optional[str] = None
    ) -> RetrievalResult:
        """Get vendor information context."""
        self._ensure_initialized()
        return self._retriever.get_vendor_context(vendor_id, vendor_name)
    
    def get_employee_history(
        self,
        employee_id: str,
        time_range: Optional[str] = None
    ) -> RetrievalResult:
        """Get employee spending history."""
        self._ensure_initialized()
        return self._retriever.get_spending_history(employee_id, time_range)
    
    def get_policy_context(
        self,
        policy_type: Optional[str] = None,
        amount: Optional[float] = None
    ) -> RetrievalResult:
        """Get relevant policy documents."""
        self._ensure_initialized()
        return self._retriever.get_policy_context(policy_type, amount)
    
    def get_comprehensive_context(
        self,
        employee_id: str,
        department: str,
        amount: float,
        category: str,
        vendor_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, RetrievalResult]:
        """
        Get comprehensive context for a payment request.
        
        This is the main method used by agents to gather all
        relevant context for decision making.
        """
        self._ensure_initialized()
        return self._retriever.get_comprehensive_context(
            employee_id=employee_id,
            department=department,
            amount=amount,
            category=category,
            vendor_id=vendor_id,
            description=description
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        self._ensure_initialized()
        
        vector_stats = self._vector_store.get_collection_stats()
        
        return {
            **self._ingestion_stats,
            "vector_store": vector_stats,
            "collection_name": self.collection_name,
            "embedding_model": self.embedding_model
        }
    
    def clear(self):
        """Clear all documents from the vector store."""
        self._ensure_initialized()
        self._vector_store.clear_collection()
        self._ingestion_stats = {
            "total_documents": 0,
            "total_chunks": 0,
            "last_ingestion": None
        }
        print("Vector store cleared")


# Singleton instance
_pipeline_instance: Optional[RAGPipeline] = None


def get_rag_pipeline(
    collection_name: str = "financial_docs",
    **kwargs
) -> RAGPipeline:
    """Get or create the RAG pipeline singleton."""
    global _pipeline_instance
    
    if _pipeline_instance is None:
        _pipeline_instance = RAGPipeline(collection_name=collection_name, **kwargs)
    
    return _pipeline_instance
