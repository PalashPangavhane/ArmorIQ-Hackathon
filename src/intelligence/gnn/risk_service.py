"""
Risk Service Module

Service layer for GNN-based risk assessment.
Provides risk signals to the control layer.

KEY HACKATHON PRINCIPLE:
This service is READ-ONLY. It provides risk signals that influence
policy decisions but NEVER directly executes or blocks transactions.
The actual blocking is done by the Enforcement Gateway based on
combined policy + risk evaluation.

ARCHITECTURE:
                                    
    [Transaction Request]           
            |                       
            v                       
    ┌───────────────────┐          
    │  RiskAssessment   │  <-- READ-ONLY Layer
    │     Service       │          
    └───────────────────┘          
            |                       
            v                       
    ┌───────────────────┐          
    │   Risk Signal     │          
    │  (score + reasons)│          
    └───────────────────┘          
            |                       
            v                       
    ┌───────────────────┐          
    │  Policy Engine    │  <-- Makes blocking decisions
    │  + Risk Integrator│          
    └───────────────────┘          
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from .graph_builder import TransactionGraphBuilder, NodeType, EdgeType, create_sample_graph
from .risk_model import FraudRiskModel, RiskSignal, RiskLevel


class RiskAssessmentService:
    """
    Service for assessing transaction risk using GNN.
    
    This service:
    1. Maintains the transaction graph
    2. Runs risk prediction on new transactions
    3. Provides risk profiles for entities
    4. Detects anomalous patterns
    
    CRITICAL: This service is READ-ONLY. It produces signals
    but cannot block or approve transactions directly.
    """
    
    def __init__(
        self,
        graph_builder: Optional[TransactionGraphBuilder] = None,
        risk_model: Optional[FraudRiskModel] = None
    ):
        self.graph_builder = graph_builder or TransactionGraphBuilder()
        self.risk_model = risk_model or FraudRiskModel()
        
        # Assessment history for audit trail
        self._assessment_history: List[Dict[str, Any]] = []
    
    def assess_transaction_risk(
        self,
        transaction: Dict[str, Any]
    ) -> RiskSignal:
        """
        Assess risk for a single transaction.
        
        Args:
            transaction: Transaction details including:
                - amount: Transaction amount
                - employee_id / agent_id: Requesting employee
                - vendor_id / vendor: Target vendor (if applicable)
                - category: Transaction category
                - timestamp: Transaction time
                
        Returns:
            RiskSignal with assessment results
        """
        # Normalize transaction data
        normalized = self._normalize_transaction(transaction)
        
        # Get graph context for the entities involved
        graph_context = self._get_graph_context(normalized)
        
        # Run risk prediction
        risk_signal = self.risk_model.predict_risk(
            transaction_data=normalized,
            graph_context=graph_context
        )
        
        # Update the transaction graph
        self.graph_builder.update_from_transaction(normalized)
        
        # Store assessment for audit
        self._record_assessment(normalized, risk_signal)
        
        return risk_signal
    
    def assess_approval_risk(
        self,
        approval_request: Dict[str, Any]
    ) -> RiskSignal:
        """
        Assess risk for an approval request.
        
        Similar to transaction risk but considers approval-specific factors.
        """
        # Extract transaction from approval request
        params = approval_request.get("parameters", {})
        transaction = {
            "amount": params.get("amount", 0),
            "vendor": params.get("vendor", ""),
            "category": params.get("category", ""),
            "agent_id": approval_request.get("agent_id", ""),
            "timestamp": datetime.now().isoformat()
        }
        
        return self.assess_transaction_risk(transaction)
    
    def get_entity_risk_profile(
        self,
        entity_id: str,
        entity_type: str
    ) -> Dict[str, Any]:
        """
        Get risk profile for an entity (employee, vendor, etc.).
        
        Returns a comprehensive risk profile including:
        - Historical patterns
        - Risk score trends
        - Typical behavior
        - Anomaly indicators
        """
        # Get pattern analysis from risk model
        pattern_analysis = self.risk_model.analyze_patterns(entity_id, entity_type)
        
        # Get graph statistics
        if entity_type == "employee":
            graph_stats = self.graph_builder.get_employee_stats(entity_id)
        else:
            graph_stats = self.graph_builder.get_vendor_stats(entity_id)
        
        # Get recent assessments
        recent_assessments = [
            a for a in self._assessment_history[-50:]
            if a.get("entity_id") == entity_id
        ]
        
        # Calculate aggregate risk
        recent_scores = [a.get("risk_score", 0) for a in recent_assessments]
        avg_risk = sum(recent_scores) / len(recent_scores) if recent_scores else 0
        
        return {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "pattern_analysis": pattern_analysis,
            "graph_stats": graph_stats,
            "recent_assessment_count": len(recent_assessments),
            "average_risk_score": round(avg_risk, 3),
            "risk_trend": self._calculate_risk_trend(recent_scores)
        }
    
    def update_graph_with_transaction(
        self,
        transaction: Dict[str, Any]
    ):
        """Update the transaction graph with new data."""
        normalized = self._normalize_transaction(transaction)
        self.graph_builder.update_from_transaction(normalized)
    
    def batch_assess(
        self,
        transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Assess risk for a batch of transactions.
        
        Returns list of transactions with their risk signals.
        """
        results = []
        for tx in transactions:
            signal = self.assess_transaction_risk(tx)
            results.append({
                "transaction": tx,
                "risk_signal": signal.to_dict()
            })
        return results
    
    def get_high_risk_transactions(
        self,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Get all transactions above risk threshold."""
        return [
            a for a in self._assessment_history
            if a.get("risk_score", 0) >= threshold
        ]
    
    def get_assessment_summary(self) -> Dict[str, Any]:
        """Get summary of all risk assessments."""
        if not self._assessment_history:
            return {
                "total_assessments": 0,
                "message": "No assessments yet"
            }
        
        scores = [a.get("risk_score", 0) for a in self._assessment_history]
        levels = [a.get("risk_level", "LOW") for a in self._assessment_history]
        
        return {
            "total_assessments": len(self._assessment_history),
            "average_risk_score": round(sum(scores) / len(scores), 3),
            "max_risk_score": max(scores),
            "min_risk_score": min(scores),
            "high_risk_count": levels.count("HIGH"),
            "medium_risk_count": levels.count("MEDIUM"),
            "low_risk_count": levels.count("LOW"),
            "graph_stats": self.graph_builder.get_statistics().to_dict()
        }
    
    def _normalize_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize transaction data to standard format."""
        return {
            "amount": transaction.get("amount", 0),
            "vendor": transaction.get("vendor", transaction.get("vendor_id", "")),
            "vendor_id": transaction.get("vendor_id", transaction.get("vendor", "")),
            "category": transaction.get("category", ""),
            "employee_id": transaction.get("employee_id", transaction.get("agent_id", "")),
            "agent_id": transaction.get("agent_id", transaction.get("employee_id", "")),
            "timestamp": transaction.get("timestamp", datetime.now().isoformat()),
            "description": transaction.get("description", ""),
            "target_id": transaction.get("target_id", "")
        }
    
    def _get_graph_context(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Get graph context for transaction entities."""
        employee_id = transaction.get("employee_id", "")
        vendor_id = transaction.get("vendor_id", "")
        
        context = {
            "employee_neighbors": [],
            "vendor_neighbors": [],
            "employee_history": [],
            "vendor_history": []
        }
        
        if employee_id:
            context["employee_neighbors"] = self.graph_builder.get_neighbor_nodes(employee_id)
            context["employee_history"] = self.graph_builder.get_transaction_history(employee_id)
        
        if vendor_id:
            context["vendor_neighbors"] = self.graph_builder.get_neighbor_nodes(vendor_id)
            context["vendor_history"] = self.graph_builder.get_transaction_history(vendor_id)
        
        return context
    
    def _record_assessment(self, transaction: Dict[str, Any], signal: RiskSignal):
        """Record assessment for audit trail."""
        self._assessment_history.append({
            "timestamp": datetime.now().isoformat(),
            "entity_id": transaction.get("employee_id", ""),
            "vendor_id": transaction.get("vendor_id", ""),
            "amount": transaction.get("amount", 0),
            "risk_score": signal.risk_score,
            "risk_level": signal.risk_level.value,
            "risk_reasons": signal.risk_reasons
        })
    
    def _calculate_risk_trend(self, scores: List[float]) -> str:
        """Calculate risk trend from recent scores."""
        if len(scores) < 3:
            return "insufficient_data"
        
        recent = scores[-3:]
        older = scores[-6:-3] if len(scores) >= 6 else scores[:-3]
        
        if not older:
            return "insufficient_data"
        
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        
        diff = recent_avg - older_avg
        
        if diff > 0.1:
            return "increasing"
        elif diff < -0.1:
            return "decreasing"
        return "stable"
    
    def reset(self):
        """Reset the service state."""
        self.graph_builder.clear()
        self.risk_model.reset()
        self._assessment_history.clear()


# Global service instance
_risk_service: Optional[RiskAssessmentService] = None


def get_risk_service() -> RiskAssessmentService:
    """Get the global risk assessment service instance."""
    global _risk_service
    if _risk_service is None:
        _risk_service = RiskAssessmentService()
    return _risk_service


def create_demo_service() -> RiskAssessmentService:
    """Create a risk service with sample data for demos."""
    # Create with sample graph
    graph = create_sample_graph()
    model = FraudRiskModel()
    model.load_model()
    
    service = RiskAssessmentService(
        graph_builder=graph,
        risk_model=model
    )
    
    return service
