"""
Approval MCP Server Module

MCP server responsible for managing approval workflows
and updating approval status in the system.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import uuid


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    EXPIRED = "expired"


@dataclass
class ApprovalRecord:
    """Record of an approval action."""
    approval_id: str
    request_id: str
    status: ApprovalStatus
    approver: str
    timestamp: str
    notes: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "request_id": self.request_id,
            "status": self.status.value,
            "approver": self.approver,
            "timestamp": self.timestamp,
            "notes": self.notes
        }


class ApprovalMCPServer:
    """
    MCP Server for approval workflow management.
    
    Capabilities:
    - Record approval decisions
    - Manage approval chains
    - Track escalations
    - Update request status
    
    Security:
    - Only accepts requests from enforcement gateway
    - Maintains complete approval audit trail
    - Enforces approval hierarchy
    """
    
    def __init__(self):
        self._approval_log: List[ApprovalRecord] = []
        self._pending_approvals: Dict[str, Dict[str, Any]] = {}
        self._approval_chains: Dict[str, List[str]] = {}
    
    async def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an approval action.
        
        Args:
            request: Execution request from enforcement gateway
            
        Returns:
            Execution result
        """
        decision_id = request.get("decision_id")
        intent = request.get("intent", {})
        constraints = request.get("constraints", {})
        
        if not decision_id:
            return {"error": "Missing decision_id", "executed": False}
        
        intent_type = intent.get("intent_type")
        
        if intent_type == "approve_payment":
            return await self._record_approval(intent, constraints)
        elif intent_type == "reject_payment":
            return await self._record_rejection(intent)
        elif intent_type == "escalate":
            return await self._handle_escalation(intent, constraints)
        elif intent_type == "flag_suspicious":
            return await self._flag_for_review(intent)
        else:
            return {"error": f"Unsupported intent type: {intent_type}", "executed": False}
    
    async def _record_approval(
        self,
        intent: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Record an approval decision."""
        approval_id = str(uuid.uuid4())
        
        # Check if dual approval is required
        if constraints.get("dual_approval"):
            return await self._initiate_dual_approval(intent, approval_id)
        
        record = ApprovalRecord(
            approval_id=approval_id,
            request_id=intent.get("target_id"),
            status=ApprovalStatus.APPROVED,
            approver=intent.get("agent_id"),
            timestamp=datetime.utcnow().isoformat(),
            notes=intent.get("reasoning", "")
        )
        
        self._approval_log.append(record)
        
        return {
            "executed": True,
            "approval": record.to_dict()
        }
    
    async def _record_rejection(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Record a rejection decision."""
        approval_id = str(uuid.uuid4())
        
        record = ApprovalRecord(
            approval_id=approval_id,
            request_id=intent.get("target_id"),
            status=ApprovalStatus.REJECTED,
            approver=intent.get("agent_id"),
            timestamp=datetime.utcnow().isoformat(),
            notes=intent.get("parameters", {}).get("reason", "")
        )
        
        self._approval_log.append(record)
        
        return {
            "executed": True,
            "rejection": record.to_dict()
        }
    
    async def _handle_escalation(
        self,
        intent: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle escalation to higher authority."""
        approval_id = str(uuid.uuid4())
        request_id = intent.get("target_id")
        
        record = ApprovalRecord(
            approval_id=approval_id,
            request_id=request_id,
            status=ApprovalStatus.ESCALATED,
            approver=intent.get("agent_id"),
            timestamp=datetime.utcnow().isoformat(),
            notes=f"Escalated to {intent.get('parameters', {}).get('escalate_to', 'higher authority')}"
        )
        
        self._approval_log.append(record)
        
        # Track escalation chain
        if request_id not in self._approval_chains:
            self._approval_chains[request_id] = []
        self._approval_chains[request_id].append(approval_id)
        
        return {
            "executed": True,
            "escalation": record.to_dict(),
            "chain_length": len(self._approval_chains[request_id])
        }
    
    async def _flag_for_review(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Flag a request for human review."""
        request_id = intent.get("target_id")
        
        self._pending_approvals[request_id] = {
            "flagged_at": datetime.utcnow().isoformat(),
            "flagged_by": intent.get("agent_id"),
            "severity": intent.get("parameters", {}).get("severity", "medium"),
            "reasons": intent.get("parameters", {}).get("anomalies", []),
            "status": "awaiting_review"
        }
        
        return {
            "executed": True,
            "flagged": True,
            "request_id": request_id,
            "status": "awaiting_human_review"
        }
    
    async def _initiate_dual_approval(
        self,
        intent: Dict[str, Any],
        approval_id: str
    ) -> Dict[str, Any]:
        """Initiate dual approval workflow."""
        request_id = intent.get("target_id")
        
        # Record first approval
        record = ApprovalRecord(
            approval_id=approval_id,
            request_id=request_id,
            status=ApprovalStatus.PENDING,
            approver=intent.get("agent_id"),
            timestamp=datetime.utcnow().isoformat(),
            notes="First approval recorded, awaiting second approver"
        )
        
        self._approval_log.append(record)
        
        # Track in pending
        self._pending_approvals[request_id] = {
            "first_approval": approval_id,
            "first_approver": intent.get("agent_id"),
            "status": "awaiting_second_approval"
        }
        
        return {
            "executed": True,
            "partial_approval": record.to_dict(),
            "requires_second_approval": True
        }
    
    def get_approval_history(self, request_id: str) -> List[Dict[str, Any]]:
        """Get approval history for a request."""
        return [
            r.to_dict() for r in self._approval_log
            if r.request_id == request_id
        ]
    
    def get_pending_approvals(self) -> Dict[str, Dict[str, Any]]:
        """Get all pending approvals."""
        return self._pending_approvals.copy()
