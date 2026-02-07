"""
Graph Builder Module

Constructs transaction graphs for GNN-based risk analysis.

Graph Structure:
- Nodes: employees, vendors, accounts, departments
- Edges: transactions, approvals, reimbursements
- Attributes: amount, time, frequency, category

KEY HACKATHON FEATURE:
This builds the transaction graph that enables fraud detection by
analyzing relationships and patterns between entities.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json


class NodeType(Enum):
    EMPLOYEE = "employee"
    VENDOR = "vendor"
    ACCOUNT = "account"
    DEPARTMENT = "department"


class EdgeType(Enum):
    TRANSACTION = "transaction"
    APPROVAL = "approval"
    REIMBURSEMENT = "reimbursement"


@dataclass
class Node:
    """Represents a node in the transaction graph."""
    id: str
    node_type: NodeType
    attributes: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.node_type.value,
            "attributes": self.attributes
        }


@dataclass
class Edge:
    """Represents an edge in the transaction graph."""
    source_id: str
    target_id: str
    edge_type: EdgeType
    attributes: Dict[str, Any]  # amount, time, frequency, category
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.edge_type.value,
            "attributes": self.attributes
        }


@dataclass
class GraphStatistics:
    """Statistics about the transaction graph."""
    total_nodes: int
    total_edges: int
    nodes_by_type: Dict[str, int]
    total_transaction_volume: float
    average_transaction_amount: float
    unique_vendors: int
    unique_employees: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "nodes_by_type": self.nodes_by_type,
            "total_transaction_volume": self.total_transaction_volume,
            "average_transaction_amount": self.average_transaction_amount,
            "unique_vendors": self.unique_vendors,
            "unique_employees": self.unique_employees
        }


class TransactionGraphBuilder:
    """
    Builds and updates transaction graphs for risk analysis.
    
    ARCHITECTURE:
    
    [Transactions] --> [GraphBuilder] --> [Transaction Graph]
                                                |
                                                v
                                          [GNN Model]
                                                |
                                                v
                                          [Risk Signal]
    
    The graph captures relationships between:
    - Employees and their spending patterns
    - Vendors and their transaction frequencies
    - Departments and their budgets
    - Unusual connections and patterns
    """
    
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._transaction_history: List[Dict[str, Any]] = []
        self._employee_stats: Dict[str, Dict[str, Any]] = {}
        self._vendor_stats: Dict[str, Dict[str, Any]] = {}
    
    def add_node(
        self, 
        node_id: str, 
        node_type: NodeType, 
        attributes: Dict[str, Any]
    ) -> Node:
        """Add a node to the graph."""
        node = Node(id=node_id, node_type=node_type, attributes=attributes)
        self.nodes[node_id] = node
        return node
    
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        amount: float,
        timestamp: str,
        category: Optional[str] = None,
        additional_attrs: Optional[Dict[str, Any]] = None
    ) -> Edge:
        """Add an edge (transaction) to the graph."""
        attributes = {
            "amount": amount,
            "timestamp": timestamp,
            "category": category,
            **(additional_attrs or {})
        }
        edge = Edge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            attributes=attributes
        )
        self.edges.append(edge)
        
        # Update statistics
        self._update_entity_stats(source_id, target_id, amount, category)
        
        return edge
    
    def _update_entity_stats(
        self, 
        employee_id: str, 
        vendor_id: str, 
        amount: float,
        category: Optional[str]
    ):
        """Update transaction statistics for entities."""
        # Update employee stats
        if employee_id not in self._employee_stats:
            self._employee_stats[employee_id] = {
                "total_transactions": 0,
                "total_amount": 0.0,
                "vendors": set(),
                "categories": {},
                "amounts": []
            }
        
        stats = self._employee_stats[employee_id]
        stats["total_transactions"] += 1
        stats["total_amount"] += amount
        stats["vendors"].add(vendor_id)
        stats["amounts"].append(amount)
        
        if category:
            stats["categories"][category] = stats["categories"].get(category, 0) + 1
        
        # Update vendor stats
        if vendor_id not in self._vendor_stats:
            self._vendor_stats[vendor_id] = {
                "total_transactions": 0,
                "total_amount": 0.0,
                "employees": set(),
                "first_seen": datetime.now().isoformat()
            }
        
        vstats = self._vendor_stats[vendor_id]
        vstats["total_transactions"] += 1
        vstats["total_amount"] += amount
        vstats["employees"].add(employee_id)
    
    def build_graph(self) -> Dict[str, Any]:
        """
        Build the graph structure for GNN processing.
        
        Returns a dictionary with:
        - nodes: List of node dictionaries
        - edges: List of edge dictionaries
        - adjacency: Adjacency list representation
        - statistics: Graph statistics
        """
        nodes_list = [node.to_dict() for node in self.nodes.values()]
        edges_list = [edge.to_dict() for edge in self.edges]
        
        # Build adjacency list
        adjacency = {}
        for edge in self.edges:
            if edge.source_id not in adjacency:
                adjacency[edge.source_id] = []
            adjacency[edge.source_id].append({
                "target": edge.target_id,
                "type": edge.edge_type.value,
                "amount": edge.attributes.get("amount", 0)
            })
        
        # Calculate statistics
        stats = self.get_statistics()
        
        return {
            "nodes": nodes_list,
            "edges": edges_list,
            "adjacency": adjacency,
            "statistics": stats.to_dict()
        }
    
    def update_from_transaction(self, transaction: Dict[str, Any]):
        """
        Update graph with a new transaction.
        
        Args:
            transaction: Dictionary containing:
                - employee_id: Who initiated
                - vendor_id: Target vendor
                - amount: Transaction amount
                - category: Category of spend
                - timestamp: When it occurred
        """
        employee_id = transaction.get("employee_id", transaction.get("agent_id", "unknown"))
        vendor_id = transaction.get("vendor_id", transaction.get("vendor", "unknown"))
        amount = transaction.get("amount", 0)
        category = transaction.get("category")
        timestamp = transaction.get("timestamp", datetime.now().isoformat())
        
        # Ensure nodes exist
        if employee_id not in self.nodes:
            self.add_node(employee_id, NodeType.EMPLOYEE, {
                "name": employee_id,
                "created_at": timestamp
            })
        
        if vendor_id not in self.nodes:
            self.add_node(vendor_id, NodeType.VENDOR, {
                "name": vendor_id,
                "first_transaction": timestamp
            })
        
        # Add edge
        self.add_edge(
            source_id=employee_id,
            target_id=vendor_id,
            edge_type=EdgeType.TRANSACTION,
            amount=amount,
            timestamp=timestamp,
            category=category
        )
        
        # Store in history
        self._transaction_history.append(transaction)
    
    def get_statistics(self) -> GraphStatistics:
        """Get graph statistics."""
        nodes_by_type = {}
        for node in self.nodes.values():
            type_name = node.node_type.value
            nodes_by_type[type_name] = nodes_by_type.get(type_name, 0) + 1
        
        total_amount = sum(
            edge.attributes.get("amount", 0) for edge in self.edges
        )
        
        avg_amount = total_amount / len(self.edges) if self.edges else 0
        
        unique_vendors = len([n for n in self.nodes.values() if n.node_type == NodeType.VENDOR])
        unique_employees = len([n for n in self.nodes.values() if n.node_type == NodeType.EMPLOYEE])
        
        return GraphStatistics(
            total_nodes=len(self.nodes),
            total_edges=len(self.edges),
            nodes_by_type=nodes_by_type,
            total_transaction_volume=total_amount,
            average_transaction_amount=avg_amount,
            unique_vendors=unique_vendors,
            unique_employees=unique_employees
        )
    
    def get_employee_stats(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific employee."""
        if employee_id not in self._employee_stats:
            return None
        
        stats = self._employee_stats[employee_id].copy()
        # Convert sets to lists for JSON serialization
        stats["vendors"] = list(stats["vendors"])
        
        # Calculate average
        if stats["amounts"]:
            stats["average_amount"] = sum(stats["amounts"]) / len(stats["amounts"])
            stats["max_amount"] = max(stats["amounts"])
            stats["min_amount"] = min(stats["amounts"])
        
        return stats
    
    def get_vendor_stats(self, vendor_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific vendor."""
        if vendor_id not in self._vendor_stats:
            return None
        
        stats = self._vendor_stats[vendor_id].copy()
        stats["employees"] = list(stats["employees"])
        return stats
    
    def get_neighbor_nodes(self, node_id: str) -> List[Dict[str, Any]]:
        """Get all nodes connected to a given node."""
        neighbors = []
        for edge in self.edges:
            if edge.source_id == node_id:
                if edge.target_id in self.nodes:
                    neighbors.append(self.nodes[edge.target_id].to_dict())
            elif edge.target_id == node_id:
                if edge.source_id in self.nodes:
                    neighbors.append(self.nodes[edge.source_id].to_dict())
        return neighbors
    
    def get_transaction_history(
        self, 
        entity_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent transaction history for an entity."""
        relevant = [
            t for t in self._transaction_history
            if t.get("employee_id") == entity_id or 
               t.get("vendor_id") == entity_id or
               t.get("agent_id") == entity_id or
               t.get("vendor") == entity_id
        ]
        return relevant[-limit:]
    
    def export_to_json(self, filepath: str):
        """Export graph to JSON file."""
        graph_data = self.build_graph()
        with open(filepath, 'w') as f:
            json.dump(graph_data, f, indent=2, default=str)
    
    def import_from_json(self, filepath: str):
        """Import graph from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Import nodes
        for node_data in data.get("nodes", []):
            self.add_node(
                node_id=node_data["id"],
                node_type=NodeType(node_data["type"]),
                attributes=node_data.get("attributes", {})
            )
        
        # Import edges
        for edge_data in data.get("edges", []):
            attrs = edge_data.get("attributes", {})
            self.add_edge(
                source_id=edge_data["source"],
                target_id=edge_data["target"],
                edge_type=EdgeType(edge_data["type"]),
                amount=attrs.get("amount", 0),
                timestamp=attrs.get("timestamp", ""),
                category=attrs.get("category"),
                additional_attrs={k: v for k, v in attrs.items() if k not in ["amount", "timestamp", "category"]}
            )
    
    def clear(self):
        """Clear the graph."""
        self.nodes.clear()
        self.edges.clear()
        self._transaction_history.clear()
        self._employee_stats.clear()
        self._vendor_stats.clear()


def create_sample_graph() -> TransactionGraphBuilder:
    """Create a sample transaction graph for testing."""
    builder = TransactionGraphBuilder()
    
    # Add employees
    builder.add_node("emp_001", NodeType.EMPLOYEE, {"name": "John Smith", "department": "Engineering"})
    builder.add_node("emp_002", NodeType.EMPLOYEE, {"name": "Jane Doe", "department": "Marketing"})
    builder.add_node("emp_003", NodeType.EMPLOYEE, {"name": "Bob Wilson", "department": "Finance"})
    
    # Add vendors
    builder.add_node("vendor_001", NodeType.VENDOR, {"name": "Office Depot", "category": "office_supplies"})
    builder.add_node("vendor_002", NodeType.VENDOR, {"name": "AWS", "category": "software"})
    builder.add_node("vendor_003", NodeType.VENDOR, {"name": "Unknown LLC", "category": "services"})
    
    # Add normal transactions
    builder.add_edge("emp_001", "vendor_001", EdgeType.TRANSACTION, 250.0, "2024-01-15", "office_supplies")
    builder.add_edge("emp_001", "vendor_002", EdgeType.TRANSACTION, 5000.0, "2024-01-16", "software")
    builder.add_edge("emp_002", "vendor_001", EdgeType.TRANSACTION, 150.0, "2024-01-17", "office_supplies")
    builder.add_edge("emp_003", "vendor_002", EdgeType.TRANSACTION, 3000.0, "2024-01-18", "software")
    
    # Add suspicious transaction (new vendor, high amount)
    builder.add_edge("emp_001", "vendor_003", EdgeType.TRANSACTION, 25000.0, "2024-01-19", "services")
    
    return builder
