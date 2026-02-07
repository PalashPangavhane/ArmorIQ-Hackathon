"""
Hybrid RAG Pipeline

State-of-the-Art RAG implementation combining:
1. Dense vector retrieval (semantic similarity)
2. Graph-based retrieval (structural relationships)
3. Community-aware summarization (topic clustering)

This hybrid approach provides superior context retrieval for complex domains.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
from datetime import datetime


class RetrievalStrategy(Enum):
    """Retrieval strategy options."""
    VECTOR_ONLY = "vector_only"      # Traditional RAG
    GRAPH_ONLY = "graph_only"        # Graph traversal only
    HYBRID = "hybrid"                # Combine vector + graph
    ADAPTIVE = "adaptive"            # Auto-select based on query


@dataclass
class RAGResponse:
    """Response from RAG pipeline."""
    answer: str
    context: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    retrieval_strategy: str = "hybrid"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "context": self.context,
            "sources": self.sources,
            "confidence": self.confidence,
            "retrieval_strategy": self.retrieval_strategy,
            "metadata": self.metadata
        }


class HybridRAGPipeline:
    """
    Hybrid RAG Pipeline combining vector and graph-based retrieval.
    
    Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │                      HYBRID RAG PIPELINE                        │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                 │
    │   ┌─────────┐                                                   │
    │   │  Query  │                                                   │
    │   └────┬────┘                                                   │
    │        │                                                        │
    │        ▼                                                        │
    │   ┌────────────────┐                                            │
    │   │ Query Analysis │──── Determines optimal strategy            │
    │   └───────┬────────┘                                            │
    │           │                                                     │
    │     ┌─────┴─────┐                                               │
    │     ▼           ▼                                               │
    │ ┌────────┐  ┌────────┐                                          │
    │ │ Vector │  │ Graph  │                                          │
    │ │  RAG   │  │  RAG   │                                          │
    │ └───┬────┘  └───┬────┘                                          │
    │     │           │                                               │
    │     └─────┬─────┘                                               │
    │           ▼                                                     │
    │   ┌───────────────┐                                             │
    │   │ Context Merge │──── Rerank + Dedupe + Weight                │
    │   └───────┬───────┘                                             │
    │           ▼                                                     │
    │   ┌───────────────┐                                             │
    │   │  LLM Answer   │──── Generate response with context          │
    │   └───────┬───────┘                                             │
    │           ▼                                                     │
    │   ┌───────────────┐                                             │
    │   │   Response    │                                             │
    │   └───────────────┘                                             │
    └─────────────────────────────────────────────────────────────────┘
    """
    
    def __init__(
        self,
        embedding_service=None,
        llm_service=None,
        vector_store=None,
        knowledge_graph=None,
        neo4j_store=None,
        default_strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        vector_weight: float = 0.5,
        graph_weight: float = 0.5,
        max_context_tokens: int = 4000
    ):
        """
        Initialize hybrid RAG pipeline.
        
        Args:
            embedding_service: Service for embeddings
            llm_service: LLM for generation
            vector_store: Vector database
            knowledge_graph: In-memory knowledge graph
            neo4j_store: Neo4j graph store
            default_strategy: Default retrieval strategy
            vector_weight: Weight for vector results (0-1)
            graph_weight: Weight for graph results (0-1)
            max_context_tokens: Max tokens for context
        """
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.vector_store = vector_store
        self.knowledge_graph = knowledge_graph
        self.neo4j_store = neo4j_store
        
        self.default_strategy = default_strategy
        self.vector_weight = vector_weight
        self.graph_weight = graph_weight
        self.max_context_tokens = max_context_tokens
        
        # Graph retriever
        self.graph_retriever = None
        
        # Statistics
        self.stats = {
            "queries_processed": 0,
            "vector_retrievals": 0,
            "graph_retrievals": 0,
            "hybrid_retrievals": 0
        }
    
    def _ensure_services(self):
        """Lazy load services if not provided."""
        if self.embedding_service is None:
            from ..rag.embedding_service import EmbeddingService
            self.embedding_service = EmbeddingService()
        
        if self.llm_service is None:
            from ..llm.ollama_service import OllamaLLMService
            self.llm_service = OllamaLLMService()
        
        if self.graph_retriever is None:
            from .graph_retriever import GraphRetriever
            self.graph_retriever = GraphRetriever(
                knowledge_graph=self.knowledge_graph,
                neo4j_store=self.neo4j_store,
                embedding_service=self.embedding_service
            )
    
    def query(
        self,
        question: str,
        strategy: Optional[RetrievalStrategy] = None,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> RAGResponse:
        """
        Process a query through the hybrid RAG pipeline.
        
        Args:
            question: User's question
            strategy: Retrieval strategy to use
            top_k: Number of results to retrieve
            filters: Optional filters for retrieval
            
        Returns:
            RAGResponse with answer and context
        """
        self._ensure_services()
        
        strategy = strategy or self.default_strategy
        self.stats["queries_processed"] += 1
        
        # Adaptive strategy selection
        if strategy == RetrievalStrategy.ADAPTIVE:
            strategy = self._select_strategy(question)
        
        # Retrieve context based on strategy
        if strategy == RetrievalStrategy.VECTOR_ONLY:
            context, sources = self._vector_retrieve(question, top_k, filters)
            self.stats["vector_retrievals"] += 1
            
        elif strategy == RetrievalStrategy.GRAPH_ONLY:
            context, sources = self._graph_retrieve(question, top_k, filters)
            self.stats["graph_retrievals"] += 1
            
        else:  # HYBRID
            context, sources = self._hybrid_retrieve(question, top_k, filters)
            self.stats["hybrid_retrievals"] += 1
        
        # Generate answer
        answer, confidence = self._generate_answer(question, context)
        
        return RAGResponse(
            answer=answer,
            context=context,
            sources=sources,
            confidence=confidence,
            retrieval_strategy=strategy.value,
            metadata={
                "top_k": top_k,
                "timestamp": datetime.now().isoformat(),
                "context_length": len(context)
            }
        )
    
    def _select_strategy(self, question: str) -> RetrievalStrategy:
        """
        Adaptively select retrieval strategy based on query characteristics.
        
        Heuristics:
        - Questions about relationships -> GRAPH
        - Questions with entity names -> HYBRID  
        - General questions -> VECTOR
        """
        question_lower = question.lower()
        
        # Graph-heavy indicators
        graph_keywords = [
            "relationship", "connect", "related", "between",
            "approve", "report to", "manages", "owns",
            "path", "chain", "flow", "process"
        ]
        
        # Check for graph indicators
        graph_score = sum(1 for kw in graph_keywords if kw in question_lower)
        
        if graph_score >= 2:
            return RetrievalStrategy.GRAPH_ONLY
        elif graph_score >= 1:
            return RetrievalStrategy.HYBRID
        else:
            return RetrievalStrategy.HYBRID  # Default to hybrid for best results
    
    def _vector_retrieve(
        self,
        question: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Retrieve using traditional vector similarity."""
        
        if self.vector_store is None:
            return "", []
        
        # Generate embedding
        embedding = self.embedding_service.generate_query_embedding(question)
        
        # Search vector store
        results = self.vector_store.similarity_search(
            embedding,
            top_k=top_k
        )
        
        # Build context
        context_parts = []
        sources = []
        
        for doc in results:
            doc_id = doc.get("id", "unknown")
            text = doc.get("content", "")
            score = doc.get("similarity_score", 0.5)
            context_parts.append(f"[Source: {doc_id}]\n{text}\n")
            sources.append({
                "id": doc_id,
                "text": text[:200],
                "score": score,
                "type": "vector"
            })
        
        context = "\n---\n".join(context_parts)
        
        # Truncate if needed
        if len(context) > self.max_context_tokens * 4:
            context = context[:self.max_context_tokens * 4]
        
        return context, sources
    
    def _graph_retrieve(
        self,
        question: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Retrieve using graph-based retrieval."""
        
        if self.graph_retriever is None:
            return "", []
        
        entity_types = filters.get("entity_types") if filters else None
        
        # Get graph context
        graph_context = self.graph_retriever.retrieve(
            query=question,
            top_k=top_k,
            entity_types=entity_types,
            expand_graph=True,
            include_communities=True
        )
        
        # Convert to context string
        context = graph_context.to_context_string()
        
        # Build sources
        sources = []
        for match in graph_context.direct_matches:
            sources.append({
                "id": match.get("id"),
                "name": match.get("name"),
                "type": match.get("type"),
                "score": match.get("score", 0.5),
                "source_type": "graph"
            })
        
        return context, sources
    
    def _hybrid_retrieve(
        self,
        question: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Hybrid retrieval combining vector and graph approaches.
        
        Uses Reciprocal Rank Fusion (RRF) to combine results.
        """
        
        # Get vector results
        vector_context, vector_sources = self._vector_retrieve(
            question, top_k, filters
        )
        
        # Get graph results
        graph_context, graph_sources = self._graph_retrieve(
            question, top_k, filters
        )
        
        # Combine contexts
        combined_context = self._merge_contexts(
            vector_context,
            graph_context,
            self.vector_weight,
            self.graph_weight
        )
        
        # Combine and rerank sources
        combined_sources = self._reciprocal_rank_fusion(
            vector_sources,
            graph_sources
        )
        
        return combined_context, combined_sources
    
    def _merge_contexts(
        self,
        vector_context: str,
        graph_context: str,
        vector_weight: float,
        graph_weight: float
    ) -> str:
        """Merge vector and graph contexts."""
        
        parts = []
        
        # Prioritize based on weights
        if graph_weight >= vector_weight:
            if graph_context:
                parts.append("## Knowledge Graph Context\n" + graph_context)
            if vector_context:
                parts.append("\n## Document Context\n" + vector_context)
        else:
            if vector_context:
                parts.append("## Document Context\n" + vector_context)
            if graph_context:
                parts.append("\n## Knowledge Graph Context\n" + graph_context)
        
        combined = "\n".join(parts)
        
        # Truncate if needed
        max_chars = self.max_context_tokens * 4
        if len(combined) > max_chars:
            combined = combined[:max_chars]
        
        return combined
    
    def _reciprocal_rank_fusion(
        self,
        vector_sources: List[Dict[str, Any]],
        graph_sources: List[Dict[str, Any]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Combine sources using Reciprocal Rank Fusion.
        
        RRF score = Σ 1/(k + rank)
        """
        rrf_scores = {}
        source_data = {}
        
        # Score vector sources
        for rank, source in enumerate(vector_sources):
            source_id = source.get("id", str(rank))
            rrf_scores[source_id] = rrf_scores.get(source_id, 0) + 1 / (k + rank + 1)
            source_data[source_id] = source
        
        # Score graph sources
        for rank, source in enumerate(graph_sources):
            source_id = source.get("id", f"graph_{rank}")
            rrf_scores[source_id] = rrf_scores.get(source_id, 0) + 1 / (k + rank + 1)
            if source_id not in source_data:
                source_data[source_id] = source
        
        # Sort by combined score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        combined = []
        for source_id in sorted_ids:
            source = source_data[source_id].copy()
            source["rrf_score"] = rrf_scores[source_id]
            combined.append(source)
        
        return combined
    
    def _generate_answer(
        self,
        question: str,
        context: str
    ) -> Tuple[str, float]:
        """Generate answer using LLM."""
        
        if not context:
            return "I don't have enough context to answer this question.", 0.0
        
        prompt = f"""You are an expert AI assistant for payment security and approval workflows.

Use the following context to answer the question accurately and concisely.
If the context doesn't contain the answer, say so clearly.

## Context:
{context}

## Question:
{question}

## Answer:"""
        
        try:
            response = self.llm_service.generate(prompt)
            
            # Estimate confidence based on context relevance
            confidence = min(0.9, 0.5 + len(context) / 10000)
            
            return response, confidence
            
        except Exception as e:
            return f"Error generating response: {str(e)}", 0.0
    
    def ingest_document(
        self,
        text: str,
        doc_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Ingest a document into both vector store and knowledge graph.
        
        Args:
            text: Document text
            doc_id: Document identifier
            metadata: Optional metadata
        """
        self._ensure_services()
        
        # Chunk the document
        chunks = self._chunk_text(text)
        
        # Ingest into vector store
        if self.vector_store:
            documents = []
            embeddings = []
            ids = []
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                embedding = self.embedding_service.generate_embedding(chunk)
                documents.append({"content": chunk, "metadata": metadata or {}})
                embeddings.append(embedding)
                ids.append(chunk_id)
            self.vector_store.add_documents(documents, embeddings, ids)
        
        # Extract entities and build graph
        if self.knowledge_graph or self.neo4j_store:
            from .entity_extractor import EntityExtractor
            extractor = EntityExtractor(self.llm_service)
            
            entities, relationships = extractor.extract_from_text(
                text,
                chunk_id=doc_id
            )
            
            # Add to knowledge graph
            if self.knowledge_graph:
                for entity in entities:
                    desc = entity.description or entity.name
                    self.knowledge_graph.add_entity(
                        entity=entity,
                        embedding=self.embedding_service.generate_embedding(
                            f"{entity.name}: {desc}"
                        )
                    )
                
                for rel in relationships:
                    source_node = self.knowledge_graph.get_node_by_name(rel.source_entity_id)
                    target_node = self.knowledge_graph.get_node_by_name(rel.target_entity_id)
                    if source_node and target_node:
                        self.knowledge_graph.add_relationship(
                            source_id=source_node.id,
                            target_id=target_node.id,
                            rel_type=rel.relationship_type.replace(" ", "_").upper(),
                            properties={"weight": rel.weight}
                        )
            
            # Add to Neo4j
            if self.neo4j_store and self.neo4j_store._initialized:
                for entity in entities:
                    desc = entity.description or entity.name
                    self.neo4j_store.add_entity(
                        entity_id=entity.id or f"{doc_id}_{entity.name}",
                        name=entity.name,
                        entity_type=entity.entity_type.value,
                        properties=entity.properties or {},
                        embedding=self.embedding_service.generate_embedding(
                            f"{entity.name}: {desc}"
                        )
                    )
                
                for rel in relationships:
                    self.neo4j_store.add_relationship(
                        source_name=rel.source_entity_id,
                        target_name=rel.target_entity_id,
                        rel_type=rel.relationship_type.replace(" ", "_").upper(),
                        properties={"weight": rel.weight, "source": doc_id}
                    )
    
    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[str]:
        """Chunk text with overlap."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to end at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                if last_period > chunk_size // 2:
                    chunk = chunk[:last_period + 1]
                    end = start + last_period + 1
            
            chunks.append(chunk)
            start = end - overlap
        
        return chunks
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        vector_size = 0
        if self.vector_store:
            if hasattr(self.vector_store, 'count'):
                vector_size = self.vector_store.count()
            elif hasattr(self.vector_store, '_store'):
                vector_size = len(getattr(self.vector_store._store, 'documents', []))
        
        return {
            **self.stats,
            "vector_store_size": vector_size,
            "graph_node_count": len(self.knowledge_graph._node_index) if self.knowledge_graph else 0,
            "graph_edge_count": (
                self.knowledge_graph.graph.number_of_edges() 
                if self.knowledge_graph and hasattr(self.knowledge_graph, 'graph') 
                else 0
            )
        }


# Convenience function
def create_hybrid_rag_pipeline(
    use_neo4j: bool = False,
    neo4j_uri: str = "bolt://localhost:7687",
    neo4j_user: str = "neo4j",
    neo4j_password: str = "password"
) -> HybridRAGPipeline:
    """
    Factory function to create a configured hybrid RAG pipeline.
    
    Args:
        use_neo4j: Whether to use Neo4j (requires running instance)
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        
    Returns:
        Configured HybridRAGPipeline instance
    """
    from ..rag.embedding_service import EmbeddingService
    from ..rag.vector_store import VectorStore
    from ..llm.ollama_service import OllamaLLMService
    from .knowledge_graph import KnowledgeGraph
    
    # Initialize services
    embedding_service = EmbeddingService()
    llm_service = OllamaLLMService()
    vector_store = VectorStore("armoriq_hybrid")
    knowledge_graph = KnowledgeGraph()
    
    neo4j_store = None
    if use_neo4j:
        from .neo4j_store import Neo4jStore, Neo4jConfig
        config = Neo4jConfig(
            uri=neo4j_uri,
            username=neo4j_user,
            password=neo4j_password
        )
        neo4j_store = Neo4jStore(config)
    
    return HybridRAGPipeline(
        embedding_service=embedding_service,
        llm_service=llm_service,
        vector_store=vector_store,
        knowledge_graph=knowledge_graph,
        neo4j_store=neo4j_store
    )
