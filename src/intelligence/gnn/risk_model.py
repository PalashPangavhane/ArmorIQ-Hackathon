"""
Risk Model Module

GNN-based fraud and risk detection model.
Produces risk signals, NOT decisions.

KEY HACKATHON PRINCIPLE:
The GNN layer is READ-ONLY - it produces signals that influence
but do NOT directly control execution. This is a "fallback mechanism
that constrains or freezes execution under uncertainty."

IMPLEMENTATION NOTE:
For the hackathon demo, we implement a heuristic-based risk model
that simulates GNN behavior. This allows demonstration without
requiring trained models or GPU infrastructure.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import math


class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskFactor(Enum):
    """Types of risk factors detected."""
    NEW_VENDOR = "new_vendor"
    AMOUNT_SPIKE = "amount_spike"
    UNUSUAL_CATEGORY = "unusual_category"
    OFF_HOURS = "off_hours"
    VELOCITY_SPIKE = "velocity_spike"
    ROUND_AMOUNT = "round_amount"
    LARGE_AMOUNT = "large_amount"
    NEW_EMPLOYEE = "new_employee"
    UNUSUAL_PATTERN = "unusual_pattern"
    FIRST_TRANSACTION = "first_transaction"
    HIGH_FREQUENCY = "high_frequency"
    SPLIT_TRANSACTION = "split_transaction"


@dataclass
class RiskSignal:
    """
    Risk signal output from the GNN model.
    
    Example:
    {
        "risk_level": "LOW | MEDIUM | HIGH",
        "risk_score": 0.0 - 1.0,
        "risk_reasons": ["new_vendor", "amount_spike"]
    }
    """
    risk_level: RiskLevel
    risk_score: float  # 0.0 - 1.0
    risk_reasons: List[str]
    risk_factors: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "risk_reasons": self.risk_reasons,
            "risk_factors": self.risk_factors
        }


@dataclass
class EntityProfile:
    """Risk profile for an entity (employee, vendor, etc.)."""
    entity_id: str
    entity_type: str
    average_amount: float = 0.0
    total_transactions: int = 0
    total_amount: float = 0.0
    typical_categories: List[str] = field(default_factory=list)
    typical_vendors: List[str] = field(default_factory=list)
    first_transaction_date: Optional[str] = None
    last_transaction_date: Optional[str] = None
    risk_score_history: List[float] = field(default_factory=list)


class FraudRiskModel:
    """
    GNN-based fraud and risk detection model.
    
    ARCHITECTURE:
    
    [Transaction] --> [Feature Extraction] --> [Risk Calculation]
                           |                          |
                           v                          v
                   [Graph Context] --------> [Risk Score]
                                                   |
                                                   v
                                            [Risk Signal]
    
    RISK FACTORS (simulating GNN outputs):
    1. Amount anomaly (deviation from typical)
    2. Vendor novelty (first time vendor)
    3. Velocity (transaction frequency spike)
    4. Time anomaly (unusual hours/days)
    5. Category mismatch (unusual category for entity)
    6. Pattern break (deviation from historical patterns)
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self._model = None
        self._thresholds = {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.8
        }
        
        # Risk factor weights (simulating learned GNN weights)
        self._factor_weights = {
            RiskFactor.NEW_VENDOR.value: 0.25,
            RiskFactor.AMOUNT_SPIKE.value: 0.30,
            RiskFactor.UNUSUAL_CATEGORY.value: 0.15,
            RiskFactor.OFF_HOURS.value: 0.10,
            RiskFactor.VELOCITY_SPIKE.value: 0.20,
            RiskFactor.ROUND_AMOUNT.value: 0.05,
            RiskFactor.LARGE_AMOUNT.value: 0.20,
            RiskFactor.NEW_EMPLOYEE.value: 0.15,
            RiskFactor.UNUSUAL_PATTERN.value: 0.25,
            RiskFactor.FIRST_TRANSACTION.value: 0.10,
            RiskFactor.HIGH_FREQUENCY.value: 0.20,
            RiskFactor.SPLIT_TRANSACTION.value: 0.30
        }
        
        # Entity profiles (simulating graph embeddings)
        self._entity_profiles: Dict[str, EntityProfile] = {}
        
        # Transaction history for pattern detection
        self._transaction_history: List[Dict[str, Any]] = []
        
        # Known good vendors (simulating graph neighborhood reputation)
        self._trusted_vendors = {
            "office depot", "staples", "aws", "microsoft", "google cloud",
            "dell", "hp", "adobe", "salesforce", "slack"
        }
        
        # Suspicious patterns
        self._suspicious_patterns = {
            "round_amounts": [1000, 5000, 10000, 25000, 50000],
            "high_risk_categories": ["consulting", "services", "miscellaneous"],
            "off_hours": list(range(0, 6)) + list(range(22, 24))  # 10pm - 6am
        }
    
    def load_model(self):
        """Load the trained GNN model (simulated for demo)."""
        # In production, this would load PyTorch/TensorFlow model
        print("✅ GNN Risk Model loaded (heuristic mode for demo)")
        return True
    
    def predict_risk(
        self, 
        transaction_data: Dict[str, Any],
        graph_context: Optional[Dict[str, Any]] = None
    ) -> RiskSignal:
        """
        Predict risk for a transaction.
        
        Args:
            transaction_data: Transaction details
            graph_context: Optional graph neighborhood context
            
        Returns:
            RiskSignal with level, score, and reasons
        """
        risk_factors = {}
        risk_reasons = []
        
        # Extract features
        amount = transaction_data.get("amount", 0)
        vendor = transaction_data.get("vendor", transaction_data.get("vendor_id", ""))
        category = transaction_data.get("category", "")
        employee_id = transaction_data.get("employee_id", transaction_data.get("agent_id", ""))
        timestamp = transaction_data.get("timestamp", datetime.now().isoformat())
        
        # 1. Check vendor novelty
        vendor_risk = self._assess_vendor_risk(vendor, employee_id)
        if vendor_risk > 0:
            risk_factors[RiskFactor.NEW_VENDOR.value] = vendor_risk
            if vendor_risk > 0.5:
                risk_reasons.append(f"New/unknown vendor: {vendor}")
        
        # 2. Check amount anomaly
        amount_risk = self._assess_amount_risk(amount, employee_id)
        if amount_risk > 0:
            risk_factors[RiskFactor.AMOUNT_SPIKE.value] = amount_risk
            if amount_risk > 0.5:
                risk_reasons.append(f"Amount spike detected: ${amount:,.2f}")
        
        # 3. Check for large amounts
        large_risk = self._assess_large_amount_risk(amount)
        if large_risk > 0:
            risk_factors[RiskFactor.LARGE_AMOUNT.value] = large_risk
            if large_risk > 0.5:
                risk_reasons.append(f"Large transaction: ${amount:,.2f}")
        
        # 4. Check round amounts (fraud indicator)
        round_risk = self._assess_round_amount_risk(amount)
        if round_risk > 0:
            risk_factors[RiskFactor.ROUND_AMOUNT.value] = round_risk
            if round_risk > 0.3:
                risk_reasons.append(f"Suspiciously round amount: ${amount:,.2f}")
        
        # 5. Check category risk
        category_risk = self._assess_category_risk(category, employee_id)
        if category_risk > 0:
            risk_factors[RiskFactor.UNUSUAL_CATEGORY.value] = category_risk
            if category_risk > 0.5:
                risk_reasons.append(f"Unusual category: {category}")
        
        # 6. Check time of transaction
        time_risk = self._assess_time_risk(timestamp)
        if time_risk > 0:
            risk_factors[RiskFactor.OFF_HOURS.value] = time_risk
            if time_risk > 0.5:
                risk_reasons.append("Transaction outside business hours")
        
        # 7. Check velocity (transaction frequency)
        velocity_risk = self._assess_velocity_risk(employee_id)
        if velocity_risk > 0:
            risk_factors[RiskFactor.VELOCITY_SPIKE.value] = velocity_risk
            if velocity_risk > 0.5:
                risk_reasons.append("Unusual transaction velocity")
        
        # 8. Check for first-time employee
        first_time_risk = self._assess_first_time_risk(employee_id)
        if first_time_risk > 0:
            risk_factors[RiskFactor.FIRST_TRANSACTION.value] = first_time_risk
            if first_time_risk > 0.3:
                risk_reasons.append("First transaction from this user")
        
        # Calculate weighted risk score
        total_score = 0.0
        total_weight = 0.0
        
        for factor, factor_score in risk_factors.items():
            weight = self._factor_weights.get(factor, 0.1)
            total_score += factor_score * weight
            total_weight += weight
        
        # Normalize score
        if total_weight > 0:
            risk_score = min(1.0, total_score / total_weight)
        else:
            risk_score = 0.0
        
        # Boost score if multiple risk factors present
        if len(risk_factors) >= 3:
            risk_score = min(1.0, risk_score * 1.3)
        if len(risk_factors) >= 5:
            risk_score = min(1.0, risk_score * 1.5)
        
        # Determine risk level
        risk_level = self._determine_risk_level(risk_score)
        
        # Store transaction for future pattern detection
        self._store_transaction(transaction_data)
        
        return RiskSignal(
            risk_level=risk_level,
            risk_score=round(risk_score, 3),
            risk_reasons=risk_reasons,
            risk_factors=risk_factors
        )
    
    def _assess_vendor_risk(self, vendor: str, employee_id: str) -> float:
        """Assess risk based on vendor novelty and reputation."""
        if not vendor:
            return 0.3  # Unknown vendor is moderate risk
        
        vendor_lower = vendor.lower()
        
        # Check if trusted vendor
        for trusted in self._trusted_vendors:
            if trusted in vendor_lower:
                return 0.0
        
        # Check if employee has used this vendor before
        profile = self._entity_profiles.get(employee_id)
        if profile and vendor_lower in [v.lower() for v in profile.typical_vendors]:
            return 0.1  # Known vendor for this employee
        
        # New vendor for this employee
        return 0.6
    
    def _assess_amount_risk(self, amount: float, employee_id: str) -> float:
        """Assess risk based on amount deviation from typical."""
        profile = self._entity_profiles.get(employee_id)
        
        if not profile or profile.total_transactions < 3:
            # Not enough history, moderate baseline risk
            if amount > 5000:
                return 0.4
            return 0.2
        
        avg = profile.average_amount
        if avg == 0:
            return 0.0
        
        # Calculate deviation
        deviation = amount / avg
        
        if deviation > 5:
            return 0.9  # 5x typical amount
        elif deviation > 3:
            return 0.7  # 3x typical amount
        elif deviation > 2:
            return 0.4  # 2x typical amount
        elif deviation > 1.5:
            return 0.2  # 1.5x typical amount
        
        return 0.0
    
    def _assess_large_amount_risk(self, amount: float) -> float:
        """Assess risk based on absolute amount."""
        if amount >= 50000:
            return 0.9
        elif amount >= 25000:
            return 0.7
        elif amount >= 10000:
            return 0.5
        elif amount >= 5000:
            return 0.3
        elif amount >= 1000:
            return 0.1
        return 0.0
    
    def _assess_round_amount_risk(self, amount: float) -> float:
        """Assess risk for suspiciously round amounts."""
        for round_amount in self._suspicious_patterns["round_amounts"]:
            if amount == round_amount:
                return 0.5
        
        # Check if amount is very round (divisible by 1000 with no cents)
        if amount >= 1000 and amount % 1000 == 0:
            return 0.3
        
        return 0.0
    
    def _assess_category_risk(self, category: str, employee_id: str) -> float:
        """Assess risk based on category."""
        if not category:
            return 0.2
        
        category_lower = category.lower()
        
        # High-risk categories
        if category_lower in self._suspicious_patterns["high_risk_categories"]:
            return 0.5
        
        # Check if employee typically uses this category
        profile = self._entity_profiles.get(employee_id)
        if profile and profile.typical_categories:
            if category_lower not in [c.lower() for c in profile.typical_categories]:
                return 0.4  # Unusual category for this employee
        
        return 0.0
    
    def _assess_time_risk(self, timestamp: str) -> float:
        """Assess risk based on time of transaction."""
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            
            hour = dt.hour
            day = dt.weekday()
            
            # Weekend transactions
            if day >= 5:
                return 0.4
            
            # Off-hours transactions
            if hour in self._suspicious_patterns["off_hours"]:
                return 0.5
            
            return 0.0
        except:
            return 0.1  # Unable to parse, slight risk
    
    def _assess_velocity_risk(self, employee_id: str) -> float:
        """Assess risk based on transaction velocity."""
        # Count recent transactions from this employee
        now = datetime.now()
        cutoff = now - timedelta(hours=1)
        
        recent_count = 0
        for tx in self._transaction_history[-100:]:  # Check last 100
            tx_employee = tx.get("employee_id", tx.get("agent_id", ""))
            if tx_employee == employee_id:
                try:
                    tx_time = datetime.fromisoformat(tx.get("timestamp", ""))
                    if tx_time > cutoff:
                        recent_count += 1
                except:
                    pass
        
        if recent_count >= 10:
            return 0.9  # Very high velocity
        elif recent_count >= 5:
            return 0.6
        elif recent_count >= 3:
            return 0.3
        
        return 0.0
    
    def _assess_first_time_risk(self, employee_id: str) -> float:
        """Assess risk for first-time users."""
        if employee_id not in self._entity_profiles:
            return 0.4  # First transaction, moderate risk
        
        profile = self._entity_profiles[employee_id]
        if profile.total_transactions < 3:
            return 0.2  # Few transactions, slight risk
        
        return 0.0
    
    def _store_transaction(self, transaction: Dict[str, Any]):
        """Store transaction and update entity profile."""
        self._transaction_history.append(transaction)
        
        # Update entity profile
        employee_id = transaction.get("employee_id", transaction.get("agent_id", ""))
        if employee_id:
            if employee_id not in self._entity_profiles:
                self._entity_profiles[employee_id] = EntityProfile(
                    entity_id=employee_id,
                    entity_type="employee"
                )
            
            profile = self._entity_profiles[employee_id]
            amount = transaction.get("amount", 0)
            
            # Update stats
            total = profile.total_amount + amount
            count = profile.total_transactions + 1
            profile.total_amount = total
            profile.total_transactions = count
            profile.average_amount = total / count
            
            # Update typical vendors
            vendor = transaction.get("vendor", transaction.get("vendor_id", ""))
            if vendor and vendor not in profile.typical_vendors:
                profile.typical_vendors.append(vendor)
            
            # Update typical categories
            category = transaction.get("category", "")
            if category and category not in profile.typical_categories:
                profile.typical_categories.append(category)
            
            # Update timestamps
            timestamp = transaction.get("timestamp", datetime.now().isoformat())
            if not profile.first_transaction_date:
                profile.first_transaction_date = timestamp
            profile.last_transaction_date = timestamp
    
    def analyze_patterns(
        self, 
        entity_id: str, 
        entity_type: str
    ) -> Dict[str, Any]:
        """Analyze historical patterns for an entity."""
        profile = self._entity_profiles.get(entity_id)
        
        if not profile:
            return {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "has_history": False,
                "pattern_analysis": "No transaction history available"
            }
        
        # Analyze patterns
        analysis = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "has_history": True,
            "total_transactions": profile.total_transactions,
            "total_amount": profile.total_amount,
            "average_amount": profile.average_amount,
            "typical_vendors": profile.typical_vendors[:5],
            "typical_categories": profile.typical_categories[:5],
            "first_seen": profile.first_transaction_date,
            "last_seen": profile.last_transaction_date
        }
        
        # Risk assessment
        if profile.total_transactions < 5:
            analysis["profile_maturity"] = "new"
            analysis["baseline_risk"] = "moderate"
        elif profile.total_transactions < 20:
            analysis["profile_maturity"] = "developing"
            analysis["baseline_risk"] = "low"
        else:
            analysis["profile_maturity"] = "established"
            analysis["baseline_risk"] = "very_low"
        
        return analysis
    
    def detect_anomalies(
        self, 
        transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect anomalous transactions in a batch."""
        anomalies = []
        
        for tx in transactions:
            signal = self.predict_risk(tx)
            
            if signal.risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]:
                anomalies.append({
                    "transaction": tx,
                    "risk_signal": signal.to_dict(),
                    "is_anomaly": True
                })
        
        return anomalies
    
    def _determine_risk_level(self, score: float) -> RiskLevel:
        """Convert risk score to risk level."""
        if score >= self._thresholds["high"]:
            return RiskLevel.HIGH
        elif score >= self._thresholds["medium"]:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
    
    def _extract_risk_reasons(
        self, 
        transaction: Dict[str, Any],
        prediction_details: Dict[str, Any]
    ) -> List[str]:
        """Extract human-readable risk reasons."""
        reasons = []
        
        for factor, score in prediction_details.items():
            if score > 0.3:
                # Convert factor enum to readable string
                readable = factor.replace("_", " ").title()
                reasons.append(f"{readable} (score: {score:.2f})")
        
        return reasons
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        return {
            "model_type": "heuristic_gnn_simulation",
            "description": "Rule-based risk model simulating GNN behavior",
            "thresholds": self._thresholds,
            "factor_weights": self._factor_weights,
            "entity_profiles_count": len(self._entity_profiles),
            "transaction_history_size": len(self._transaction_history),
            "trusted_vendors_count": len(self._trusted_vendors)
        }
    
    def reset(self):
        """Reset the model state."""
        self._entity_profiles.clear()
        self._transaction_history.clear()
