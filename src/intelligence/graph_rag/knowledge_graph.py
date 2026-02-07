"""
Knowledge Graph Module

Manages the in-memory knowledge graph using NetworkX.
Supports graph operations, community detection, and path finding.
"""

import json
import pickle
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict

import networkx as nx

from .entity_extractor import Entity, Relationship, EntityType


@dataclass
class GraphNode:
    """Represents a node in the knowledge graph."""
    id: str
    name: str
    node_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.node_type,
            "properties": self.properties
        }


@dataclass
class GraphEdge:
    """Represents an edge in the knowledge graph."""
    source_id: str
    target_id: str
    edge_type: str
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.edge_type,
            "weight": self.weight,
            "properties": self.properties
        }


class KnowledgeGraph:
    """
    In-memory knowledge graph using NetworkX.
    
    Supports:
    - Adding/removing nodes and edges
    - Graph traversal and path finding
    - Community detection
    - Subgraph extraction
    - Graph persistence
    """
    
    def __init__(self, persist_path: Optional[str] = None):
        """
        Initialize knowledge graph.
        
        Args:
            persist_path: Optional path for graph persistence
        """
        self.graph = nx.DiGraph()
        self.persist_path = Path(persist_path) if persist_path else None
        self._node_index: Dict[str, GraphNode] = {}
        self._type_index: Dict[str, Set[str]] = defaultdict(set)
        self._name_index: Dict[str, str] = {}  # lowercase name -> id
        
        if self.persist_path and self.persist_path.exists():
            self.load()
    
    def add_entity(self, entity: Entity, embedding: Optional[List[float]] = None) -> str:
        """
        Add an entity as a node to the graph.
        
        Args:
            entity: Entity to add
            embedding: Optional embedding vector
            
        Returns:
            Node ID
        """
        node = GraphNode(
            id=entity.id,
            name=entity.name,
            node_type=entity.entity_type.value,
            properties={
                "description": entity.description,
                **entity.properties,
                "source_chunk_id": entity.source_chunk_id
            },
            embedding=embedding
        )
        
        # Add to NetworkX graph
        self.graph.add_node(
            entity.id,
            name=entity.name,
            type=entity.entity_type.value,
            description=entity.description,
            **entity.properties
        )
        
        # Update indices
        self._node_index[entity.id] = node
        self._type_index[entity.entity_type.value].add(entity.id)
        self._name_index[entity.name.lower()] = entity.id
        
        return entity.id
    
    def add_relationship(self, relationship: Relationship) -> str:
        """
        Add a relationship as an edge to the graph.
        
        Args:
            relationship: Relationship to add
            
        Returns:
            Edge key
        """
        self.graph.add_edge(
            relationship.source_entity_id,
            relationship.target_entity_id,
            key=relationship.id,
            type=relationship.relationship_type,
            weight=relationship.weight,
            description=relationship.description,
            **relationship.properties
        )
        
        return relationship.id
    
    def add_entities_batch(
        self,
        entities: List[Entity],
        embeddings: Optional[List[List[float]]] = None
    ) -> List[str]:
        """Add multiple entities at once."""
        ids = []
        for i, entity in enumerate(entities):
            emb = embeddings[i] if embeddings and i < len(embeddings) else None
            ids.append(self.add_entity(entity, emb))
        return ids
    
    def add_relationships_batch(self, relationships: List[Relationship]) -> List[str]:
        """Add multiple relationships at once."""
        return [self.add_relationship(rel) for rel in relationships]
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID."""
        return self._node_index.get(node_id)
    
    def get_node_by_name(self, name: str) -> Optional[GraphNode]:
        """Get a node by name (case-insensitive)."""
        node_id = self._name_index.get(name.lower())
        if node_id:
            return self._node_index.get(node_id)
        return None
    
    def get_nodes_by_type(self, node_type: str) -> List[GraphNode]:
        """Get all nodes of a specific type."""
        node_ids = self._type_index.get(node_type, set())
        return [self._node_index[nid] for nid in node_ids if nid in self._node_index]
    
    def get_neighbors(
        self,
        node_id: str,
        direction: str = "both",
        edge_types: Optional[List[str]] = None,
        max_depth: int = 1
    ) -> List[Tuple[GraphNode, str, int]]:
        """
        Get neighboring nodes.
        
        Args:
            node_id: Starting node ID
            direction: "in", "out", or "both"
            edge_types: Filter by edge types
            max_depth: Maximum traversal depth
            
        Returns:
            List of (node, relationship_type, depth) tuples
        """
        if node_id not in self.graph:
            return []
        
        neighbors = []
        visited = {node_id}
        queue = [(node_id, 0)]
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if depth >= max_depth:
                continue
            
            # Get edges based on direction
            if direction in ("out", "both"):
                for _, target, data in self.graph.out_edges(current_id, data=True):
                    if target not in visited:
                        edge_type = data.get("type", "RELATED_TO")
                        if edge_types is None or edge_type in edge_types:
                            if target in self._node_index:
                                neighbors.append((self._node_index[target], edge_type, depth + 1))
                            visited.add(target)
                            queue.append((target, depth + 1))
            
            if direction in ("in", "both"):
                for source, _, data in self.graph.in_edges(current_id, data=True):
                    if source not in visited:
                        edge_type = data.get("type", "RELATED_TO")
                        if edge_types is None or edge_type in edge_types:
                            if source in self._node_index:
                                neighbors.append((self._node_index[source], edge_type, depth + 1))
                            visited.add(source)
                            queue.append((source, depth + 1))
        
        return neighbors
    
    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_length: int = 5
    ) -> Optional[List[Tuple[str, str, str]]]:
        """
        Find shortest path between two nodes.
        
        Returns:
            List of (source_id, edge_type, target_id) tuples, or None
        """
        try:
            path = nx.shortest_path(
                self.graph,
                source=source_id,
                target=target_id
            )
            
            if len(path) > max_length + 1:
                return None
            
            result = []
            for i in range(len(path) - 1):
                edge_data = self.graph.get_edge_data(path[i], path[i + 1])
                edge_type = "RELATED_TO"
                if edge_data:
                    # Get first edge if multiple
                    first_key = list(edge_data.keys())[0]
                    edge_type = edge_data[first_key].get("type", "RELATED_TO")
                result.append((path[i], edge_type, path[i + 1]))
            
            return result
        except nx.NetworkXNoPath:
            return None
    
    def get_subgraph(
        self,
        center_node_id: str,
        max_depth: int = 2,
        max_nodes: int = 50
    ) -> "KnowledgeGraph":
        """
        Extract a subgraph centered on a node.
        
        Args:
            center_node_id: Center node ID
            max_depth: Maximum depth from center
            max_nodes: Maximum nodes to include
            
        Returns:
            New KnowledgeGraph with subgraph
        """
        if center_node_id not in self.graph:
            return KnowledgeGraph()
        
        # BFS to get nodes
        visited = {center_node_id}
        queue = [(center_node_id, 0)]
        
        while queue and len(visited) < max_nodes:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            
            for neighbor in self.graph.neighbors(current):
                if neighbor not in visited and len(visited) < max_nodes:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
            
            for predecessor in self.graph.predecessors(current):
                if predecessor not in visited and len(visited) < max_nodes:
                    visited.add(predecessor)
                    queue.append((predecessor, depth + 1))
        
        # Create subgraph
        subgraph = KnowledgeGraph()
        subgraph.graph = self.graph.subgraph(visited).copy()
        
        for node_id in visited:
            if node_id in self._node_index:
                subgraph._node_index[node_id] = self._node_index[node_id]
                node = self._node_index[node_id]
                subgraph._type_index[node.node_type].add(node_id)
                subgraph._name_index[node.name.lower()] = node_id
        
        return subgraph
    
    def detect_communities(self) -> Dict[str, int]:
        """
        Detect communities in the graph using Louvain algorithm.
        
        Returns:
            Dict mapping node_id to community_id
        """
        # Convert to undirected for community detection
        undirected = self.graph.to_undirected()
        
        try:
            from networkx.algorithms.community import louvain_communities
            communities = louvain_communities(undirected)
            
            node_to_community = {}
            for i, community in enumerate(communities):
                for node_id in community:
                    node_to_community[node_id] = i
            
            return node_to_community
        except Exception:
            # Fallback: each connected component is a community
            components = list(nx.connected_components(undirected))
            node_to_community = {}
            for i, component in enumerate(components):
                for node_id in component:
                    node_to_community[node_id] = i
            return node_to_community
    
    def get_community_summary(self, community_id: int) -> Dict[str, Any]:
        """Get summary of a community."""
        communities = self.detect_communities()
        
        community_nodes = [
            node_id for node_id, cid in communities.items()
            if cid == community_id
        ]
        
        # Get node details
        nodes = [self._node_index[nid] for nid in community_nodes if nid in self._node_index]
        
        # Count types
        type_counts = defaultdict(int)
        for node in nodes:
            type_counts[node.node_type] += 1
        
        return {
            "community_id": community_id,
            "node_count": len(nodes),
            "type_distribution": dict(type_counts),
            "key_entities": [n.name for n in nodes[:10]]
        }
    
    def calculate_centrality(self) -> Dict[str, float]:
        """Calculate PageRank centrality for all nodes."""
        try:
            return nx.pagerank(self.graph)
        except:
            return {}
    
    def get_important_nodes(self, top_k: int = 10) -> List[Tuple[GraphNode, float]]:
        """Get most important nodes by centrality."""
        centrality = self.calculate_centrality()
        
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        
        result = []
        for node_id, score in sorted_nodes[:top_k]:
            if node_id in self._node_index:
                result.append((self._node_index[node_id], score))
        
        return result
    
    def search_nodes(
        self,
        query: str,
        node_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[GraphNode]:
        """
        Search nodes by name/description.
        
        Args:
            query: Search query
            node_types: Filter by node types
            limit: Maximum results
            
        Returns:
            List of matching nodes
        """
        query_lower = query.lower()
        results = []
        
        for node in self._node_index.values():
            if node_types and node.node_type not in node_types:
                continue
            
            # Check name and description
            if query_lower in node.name.lower():
                results.append((node, 1.0))  # Exact name match
            elif query_lower in node.properties.get("description", "").lower():
                results.append((node, 0.5))  # Description match
        
        # Sort by score and return
        results.sort(key=lambda x: x[1], reverse=True)
        return [node for node, _ in results[:limit]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary representation."""
        return {
            "nodes": [node.to_dict() for node in self._node_index.values()],
            "edges": [
                {
                    "source": u,
                    "target": v,
                    "type": data.get("type", "RELATED_TO"),
                    "weight": data.get("weight", 1.0),
                    "properties": {k: v for k, v in data.items() if k not in ("type", "weight")}
                }
                for u, v, data in self.graph.edges(data=True)
            ]
        }
    
    def save(self, path: Optional[str] = None):
        """Save graph to disk."""
        save_path = Path(path) if path else self.persist_path
        if not save_path:
            raise ValueError("No persist path specified")
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save as pickle for full fidelity
        with open(save_path, 'wb') as f:
            pickle.dump({
                'graph': self.graph,
                'node_index': self._node_index,
                'type_index': dict(self._type_index),
                'name_index': self._name_index
            }, f)
        
        # Also save JSON for debugging
        json_path = save_path.with_suffix('.json')
        with open(json_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
    
    def load(self, path: Optional[str] = None):
        """Load graph from disk."""
        load_path = Path(path) if path else self.persist_path
        if not load_path or not load_path.exists():
            return
        
        with open(load_path, 'rb') as f:
            data = pickle.load(f)
            self.graph = data['graph']
            self._node_index = data['node_index']
            self._type_index = defaultdict(set, data['type_index'])
            self._name_index = data['name_index']
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "num_nodes": self.graph.number_of_nodes(),
            "num_edges": self.graph.number_of_edges(),
            "node_types": {k: len(v) for k, v in self._type_index.items()},
            "density": nx.density(self.graph) if self.graph.number_of_nodes() > 0 else 0,
            "is_connected": nx.is_weakly_connected(self.graph) if self.graph.number_of_nodes() > 0 else True
        }
    
    def clear(self):
        """Clear all data from the graph."""
        self.graph.clear()
        self._node_index.clear()
        self._type_index.clear()
        self._name_index.clear()
