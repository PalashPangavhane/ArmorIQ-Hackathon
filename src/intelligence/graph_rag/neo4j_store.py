"""
Neo4j Graph Store Module

Provides persistent storage in Neo4j graph database.
Supports vector search with graph traversal for GraphRAG.
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

from .entity_extractor import Entity, Relationship, EntityType
from .knowledge_graph import GraphNode, KnowledgeGraph


@dataclass
class Neo4jConfig:
    """Neo4j connection configuration."""
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"
    
    @classmethod
    def from_env(cls) -> "Neo4jConfig":
        """Load config from environment variables."""
        return cls(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
            database=os.getenv("NEO4J_DATABASE", "neo4j")
        )


class Neo4jStore:
    """
    Neo4j graph database interface for GraphRAG.
    
    Features:
    - Entity and relationship storage
    - Vector similarity search (with Neo4j vector index)
    - Graph pattern matching with Cypher
    - Hybrid search combining vectors and graph structure
    """
    
    def __init__(
        self,
        config: Optional[Neo4jConfig] = None,
        embedding_dimension: int = 768
    ):
        """
        Initialize Neo4j store.
        
        Args:
            config: Neo4j connection config
            embedding_dimension: Dimension of embedding vectors
        """
        self.config = config or Neo4jConfig.from_env()
        self.embedding_dimension = embedding_dimension
        self._driver = None
        self._initialized = False
    
    def initialize(self):
        """Initialize Neo4j connection and create indices."""
        try:
            from neo4j import GraphDatabase
            
            self._driver = GraphDatabase.driver(
                self.config.uri,
                auth=(self.config.username, self.config.password)
            )
            
            # Verify connection
            self._driver.verify_connectivity()
            
            # Create indices and constraints
            self._setup_schema()
            
            self._initialized = True
            print(f"Neo4j connected: {self.config.uri}")
            
        except ImportError:
            raise ImportError("neo4j package required. Install with: pip install neo4j")
        except Exception as e:
            print(f"Warning: Neo4j connection failed: {e}")
            print("Falling back to in-memory knowledge graph")
            self._initialized = False
    
    def _ensure_initialized(self):
        """Ensure store is initialized."""
        if not self._initialized:
            self.initialize()
    
    def _setup_schema(self):
        """Create necessary indices and constraints."""
        with self._driver.session(database=self.config.database) as session:
            # Create constraints for unique IDs
            try:
                session.run("""
                    CREATE CONSTRAINT entity_id IF NOT EXISTS
                    FOR (e:Entity) REQUIRE e.id IS UNIQUE
                """)
            except:
                pass
            
            # Create index for entity types
            try:
                session.run("""
                    CREATE INDEX entity_type IF NOT EXISTS
                    FOR (e:Entity) ON (e.type)
                """)
            except:
                pass
            
            # Create index for entity names
            try:
                session.run("""
                    CREATE INDEX entity_name IF NOT EXISTS
                    FOR (e:Entity) ON (e.name)
                """)
            except:
                pass
            
            # Create vector index if Neo4j version supports it
            try:
                session.run(f"""
                    CREATE VECTOR INDEX entity_embedding IF NOT EXISTS
                    FOR (e:Entity) ON (e.embedding)
                    OPTIONS {{indexConfig: {{
                        `vector.dimensions`: {self.embedding_dimension},
                        `vector.similarity_function`: 'cosine'
                    }}}}
                """)
            except:
                pass  # Vector index not supported in this version
    
    def add_entity(
        self,
        entity: Entity,
        embedding: Optional[List[float]] = None
    ) -> str:
        """Add an entity to Neo4j."""
        self._ensure_initialized()
        
        if not self._initialized:
            return entity.id
        
        with self._driver.session(database=self.config.database) as session:
            # Create or merge entity node
            query = """
                MERGE (e:Entity {id: $id})
                SET e.name = $name,
                    e.type = $type,
                    e.description = $description,
                    e.source_chunk_id = $source_chunk_id,
                    e.confidence = $confidence
            """
            
            params = {
                "id": entity.id,
                "name": entity.name,
                "type": entity.entity_type.value,
                "description": entity.description,
                "source_chunk_id": entity.source_chunk_id,
                "confidence": entity.confidence
            }
            
            # Add properties
            for key, value in entity.properties.items():
                if isinstance(value, (str, int, float, bool)):
                    query = query.rstrip() + f", e.{key} = ${key}"
                    params[key] = value
            
            # Add embedding if provided
            if embedding:
                query = query.rstrip() + ", e.embedding = $embedding"
                params["embedding"] = embedding
            
            session.run(query, params)
            
            # Add type-specific label
            label = entity.entity_type.value.capitalize()
            session.run(f"""
                MATCH (e:Entity {{id: $id}})
                SET e:{label}
            """, {"id": entity.id})
        
        return entity.id
    
    def add_relationship(self, relationship: Relationship) -> str:
        """Add a relationship to Neo4j."""
        self._ensure_initialized()
        
        if not self._initialized:
            return relationship.id
        
        with self._driver.session(database=self.config.database) as session:
            # Create relationship
            query = f"""
                MATCH (source:Entity {{id: $source_id}})
                MATCH (target:Entity {{id: $target_id}})
                MERGE (source)-[r:{relationship.relationship_type}]->(target)
                SET r.id = $rel_id,
                    r.description = $description,
                    r.weight = $weight,
                    r.source_chunk_id = $source_chunk_id
            """
            
            session.run(query, {
                "source_id": relationship.source_entity_id,
                "target_id": relationship.target_entity_id,
                "rel_id": relationship.id,
                "description": relationship.description,
                "weight": relationship.weight,
                "source_chunk_id": relationship.source_chunk_id
            })
        
        return relationship.id
    
    def add_entities_batch(
        self,
        entities: List[Entity],
        embeddings: Optional[List[List[float]]] = None
    ):
        """Add multiple entities in batch."""
        self._ensure_initialized()
        
        if not self._initialized:
            return
        
        with self._driver.session(database=self.config.database) as session:
            def create_entities(tx):
                for i, entity in enumerate(entities):
                    emb = embeddings[i] if embeddings and i < len(embeddings) else None
                    
                    params = {
                        "id": entity.id,
                        "name": entity.name,
                        "type": entity.entity_type.value,
                        "description": entity.description,
                        "source_chunk_id": entity.source_chunk_id,
                        "confidence": entity.confidence,
                        "embedding": emb
                    }
                    
                    tx.run("""
                        MERGE (e:Entity {id: $id})
                        SET e.name = $name,
                            e.type = $type,
                            e.description = $description,
                            e.source_chunk_id = $source_chunk_id,
                            e.confidence = $confidence,
                            e.embedding = $embedding
                    """, params)
            
            session.execute_write(create_entities)
    
    def add_relationships_batch(self, relationships: List[Relationship]):
        """Add multiple relationships in batch."""
        self._ensure_initialized()
        
        if not self._initialized:
            return
        
        with self._driver.session(database=self.config.database) as session:
            def create_relationships(tx):
                for rel in relationships:
                    tx.run(f"""
                        MATCH (source:Entity {{id: $source_id}})
                        MATCH (target:Entity {{id: $target_id}})
                        MERGE (source)-[r:{rel.relationship_type}]->(target)
                        SET r.id = $rel_id,
                            r.description = $description,
                            r.weight = $weight
                    """, {
                        "source_id": rel.source_entity_id,
                        "target_id": rel.target_entity_id,
                        "rel_id": rel.id,
                        "description": rel.description,
                        "weight": rel.weight
                    })
            
            session.execute_write(create_relationships)
    
    def vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        node_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search entities by vector similarity.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results
            node_types: Filter by entity types
            
        Returns:
            List of matching entities with scores
        """
        self._ensure_initialized()
        
        if not self._initialized:
            return []
        
        with self._driver.session(database=self.config.database) as session:
            # Try vector index first
            try:
                type_filter = ""
                if node_types:
                    types_str = "', '".join(node_types)
                    type_filter = f"WHERE e.type IN ['{types_str}']"
                
                result = session.run(f"""
                    CALL db.index.vector.queryNodes('entity_embedding', $top_k, $embedding)
                    YIELD node, score
                    WITH node as e, score
                    {type_filter}
                    RETURN e.id as id, e.name as name, e.type as type,
                           e.description as description, score
                    LIMIT $top_k
                """, {
                    "embedding": query_embedding,
                    "top_k": top_k
                })
                
                return [dict(record) for record in result]
                
            except Exception:
                # Fallback: return all entities (no vector search)
                result = session.run("""
                    MATCH (e:Entity)
                    RETURN e.id as id, e.name as name, e.type as type,
                           e.description as description, 0.5 as score
                    LIMIT $top_k
                """, {"top_k": top_k})
                
                return [dict(record) for record in result]
    
    def graph_search(
        self,
        start_entity_id: str,
        max_depth: int = 2,
        relationship_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search graph starting from an entity.
        
        Args:
            start_entity_id: Starting entity ID
            max_depth: Maximum traversal depth
            relationship_types: Filter by relationship types
            limit: Maximum results
            
        Returns:
            Dict with nodes and relationships
        """
        self._ensure_initialized()
        
        if not self._initialized:
            return {"nodes": [], "relationships": []}
        
        with self._driver.session(database=self.config.database) as session:
            rel_pattern = ""
            if relationship_types:
                rel_types = "|".join(relationship_types)
                rel_pattern = f":{rel_types}"
            
            result = session.run(f"""
                MATCH path = (start:Entity {{id: $start_id}})-[r{rel_pattern}*1..{max_depth}]-(connected)
                WITH start, connected, relationships(path) as rels
                UNWIND rels as rel
                WITH COLLECT(DISTINCT start) + COLLECT(DISTINCT connected) as nodes,
                     COLLECT(DISTINCT rel) as relationships
                UNWIND nodes as n
                WITH COLLECT(DISTINCT {{
                    id: n.id,
                    name: n.name,
                    type: n.type,
                    description: n.description
                }}) as nodes, relationships
                UNWIND relationships as r
                RETURN nodes,
                       COLLECT(DISTINCT {{
                           source: startNode(r).id,
                           target: endNode(r).id,
                           type: type(r),
                           description: r.description
                       }}) as relationships
                LIMIT 1
            """, {"start_id": start_entity_id})
            
            record = result.single()
            if record:
                return {
                    "nodes": record["nodes"][:limit],
                    "relationships": record["relationships"]
                }
            
            return {"nodes": [], "relationships": []}
    
    def hybrid_search(
        self,
        query_embedding: List[float],
        query_text: str,
        top_k: int = 10,
        graph_depth: int = 1
    ) -> Dict[str, Any]:
        """
        Hybrid search combining vector similarity and graph traversal.
        
        Args:
            query_embedding: Query vector for similarity search
            query_text: Query text for additional matching
            top_k: Number of initial results
            graph_depth: Depth to expand graph context
            
        Returns:
            Dict with vector_results, graph_context, and combined_results
        """
        # Get vector search results
        vector_results = self.vector_search(query_embedding, top_k)
        
        # Expand each result with graph context
        expanded_results = []
        all_graph_nodes = set()
        
        for result in vector_results:
            entity_id = result["id"]
            graph_context = self.graph_search(entity_id, max_depth=graph_depth)
            
            expanded_results.append({
                "entity": result,
                "graph_context": graph_context
            })
            
            for node in graph_context.get("nodes", []):
                all_graph_nodes.add(node["id"])
        
        return {
            "vector_results": vector_results,
            "expanded_results": expanded_results,
            "total_graph_nodes": len(all_graph_nodes)
        }
    
    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_length: int = 4
    ) -> List[List[Dict[str, Any]]]:
        """Find paths between two entities."""
        self._ensure_initialized()
        
        if not self._initialized:
            return []
        
        with self._driver.session(database=self.config.database) as session:
            result = session.run(f"""
                MATCH path = shortestPath(
                    (source:Entity {{id: $source_id}})-[*1..{max_length}]-(target:Entity {{id: $target_id}})
                )
                RETURN [node in nodes(path) | {{
                    id: node.id,
                    name: node.name,
                    type: node.type
                }}] as path_nodes,
                [rel in relationships(path) | {{
                    type: type(rel),
                    description: rel.description
                }}] as path_rels
            """, {
                "source_id": source_id,
                "target_id": target_id
            })
            
            paths = []
            for record in result:
                paths.append({
                    "nodes": record["path_nodes"],
                    "relationships": record["path_rels"]
                })
            
            return paths
    
    def get_entity_context(
        self,
        entity_id: str,
        include_neighbors: bool = True,
        neighbor_depth: int = 1
    ) -> Dict[str, Any]:
        """Get full context for an entity."""
        self._ensure_initialized()
        
        if not self._initialized:
            return {}
        
        with self._driver.session(database=self.config.database) as session:
            # Get entity details
            entity_result = session.run("""
                MATCH (e:Entity {id: $id})
                RETURN e
            """, {"id": entity_id})
            
            entity_record = entity_result.single()
            if not entity_record:
                return {}
            
            entity_data = dict(entity_record["e"])
            
            context = {
                "entity": entity_data,
                "neighbors": [],
                "relationships": []
            }
            
            if include_neighbors:
                # Get neighbors
                neighbor_result = session.run(f"""
                    MATCH (e:Entity {{id: $id}})-[r]-(neighbor:Entity)
                    RETURN neighbor.id as id, neighbor.name as name, 
                           neighbor.type as type, type(r) as rel_type,
                           r.description as rel_description
                """, {"id": entity_id})
                
                for record in neighbor_result:
                    context["neighbors"].append({
                        "id": record["id"],
                        "name": record["name"],
                        "type": record["type"],
                        "relationship": record["rel_type"],
                        "rel_description": record["rel_description"]
                    })
            
            return context
    
    def execute_cypher(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute raw Cypher query."""
        self._ensure_initialized()
        
        if not self._initialized:
            return []
        
        with self._driver.session(database=self.config.database) as session:
            result = session.run(query, params or {})
            return [dict(record) for record in result]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        self._ensure_initialized()
        
        if not self._initialized:
            return {"status": "disconnected"}
        
        with self._driver.session(database=self.config.database) as session:
            # Count nodes and relationships
            result = session.run("""
                MATCH (n:Entity)
                WITH count(n) as node_count
                MATCH ()-[r]->()
                RETURN node_count, count(r) as rel_count
            """)
            
            record = result.single()
            
            # Get type distribution
            type_result = session.run("""
                MATCH (n:Entity)
                RETURN n.type as type, count(*) as count
            """)
            
            type_counts = {r["type"]: r["count"] for r in type_result}
            
            return {
                "status": "connected",
                "node_count": record["node_count"] if record else 0,
                "relationship_count": record["rel_count"] if record else 0,
                "type_distribution": type_counts
            }
    
    def clear_all(self):
        """Clear all data from the database."""
        self._ensure_initialized()
        
        if not self._initialized:
            return
        
        with self._driver.session(database=self.config.database) as session:
            session.run("MATCH (n) DETACH DELETE n")
    
    def close(self):
        """Close the database connection."""
        if self._driver:
            self._driver.close()
            self._driver = None
            self._initialized = False


# Convenience function for getting store instance
_neo4j_store = None

def get_neo4j_store() -> Neo4jStore:
    """Get or create singleton Neo4j store."""
    global _neo4j_store
    if _neo4j_store is None:
        _neo4j_store = Neo4jStore()
    return _neo4j_store
