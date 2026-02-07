"""
MCP Client Module

Client for communicating with MCP servers.
Used by the enforcement gateway to forward approved intents.

CRITICAL SECURITY PRINCIPLE:
This is the ONLY pathway for agents to affect the real world.
All requests MUST have a valid decision_id from the Enforcement Gateway.
Requests without valid approval are BLOCKED.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from .payment_server import PaymentMCPServer
from .approval_server import ApprovalMCPServer
from .account_server import AccountMCPServer


class MCPServerType(Enum):
    PAYMENT = "payment"
    APPROVAL = "approval"
    ACCOUNT = "account"


@dataclass
class ExecutionRecord:
    """Complete audit record of an execution attempt."""
    record_id: str
    decision_id: str
    agent_id: str
    intent_type: str
    timestamp: str
    was_blocked: bool
    block_reason: Optional[str] = None
    success: bool = False
    execution_result: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "decision_id": self.decision_id,
            "agent_id": self.agent_id,
            "intent_type": self.intent_type,
            "timestamp": self.timestamp,
            "was_blocked": self.was_blocked,
            "block_reason": self.block_reason,
            "success": self.success,
            "execution_result": self.execution_result
        }


class MCPClient:
    """
    Client for MCP server communication.
    
    ARCHITECTURE:
    ┌─────────────────────────────────────────────────────────────┐
    │                     AGENT (FREE REASONING)                  │
    │  - Analyzes requests using RAG/GNN                          │
    │  - Reasons about best action                                │
    │  - Proposes intents (NO DIRECT EXECUTION)                   │
    └─────────────────────────────────────────────────────────────┘
                                │
                                ▼ Intent
    ┌─────────────────────────────────────────────────────────────┐
    │                 ENFORCEMENT GATEWAY                         │
    │  - Validates intent structure                               │
    │  - Checks against user-defined policy rules                 │
    │  - BLOCKS if rules violated                                 │
    │  - Issues decision_id if approved                           │
    └─────────────────────────────────────────────────────────────┘
                                │
                                ▼ Approved Request + Decision ID
    ┌─────────────────────────────────────────────────────────────┐
    │                     MCP CLIENT (YOU ARE HERE)               │
    │  - VERIFIES decision_id is valid                            │
    │  - Routes to appropriate MCP server                         │
    │  - Records ALL attempts for audit trail                     │
    │  - BLOCKS requests without valid approval                   │
    └─────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              ┌─────────┐ ┌─────────┐ ┌─────────┐
              │ Payment │ │Approval │ │ Account │
              │  MCP    │ │   MCP   │ │   MCP   │
              └─────────┘ └─────────┘ └─────────┘
    
    Routes execution requests to appropriate MCP servers.
    Provides unified interface for the enforcement gateway.
    """
    
    def __init__(self):
        self._servers: Dict[MCPServerType, Any] = {}
        self._valid_decisions: Dict[str, Dict[str, Any]] = {}  # Approved decisions
        self._execution_log: List[ExecutionRecord] = []  # Audit trail
        self._initialize_servers()
    
    def _initialize_servers(self):
        """Initialize MCP servers."""
        self._servers[MCPServerType.PAYMENT] = PaymentMCPServer()
        self._servers[MCPServerType.APPROVAL] = ApprovalMCPServer()
        self._servers[MCPServerType.ACCOUNT] = AccountMCPServer()
        print("[MCP Client] All MCP servers initialized")
    
    def register_approved_decision(self, decision_id: str, decision_data: Dict[str, Any]):
        """
        Register an approved decision from the Enforcement Gateway.
        
        This is the ONLY way to authorize execution. The gateway must
        explicitly register decisions before they can be executed.
        
        Args:
            decision_id: Unique decision identifier
            decision_data: Decision details including allowed status
        """
        self._valid_decisions[decision_id] = {
            **decision_data,
            "registered_at": datetime.utcnow().isoformat(),
            "used": False
        }
        print(f"[MCP Client] Decision registered: {decision_id[:8]}... allowed={decision_data.get('allowed', False)}")
    
    async def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a request by routing to appropriate MCP server.
        
        SECURITY: Validates decision_id before ANY execution.
        
        Args:
            request: Execution request containing:
                - decision_id: ID from enforcement gateway (REQUIRED)
                - intent: Original intent
                - constraints: Applied constraints
                - agent_id: Requesting agent
                
        Returns:
            Combined execution results
        """
        decision_id = request.get("decision_id")
        intent = request.get("intent", {})
        agent_id = request.get("agent_id", "unknown")
        intent_type = intent.get("intent_type", "unknown")
        timestamp = datetime.utcnow().isoformat()
        
        # ================================================================
        # CRITICAL SECURITY CHECK: Verify decision was approved by gateway
        # ================================================================
        if not decision_id:
            return self._block_execution(
                decision_id="MISSING",
                agent_id=agent_id,
                intent_type=intent_type,
                reason="BLOCKED: No decision_id provided. All actions MUST be approved by Enforcement Gateway."
            )
        
        if decision_id not in self._valid_decisions:
            return self._block_execution(
                decision_id=decision_id,
                agent_id=agent_id,
                intent_type=intent_type,
                reason="BLOCKED: Invalid decision_id. This decision was not approved by the Enforcement Gateway."
            )
        
        decision_data = self._valid_decisions[decision_id]
        
        # Check if decision was already used (one-time use)
        if decision_data.get("used", False):
            return self._block_execution(
                decision_id=decision_id,
                agent_id=agent_id,
                intent_type=intent_type,
                reason="BLOCKED: Decision already executed. Each approval can only be used once."
            )
        
        # Check if decision allows execution
        if not decision_data.get("allowed", False):
            return self._block_execution(
                decision_id=decision_id,
                agent_id=agent_id,
                intent_type=intent_type,
                reason=f"BLOCKED: Decision explicitly denied. Reason: {decision_data.get('reason', 'Policy violation')}"
            )
        
        # Mark decision as used
        self._valid_decisions[decision_id]["used"] = True
        
        # ================================================================
        # Decision approved - proceed with execution
        # ================================================================
        
        # Route based on intent type
        server = self._get_server_for_intent(intent_type)
        
        if server is None:
            result = {
                "error": f"No server available for intent type: {intent_type}",
                "executed": False
            }
            self._log_execution(decision_id, agent_id, intent_type, False, result)
            return result
        
        # Execute on appropriate server
        result = await server.execute(request)
        
        # For payment approvals, also update account
        if intent_type == "approve_payment" and result.get("executed"):
            account_result = await self._servers[MCPServerType.ACCOUNT].execute(request)
            result["account_update"] = account_result
        
        # Always record approval status
        if intent_type in ["approve_payment", "reject_payment", "escalate", "flag_suspicious"]:
            approval_result = await self._servers[MCPServerType.APPROVAL].execute(request)
            result["approval_record"] = approval_result
        
        # Log successful execution
        self._log_execution(
            decision_id=decision_id,
            agent_id=agent_id,
            intent_type=intent_type,
            success=result.get("executed", False),
            result=result
        )
        
        return result
    
    def _block_execution(
        self,
        decision_id: str,
        agent_id: str,
        intent_type: str,
        reason: str
    ) -> Dict[str, Any]:
        """Block an execution attempt and log it."""
        record = ExecutionRecord(
            record_id=str(uuid.uuid4()),
            decision_id=decision_id,
            agent_id=agent_id,
            intent_type=intent_type,
            timestamp=datetime.utcnow().isoformat(),
            was_blocked=True,
            block_reason=reason,
            success=False
        )
        self._execution_log.append(record)
        
        print(f"\n{'='*60}")
        print(f"🚫 EXECUTION BLOCKED")
        print(f"{'='*60}")
        print(f"Agent: {agent_id}")
        print(f"Intent: {intent_type}")
        print(f"Reason: {reason}")
        print(f"{'='*60}\n")
        
        return {
            "error": reason,
            "executed": False,
            "blocked": True,
            "record_id": record.record_id
        }
    
    def _log_execution(
        self,
        decision_id: str,
        agent_id: str,
        intent_type: str,
        success: bool,
        result: Dict[str, Any]
    ):
        """Log a successful execution attempt."""
        record = ExecutionRecord(
            record_id=str(uuid.uuid4()),
            decision_id=decision_id,
            agent_id=agent_id,
            intent_type=intent_type,
            timestamp=datetime.utcnow().isoformat(),
            was_blocked=False,
            success=success,
            execution_result=result
        )
        self._execution_log.append(record)
    
    def _get_server_for_intent(self, intent_type: str) -> Optional[Any]:
        """Get the appropriate MCP server for an intent type."""
        if intent_type in ["approve_payment", "reject_payment"]:
            return self._servers[MCPServerType.PAYMENT]
        elif intent_type in ["escalate", "flag_suspicious"]:
            return self._servers[MCPServerType.APPROVAL]
        return None
    
    # ================================================================
    # Audit Trail Methods
    # ================================================================
    
    def get_execution_log(self) -> List[Dict[str, Any]]:
        """Get the complete execution log for audit trail."""
        return [r.to_dict() for r in self._execution_log]
    
    def get_blocked_attempts(self) -> List[Dict[str, Any]]:
        """Get all blocked execution attempts."""
        return [r.to_dict() for r in self._execution_log if r.was_blocked]
    
    def get_successful_executions(self) -> List[Dict[str, Any]]:
        """Get all successful executions."""
        return [r.to_dict() for r in self._execution_log if r.success and not r.was_blocked]
    
    def print_audit_trail(self):
        """Print formatted audit trail."""
        print("\n" + "="*70)
        print("📋 AUDIT TRAIL - All Execution Attempts")
        print("="*70)
        
        for i, record in enumerate(self._execution_log, 1):
            status = "🚫 BLOCKED" if record.was_blocked else ("✅ SUCCESS" if record.success else "❌ FAILED")
            print(f"\n{i}. {status}")
            print(f"   Decision ID: {record.decision_id[:8]}..." if len(record.decision_id) > 8 else f"   Decision ID: {record.decision_id}")
            print(f"   Agent: {record.agent_id}")
            print(f"   Intent: {record.intent_type}")
            print(f"   Time: {record.timestamp}")
            if record.was_blocked:
                print(f"   Block Reason: {record.block_reason}")
        
        print("\n" + "="*70)
        total = len(self._execution_log)
        blocked = len([r for r in self._execution_log if r.was_blocked])
        success = len([r for r in self._execution_log if r.success])
        print(f"Summary: {total} total | {blocked} blocked | {success} successful")
        print("="*70 + "\n")
    
    def get_payment_server(self) -> PaymentMCPServer:
        """Get the payment MCP server."""
        return self._servers[MCPServerType.PAYMENT]
    
    def get_approval_server(self) -> ApprovalMCPServer:
        """Get the approval MCP server."""
        return self._servers[MCPServerType.APPROVAL]
    
    def get_account_server(self) -> AccountMCPServer:
        """Get the account MCP server."""
        return self._servers[MCPServerType.ACCOUNT]
