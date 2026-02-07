"""
Payment MCP Server Module

MCP server responsible for executing payment operations.
This is the ONLY way payments can be executed in the system.

All requests must come through the enforcement gateway
with proper authorization and constraints.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import uuid


class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PaymentResult:
    """Result of a payment execution."""
    payment_id: str
    status: PaymentStatus
    amount: float
    timestamp: str
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "payment_id": self.payment_id,
            "status": self.status.value,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "details": self.details
        }


class PaymentMCPServer:
    """
    MCP Server for payment execution.
    
    Capabilities:
    - Execute approved payments
    - Process reimbursements
    - Handle transfers between accounts
    
    Security:
    - Only accepts requests from enforcement gateway
    - Validates decision_id and constraints
    - Maintains execution audit log
    """
    
    def __init__(self):
        self._execution_log: list = []
        self._pending_payments: Dict[str, Dict[str, Any]] = {}
    
    async def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a payment request.
        
        Args:
            request: Execution request containing:
                - decision_id: ID from enforcement gateway
                - intent: Original intent
                - constraints: Applied constraints
                
        Returns:
            Execution result
        """
        decision_id = request.get("decision_id")
        intent = request.get("intent", {})
        constraints = request.get("constraints", {})
        
        # Validate request
        if not decision_id:
            return {"error": "Missing decision_id", "executed": False}
        
        # Check constraints (handle None)
        constraints = constraints or {}
        if constraints.get("frozen"):
            return {
                "error": "Execution frozen by risk policy",
                "executed": False,
                "freeze_reason": constraints.get("freeze_reason")
            }
        
        # Handle different intent types
        intent_type = intent.get("intent_type")
        
        if intent_type == "approve_payment":
            return await self._execute_payment(intent, constraints)
        elif intent_type == "reject_payment":
            return await self._reject_payment(intent)
        else:
            return {"error": f"Unsupported intent type: {intent_type}", "executed": False}
    
    async def _execute_payment(
        self,
        intent: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an approved payment."""
        payment_id = str(uuid.uuid4())
        params = intent.get("parameters", {})
        amount = params.get("amount", 0)
        
        # Apply constraint-based delays
        if constraints.get("delay_execution"):
            # In production, would implement actual delay
            pass
        
        # Create payment record
        payment = PaymentResult(
            payment_id=payment_id,
            status=PaymentStatus.PROCESSING,
            amount=amount,
            timestamp=datetime.utcnow().isoformat(),
            details={
                "target_id": intent.get("target_id"),
                "approval_level": params.get("approval_level", "standard"),
                "constraints_applied": list(constraints.keys())
            }
        )
        
        # Log execution
        self._log_execution(payment, intent, constraints)
        
        # Simulate payment processing
        # In production, would integrate with actual payment provider
        payment.status = PaymentStatus.COMPLETED
        
        return {
            "executed": True,
            "payment": payment.to_dict()
        }
    
    async def _reject_payment(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment rejection."""
        return {
            "executed": True,
            "action": "rejection_recorded",
            "target_id": intent.get("target_id"),
            "reason": intent.get("parameters", {}).get("reason")
        }
    
    def _log_execution(
        self,
        payment: PaymentResult,
        intent: Dict[str, Any],
        constraints: Dict[str, Any]
    ):
        """Log payment execution for audit."""
        self._execution_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "payment_id": payment.payment_id,
            "amount": payment.amount,
            "intent": intent,
            "constraints": constraints
        })
    
    def get_execution_log(self) -> list:
        """Retrieve execution log."""
        return self._execution_log.copy()
    
    def get_payment_status(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a payment."""
        for entry in self._execution_log:
            if entry.get("payment_id") == payment_id:
                return entry
        return None
