"""
CUDA-Accelerated Graph Neural Network

Implements GNN-based risk detection with NVIDIA GPU acceleration.
Uses PyTorch Geometric for efficient graph operations on CUDA.

Architecture:
- GraphSAGE / GAT layers for node embedding
- Transaction graph as input
- Risk score prediction per transaction

Requirements:
- torch (PyTorch with CUDA)
- torch-geometric (PyTorch Geometric)
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import math

# Try to import PyTorch
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch import Tensor
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    nn = None
    F = None
    Tensor = None

# Try to import PyTorch Geometric
try:
    from torch_geometric.nn import SAGEConv, GATConv, global_mean_pool
    from torch_geometric.data import Data, Batch
    TORCH_GEOMETRIC_AVAILABLE = True
except ImportError:
    TORCH_GEOMETRIC_AVAILABLE = False
    SAGEConv = None
    GATConv = None

from .device_manager import get_device, get_device_manager


@dataclass
class GNNConfig:
    """Configuration for GNN models."""
    input_dim: int = 16          # Node feature dimension
    hidden_dim: int = 64         # Hidden layer dimension
    output_dim: int = 32         # Output embedding dimension
    num_layers: int = 3          # Number of GNN layers
    dropout: float = 0.2         # Dropout rate
    heads: int = 4               # Attention heads (for GAT)
    use_attention: bool = True   # Use GAT vs GraphSAGE


# Placeholder classes when PyTorch not available
CUDAGraphNeuralNetwork = None
GraphSAGELayer = None
GATLayer = None


# Only define neural network classes if PyTorch is available
if TORCH_AVAILABLE and TORCH_GEOMETRIC_AVAILABLE:
    
    class GraphSAGELayer(nn.Module):
        """GraphSAGE convolution layer with residual connections."""
        
        def __init__(self, in_dim: int, out_dim: int, dropout: float = 0.2):
            super().__init__()
            self.conv = SAGEConv(in_dim, out_dim)
            self.norm = nn.LayerNorm(out_dim)
            self.dropout = nn.Dropout(dropout)
            self.residual = nn.Linear(in_dim, out_dim) if in_dim != out_dim else nn.Identity()
        
        def forward(self, x, edge_index):
            residual = self.residual(x)
            x = self.conv(x, edge_index)
            x = self.norm(x)
            x = F.relu(x)
            x = self.dropout(x)
            return x + residual

    class GATLayer(nn.Module):
        """Graph Attention Network layer."""
        
        def __init__(self, in_dim: int, out_dim: int, heads: int = 4, dropout: float = 0.2):
            super().__init__()
            self.conv = GATConv(in_dim, out_dim // heads, heads=heads, dropout=dropout)
            self.norm = nn.LayerNorm(out_dim)
            self.dropout = nn.Dropout(dropout)
            self.residual = nn.Linear(in_dim, out_dim) if in_dim != out_dim else nn.Identity()
        
        def forward(self, x, edge_index):
            residual = self.residual(x)
            x = self.conv(x, edge_index)
            x = self.norm(x)
            x = F.elu(x)
            x = self.dropout(x)
            return x + residual

    class CUDAGraphNeuralNetwork(nn.Module):
        """
        GPU-Accelerated Graph Neural Network for transaction risk analysis.
        
        Features:
        - Automatic CUDA device placement
        - Mixed precision training support
        - Batch inference for high throughput
        - GraphSAGE or GAT backbone
        """
        
        def __init__(self, config: Optional[GNNConfig] = None):
            super().__init__()
            self.config = config or GNNConfig()
            
            # Input projection
            self.input_proj = nn.Linear(self.config.input_dim, self.config.hidden_dim)
            
            # GNN layers
            self.gnn_layers = nn.ModuleList()
            
            if self.config.use_attention:
                for _ in range(self.config.num_layers):
                    self.gnn_layers.append(
                        GATLayer(self.config.hidden_dim, self.config.hidden_dim,
                                self.config.heads, self.config.dropout)
                    )
            else:
                for _ in range(self.config.num_layers):
                    self.gnn_layers.append(
                        GraphSAGELayer(self.config.hidden_dim, self.config.hidden_dim,
                                      self.config.dropout)
                    )
            
            # Output projection
            self.output_proj = nn.Sequential(
                nn.Linear(self.config.hidden_dim, self.config.output_dim),
                nn.ReLU(),
                nn.Dropout(self.config.dropout),
                nn.Linear(self.config.output_dim, 1),
                nn.Sigmoid()
            )
            
            # Risk classification head
            self.risk_classifier = nn.Sequential(
                nn.Linear(self.config.hidden_dim, 32),
                nn.ReLU(),
                nn.Linear(32, 3),
                nn.Softmax(dim=-1)
            )
        
        def forward(self, x, edge_index, batch=None):
            """Forward pass for risk prediction."""
            x = self.input_proj(x)
            x = F.relu(x)
            
            for layer in self.gnn_layers:
                x = layer(x, edge_index)
            
            risk_scores = self.output_proj(x)
            risk_classes = self.risk_classifier(x)
            
            return risk_scores, risk_classes
        
        def get_embeddings(self, x, edge_index):
            """Get node embeddings from GNN."""
            x = self.input_proj(x)
            x = F.relu(x)
            for layer in self.gnn_layers:
                x = layer(x, edge_index)
            return x


class CUDAGNNRiskModel:
    """
    High-level risk model with GPU acceleration.
    
    Wraps CUDAGraphNeuralNetwork with:
    - Automatic device management
    - Feature extraction from transactions
    - Graph construction
    - Batch inference
    - Heuristic fallback when PyTorch unavailable
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        config: Optional[GNNConfig] = None,
        force_cpu: bool = False
    ):
        self.model_path = model_path
        self.config = config or GNNConfig()
        
        # Device setup
        self._device_manager = get_device_manager()
        self._device = "cpu" if force_cpu else self._device_manager.get_optimal_device()
        
        # Initialize model
        self._model = None
        self._initialized = False
        
        # Statistics for normalization
        self._stats = {
            "amount_mean": 1000.0,
            "amount_std": 5000.0,
            "max_amount": 100000.0
        }
        
        # Entity profiles for feature extraction
        self._vendor_counts: Dict[str, int] = {}
        self._category_counts: Dict[str, int] = {}
        self._employee_profiles: Dict[str, Dict] = {}
    
    def initialize(self):
        """Initialize the model and move to GPU."""
        if self._initialized:
            return
        
        if TORCH_AVAILABLE and TORCH_GEOMETRIC_AVAILABLE and CUDAGraphNeuralNetwork is not None:
            self._model = CUDAGraphNeuralNetwork(self.config)
            self._model = self._model.to(self._device)
            self._model.eval()
            print(f"✅ CUDA GNN Risk Model initialized on {self._device}")
            
            if self.model_path:
                self._load_weights()
        else:
            print("⚠️ Running in heuristic mode (PyTorch/Geometric not available)")
        
        self._initialized = True
    
    def _load_weights(self):
        """Load pre-trained weights if available."""
        if not TORCH_AVAILABLE:
            return
        try:
            state_dict = torch.load(self.model_path, map_location=self._device)
            self._model.load_state_dict(state_dict)
            print(f"✅ Loaded weights from {self.model_path}")
        except FileNotFoundError:
            print(f"⚠️ No pre-trained weights found at {self.model_path}")
    
    def _extract_features(self, transaction: Dict[str, Any]) -> List[float]:
        """Extract numerical features from transaction."""
        amount = transaction.get("amount", 0)
        vendor = str(transaction.get("vendor", transaction.get("vendor_id", "unknown")))
        category = str(transaction.get("category", "unknown"))
        employee_id = str(transaction.get("employee_id", transaction.get("agent_id", "unknown")))
        timestamp = transaction.get("timestamp", "")
        
        # Parse timestamp
        hour = 12
        day_of_week = 0
        if timestamp:
            try:
                from datetime import datetime
                if isinstance(timestamp, str):
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                else:
                    dt = timestamp
                hour = dt.hour
                day_of_week = dt.weekday()
            except:
                pass
        
        # Update counts
        self._vendor_counts[vendor] = self._vendor_counts.get(vendor, 0) + 1
        self._category_counts[category] = self._category_counts.get(category, 0) + 1
        
        # Update employee profile
        if employee_id not in self._employee_profiles:
            self._employee_profiles[employee_id] = {"total_amount": 0, "count": 0, "avg_amount": 0}
        profile = self._employee_profiles[employee_id]
        profile["total_amount"] += amount
        profile["count"] += 1
        profile["avg_amount"] = profile["total_amount"] / profile["count"]
        
        # Extract features
        features = [
            (amount - self._stats["amount_mean"]) / self._stats["amount_std"],
            math.log1p(amount) / 10,
            1.0 if amount % 1000 == 0 and amount > 0 else 0.0,
            math.sin(2 * math.pi * hour / 24),
            math.cos(2 * math.pi * hour / 24),
            day_of_week / 6,
            min(self._vendor_counts.get(vendor, 0) / 100, 1.0),
            min(self._category_counts.get(category, 0) / 100, 1.0),
            profile["avg_amount"] / self._stats["max_amount"],
            min(profile["count"] / 100, 1.0),
            1.0 if self._vendor_counts.get(vendor, 0) <= 1 else 0.0,
            1.0 if profile["count"] <= 1 else 0.0,
            0.0, 0.0,  # velocity placeholders
            amount / max(profile["avg_amount"], 1.0) if profile["avg_amount"] > 0 else 1.0,
            0.3 if category.lower() in ["consulting", "services", "misc"] else 0.0
        ]
        
        return features
    
    def predict_risk(
        self,
        transaction: Dict[str, Any],
        graph_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Predict risk for a single transaction using GPU-accelerated GNN."""
        if not self._initialized:
            self.initialize()
        
        if self._model is not None and TORCH_AVAILABLE:
            return self._neural_predict(transaction, graph_context)
        
        return self._heuristic_predict(transaction)
    
    def _neural_predict(
        self,
        transaction: Dict[str, Any],
        graph_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Neural network prediction with CUDA acceleration."""
        with torch.no_grad():
            features = self._extract_features(transaction)
            x = torch.tensor([features], dtype=torch.float32).to(self._device)
            edge_index = torch.tensor([[0], [0]], dtype=torch.long).to(self._device)
            
            risk_scores, risk_classes = self._model(x, edge_index)
            
            risk_score = risk_scores[0].item()
            risk_probs = risk_classes[0].cpu().numpy()
            
            if risk_score < 0.3:
                risk_level = "LOW"
            elif risk_score < 0.7:
                risk_level = "MEDIUM"
            else:
                risk_level = "HIGH"
            
            return {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_reasons": self._extract_risk_factors(transaction, features),
                "class_probabilities": {
                    "low": float(risk_probs[0]),
                    "medium": float(risk_probs[1]),
                    "high": float(risk_probs[2])
                },
                "device": self._device,
                "inference_mode": "neural_cuda" if self._device == "cuda" else "neural_cpu"
            }
    
    def _heuristic_predict(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Heuristic fallback when GPU/neural model unavailable."""
        features = self._extract_features(transaction)
        amount = transaction.get("amount", 0)
        
        risk_score = 0.0
        risk_factors = []
        
        if amount > 10000:
            risk_score += 0.3
            risk_factors.append(f"Large amount: ${amount:,.2f}")
        elif amount > 5000:
            risk_score += 0.15
        
        if features[2] > 0:
            risk_score += 0.1
            risk_factors.append("Suspicious round amount")
        
        if features[10] > 0:
            risk_score += 0.2
            risk_factors.append("First-time vendor")
        
        if features[11] > 0:
            risk_score += 0.15
            risk_factors.append("New employee")
        
        if abs(features[3]) > 0.9:
            risk_score += 0.1
            risk_factors.append("Transaction outside business hours")
        
        risk_score = min(risk_score, 1.0)
        
        if risk_score < 0.3:
            risk_level = "LOW"
        elif risk_score < 0.7:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"
        
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_reasons": risk_factors,
            "inference_mode": "heuristic"
        }
    
    def _extract_risk_factors(self, transaction: Dict[str, Any], features: List[float]) -> List[str]:
        """Extract human-readable risk factors."""
        factors = []
        amount = transaction.get("amount", 0)
        
        if features[2] > 0:
            factors.append("Suspiciously round amount")
        if features[10] > 0:
            factors.append(f"New vendor: {transaction.get('vendor', 'unknown')}")
        if features[11] > 0:
            factors.append("First transaction from this employee")
        if amount > 10000:
            factors.append(f"Large transaction: ${amount:,.2f}")
        if features[14] > 2.0:
            factors.append("Amount significantly above employee average")
        
        return factors
    
    def predict_batch(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Batch prediction for multiple transactions (GPU optimized)."""
        if not self._initialized:
            self.initialize()
        
        if self._model is None or not TORCH_AVAILABLE:
            return [self._heuristic_predict(txn) for txn in transactions]
        
        with torch.no_grad():
            # Extract features for all transactions
            all_features = [self._extract_features(txn) for txn in transactions]
            x = torch.tensor(all_features, dtype=torch.float32).to(self._device)
            
            # Simple batch - each transaction as separate node
            num_nodes = len(transactions)
            edge_index = torch.tensor(
                [[i, i] for i in range(num_nodes)], dtype=torch.long
            ).t().contiguous().to(self._device)
            
            risk_scores, risk_classes = self._model(x, edge_index)
            
            results = []
            for i, txn in enumerate(transactions):
                score = risk_scores[i].item()
                
                if score < 0.3:
                    level = "LOW"
                elif score < 0.7:
                    level = "MEDIUM"
                else:
                    level = "HIGH"
                
                results.append({
                    "risk_score": score,
                    "risk_level": level,
                    "risk_reasons": self._extract_risk_factors(txn, all_features[i]),
                    "device": self._device,
                    "inference_mode": "batch_cuda" if self._device == "cuda" else "batch_cpu"
                })
            
            return results
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get current device information."""
        return {
            "device": self._device,
            "model_loaded": self._model is not None,
            "initialized": self._initialized,
            "torch_available": TORCH_AVAILABLE,
            "torch_geometric_available": TORCH_GEOMETRIC_AVAILABLE
        }
