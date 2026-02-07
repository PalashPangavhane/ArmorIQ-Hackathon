"""
Graph Retriever Module

Advanced retrieval combining vector search with graph traversal.
Core component of the GraphRAG pipeline for superior context retrieval.
"""

from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
import math

from .knowledge_graph import KnowledgeGraph, GraphNode
from .neo4j_store import Neo4jStore
from .entity_extractor import EntityType


@dataclass
class GraphContext:
    """
    Rich context from graph-based retrieval.
    
    Contains both the direct matches and expanded graph context.
    """
    query: str
    
    # Direct matches from vector search
    direct_matches: List[Dict[str, Any]] = field(default_factory=list)
    
    # Entities discovered through graph traversal
    graph_entities: List[Dict[str, Any]] = field(default_factory=list)
    
    # Relationships in the context
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    
    # Community/cluster summaries
    community_summaries: List[str] = field(default_factory=list)
    
    # Source documents referenced
    source_chunks: List[str] = field(default_factory=list)
    
    # Confidence score
    confidence: float = 0.0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_context_string(self) -> str:
        """Convert to string for LLM context."""
        parts = []
        
        # Direct matches
        if self.direct_matches:
            parts.append("=== RELEVANT ENTITIES ===")
            for match in self.direct_matches[:10]:
                name = match.get("name", "Unknown")
                entity_type = match.get("type", "unknown")
                desc = match.get("description", "")
                parts.append(f"- {name} ({entity_type}): {desc}")
        
        # Graph context
        if self.graph_entities:
            parts.append("\n=== RELATED CONTEXT ===")
            for entity in self.graph_entities[:15]:
                name = entity.get("name", "Unknown")
                rel = entity.get("relationship", "related to")
                parts.append(f"- {name} ({rel})")
        
        # Relationships
        if self.relationships:
            parts.append("\n=== KEY RELATIONSHIPS ===")
            for rel in self.relationships[:10]:
                source = rel.get("source_name", rel.get("source", "?"))
                target = rel.get("target_name", rel.get("target", "?"))
                rel_type = rel.get("type", "RELATED_TO")
                parts.append(f"- {source} --[{rel_type}]--> {target}")
        
        # Community summaries
        if self.community_summaries:
            parts.append("\n=== CONTEXT SUMMARIES ===")
            for summary in self.community_summaries[:3]:
                parts.append(f"- {summary}")
        
        return "\n".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "direct_matches": self.direct_matches,
            "graph_entities": self.graph_entities,
            "relationships": self.relationships,
            "community_summaries": self.community_summaries,
            "source_chunks": self.source_chunks,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


class GraphRetriever:
    """
    Advanced retriever that combines vector similarity with graph structure.
    
    Retrieval Strategy:
    1. Vector search to find initial relevant entities
    2. Graph traversal to expand context
    3. Community detection for topic clustering
    4. Path finding for relationship discovery
    5. Ranking and filtering
    
    This produces richer, more connected context than pure vector search.
    """
    
    def __init__(
        self,
        knowledge_graph: Optional[KnowledgeGraph] = None,
        neo4j_store: Optional[Neo4jStore] = None,
        embedding_service=None,
        default_top_k: int = 10,
        graph_expansion_depth: int = 2,
        use_communities: bool = True
    ):
        """
        Initialize graph retriever.
        
        Args:
            knowledge_graph: In-memory knowledge graph
            neo4j_store: Neo4j database store
            embedding_service: Service for generating embeddings
            default_top_k: Default number of results
            graph_expansion_depth: How deep to expand in graph
            use_communities: Whether to use community detection
        """
        self.knowledge_graph = knowledge_graph
        self.neo4j_store = neo4j_store
        self.embedding_service = embedding_service
        self.default_top_k = default_top_k
        self.graph_expansion_depth = graph_expansion_depth
        self.use_communities = use_communities
        
        # Cache for community summaries
        self._community_cache: Dict[int, str] = {}
    
    def _ensure_embedding_service(self):
        """Ensure embedding service is available."""
        if self.embedding_service is None:
            from ..rag.embedding_service import EmbeddingService
            self.embedding_service = EmbeddingService()
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        entity_types: Optional[List[str]] = None,
        expand_graph: bool = True,
        include_communities: bool = True
    ) -> GraphContext:
        """
        Retrieve context using hybrid vector + graph search.
        
        Args:
            query: Natural language query
            top_k: Number of initial results
            entity_types: Filter by entity types
            expand_graph: Whether to expand with graph traversal
            include_communities: Whether to include community summaries
            
        Returns:
            GraphContext with rich context information
        """
        top_k = top_k or self.default_top_k
        self._ensure_embedding_service()
        
        # Generate query embedding
        query_embedding = self.embedding_service.generate_query_embedding(query)
        
        # Initialize context
        context = GraphContext(query=query)
        
        # Step 1: Vector search for initial matches
        direct_matches = self._vector_search(query_embedding, top_k, entity_types)
        context.direct_matches = direct_matches
        
        # Step 2: Extract entities mentioned in query  
        query_entities = self._extract_query_entities(query)
        
        # Step 3: Graph expansion
        if expand_graph and direct_matches:
            graph_entities, relationships = self._expand_graph_context(
                direct_matches,
                query_entities
            )
            context.graph_entities = graph_entities
            context.relationships = relationships
        
        # Step 4: Community summaries
        if include_communities and self.use_communities:
            community_summaries = self._get_community_context(
                [m.get("id") for m in direct_matches]
            )
            context.community_summaries = community_summaries
        
        # Step 5: Collect source chunks
        source_chunks = set()
        for match in direct_matches:
            chunk_id = match.get("source_chunk_id")
            if chunk_id:
                source_chunks.add(chunk_id)
        context.source_chunks = list(source_chunks)
        
        # Calculate confidence
        if direct_matches:
            avg_score = sum(m.get("score", 0.5) for m in direct_matches) / len(direct_matches)
            context.confidence = min(avg_score, 1.0)
        
        # Metadata
        context.metadata = {
            "num_direct_matches": len(direct_matches),
            "num_graph_entities": len(context.graph_entities),
            "num_relationships": len(context.relationships),
            "expansion_depth": self.graph_expansion_depth
        }
        
        return context
    
    def _vector_search(
        self,
        query_embedding: List[float],
        top_k: int,
        entity_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search."""
        
        # Try Neo4j first
        if self.neo4j_store and self.neo4j_store._initialized:
            return self.neo4j_store.vector_search(
                query_embedding,
                top_k,
                entity_types
            )
        
        # Fallback to in-memory graph
        if self.knowledge_graph:
            return self._vector_search_inmemory(query_embedding, top_k, entity_types)
        
        return []
    
    def _vector_search_inmemory(
        self,
        query_embedding: List[float],
        top_k: int,
        entity_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Vector search in in-memory graph."""
        results = []
        
        for node in self.knowledge_graph._node_index.values():
            if entity_types and node.node_type not in entity_types:
                continue
            
            if node.embedding:
                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_embedding, node.embedding)
                results.append({
                    "id": node.id,
                    "name": node.name,
                    "type": node.node_type,
                    "description": node.properties.get("description", ""),
                    "score": similarity,
                    "source_chunk_id": node.properties.get("source_chunk_id", "")
                })
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)
    
    def _extract_query_entities(self, query: str) -> List[str]:
        """Extract potential entity references from query."""
        # Simple extraction - look for capitalized words and known patterns
        import re
        
        entities = []
        
        # Capitalized words (potential names)
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        entities.extend(capitalized)
        
        # Dollar amounts
        amounts = re.findall(r'\$[\d,]+(?:\.\d{2})?', query)
        entities.extend(amounts)
        
        return entities
    
    def _expand_graph_context(
        self,
        seed_matches: List[Dict[str, Any]],
        query_entities: List[str]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Expand context using graph traversal."""
        
        expanded_entities = []
        relationships = []
        seen_ids = set(m.get("id") for m in seed_matches)
        
        for match in seed_matches[:5]:  # Expand from top 5 matches
            entity_id = match.get("id")
            if not entity_id:
                continue
            
            # Get neighbors from graph
            if self.neo4j_store and self.neo4j_store._initialized:
                graph_context = self.neo4j_store.graph_search(
                    entity_id,
                    max_depth=self.graph_expansion_depth
                )
                
                for node in graph_context.get("nodes", []):
                    if node["id"] not in seen_ids:
                        expanded_entities.append(node)
                        seen_ids.add(node["id"])
                
                relationships.extend(graph_context.get("relationships", []))
            
            elif self.knowledge_graph:
                neighbors = self.knowledge_graph.get_neighbors(
                    entity_id,
                    direction="both",
                    max_depth=self.graph_expansion_depth
                )
                
                for node, rel_type, depth in neighbors:
                    if node.id not in seen_ids:
                        expanded_entities.append({
                            "id": node.id,
                            "name": node.name,
                            "type": node.node_type,
                            "relationship": rel_type,
                            "depth": depth
                        })
                        seen_ids.add(node.id)
                        
                        relationships.append({
                            "source": entity_id,
                            "target": node.id,
                            "source_name": match.get("name", ""),
                            "target_name": node.name,
                            "type": rel_type
                        })
        
        # Also try to find query entities in the graph
        for entity_name in query_entities:
            if self.knowledge_graph:
                node = self.knowledge_graph.get_node_by_name(entity_name)
                if node and node.id not in seen_ids:
                    expanded_entities.append({
                        "id": node.id,
                        "name": node.name,
                        "type": node.node_type,
                        "relationship": "query_mention"
                    })
                    seen_ids.add(node.id)
        
        return expanded_entities, relationships
    
    def _get_community_context(self, entity_ids: List[str]) -> List[str]:
        """Get community summaries for relevant entities."""
        summaries = []
        
        if not self.knowledge_graph:
            return summaries
        
        try:
            communities = self.knowledge_graph.detect_communities()
            
            # Find communities for our entities
            relevant_communities = set()
            for entity_id in entity_ids:
                if entity_id in communities:
                    relevant_communities.add(communities[entity_id])
            
            # Get summaries for relevant communities
            for community_id in list(relevant_communities)[:3]:
                if community_id in self._community_cache:
                    summaries.append(self._community_cache[community_id])
                else:
                    summary_data = self.knowledge_graph.get_community_summary(community_id)
                    summary = self._format_community_summary(summary_data)
                    self._community_cache[community_id] = summary
                    summaries.append(summary)
        except Exception as e:
            pass  # Community detection may fail on small graphs
        
        return summaries
    
    def _format_community_summary(self, summary_data: Dict[str, Any]) -> str:
        """Format community summary as string."""
        key_entities = summary_data.get("key_entities", [])[:5]
        type_dist = summary_data.get("type_distribution", {})
        
        entity_types = ", ".join(f"{k}: {v}" for k, v in type_dist.items())
        entities = ", ".join(key_entities)
        
        return f"Cluster with {summary_data.get('node_count', 0)} entities ({entity_types}). Key: {entities}"
    
    def find_entity_paths(
        self,
        source_name: str,
        target_name: str,
        max_length: int = 4
    ) -> List[Dict[str, Any]]:
        """Find paths between two named entities."""
        
        # Find entity IDs
        source_id = None
        target_id = None
        
        if self.knowledge_graph:
            source_node = self.knowledge_graph.get_node_by_name(source_name)
            target_node = self.knowledge_graph.get_node_by_name(target_name)
            
            if source_node:
                source_id = source_node.id
            if target_node:
                target_id = target_node.id
        
        if not source_id or not target_id:
            return []
        
        # Find paths
        if self.neo4j_store and self.neo4j_store._initialized:
            return self.neo4j_store.find_paths(source_id, target_id, max_length)
        
        if self.knowledge_graph:
            path = self.knowledge_graph.find_path(source_id, target_id, max_length)
            if path:
                return [{"path": path}]
        
        return []
    
    def get_entity_context(
        self,
        entity_name: str,
        depth: int = 2
    ) -> GraphContext:
        """Get full context for a named entity."""
        
        context = GraphContext(query=f"Context for {entity_name}")
        
        # Find entity
        entity_id = None
        entity_node = None
        
        if self.knowledge_graph:
            entity_node = self.knowledge_graph.get_node_by_name(entity_name)
            if entity_node:
                entity_id = entity_node.id
                context.direct_matches = [{
                    "id": entity_node.id,
                    "name": entity_node.name,
                    "type": entity_node.node_type,
                    "description": entity_node.properties.get("description", ""),
                    "score": 1.0
                }]
        
        if not entity_id:
            return context
        
        # Expand context
        if self.neo4j_store and self.neo4j_store._initialized:
            full_context = self.neo4j_store.get_entity_context(
                entity_id,
                include_neighbors=True,
                neighbor_depth=depth
            )
            
            context.graph_entities = full_context.get("neighbors", [])
        
        elif self.knowledge_graph:
            neighbors = self.knowledge_graph.get_neighbors(
                entity_id,
                direction="both",
                max_depth=depth
            )
            
            for node, rel_type, d in neighbors:
                context.graph_entities.append({
                    "id": node.id,
                    "name": node.name,
                    "type": node.node_type,
                    "relationship": rel_type,
                    "depth": d
                })
                
                context.relationships.append({
                    "source_name": entity_name,
                    "target_name": node.name,
                    "type": rel_type
                })
        
        context.confidence = 1.0
        return context
    
    def get_comprehensive_context(
        self,
        query: str,
        context_types: Optional[List[str]] = None
    ) -> Dict[str, GraphContext]:
        """
        Get comprehensive context from multiple perspectives.
        
        Args:
            query: Query text
            context_types: Types of context to retrieve
            
        Returns:
            Dict mapping context type to GraphContext
        """
        if context_types is None:
            context_types = ["policy", "budget", "vendor", "process"]
        
        results = {}
        
        for ctx_type in context_types:
            # Filter to specific entity types
            type_mapping = {
                "policy": ["policy", "rule", "threshold", "approval"],
                "budget": ["budget", "amount", "department"],
                "vendor": ["vendor", "organization"],
                "process": ["process", "approval", "role"]
            }
            
            entity_types = type_mapping.get(ctx_type, None)
            
            context = self.retrieve(
                query=query,
                top_k=5,
                entity_types=entity_types,
                expand_graph=True,
                include_communities=False
            )
            
            results[ctx_type] = context
        
        return results
