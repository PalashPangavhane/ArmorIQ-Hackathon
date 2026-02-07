"""
Enforcement Gateway Module

Central gateway that enforces all policy decisions before
forwarding approved intents to MCP execution servers.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid

from .intent_validator import IntentValidator, ValidationResult
from .policy_engine import PolicyEngine, PolicyResult
from .risk_policy_integrator import RiskPolicyIntegrator


@dataclass
class EnforcementDecision:
    """Final enforcement decision."""
    decision_id: str
    timestamp: str
    intent_id: str
    allowed: bool
    constraints: Dict[str, Any]
    reason: str
    audit_trail: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "timestamp": self.timestamp,
            "intent_id": self.intent_id,
            "allowed": self.allowed,
            "constraints": self.constraints,
            "reason": self.reason,
            "audit_trail": self.audit_trail
        }


class EnforcementGateway:
    """
    Central enforcement gateway.
    
    All intents must pass through this gateway before execution.
    
    Flow:
    1. Validate intent structure and authorization
    2. Evaluate against policy rules
    3. Integrate risk signals
    4. Make final allow/deny decision
    5. Log for audit
    6. Forward to MCP server if allowed
    """
    
    def __init__(
        self,
        intent_validator: IntentValidator,
        policy_engine: PolicyEngine,
        risk_integrator: RiskPolicyIntegrator
    ):
        self.intent_validator = intent_validator
        self.policy_engine = policy_engine
        self.risk_integrator = risk_integrator
        self._mcp_client = None
        self._audit_log: list = []
    
    def set_mcp_client(self, mcp_client):
        """Set the MCP client for execution forwarding."""
        self._mcp_client = mcp_client
    
    async def process_intent(
        self,
        intent: Dict[str, Any],
        risk_signal: Optional[Dict[str, Any]] = None
    ) -> EnforcementDecision:
        """
        Process an intent through the full enforcement pipeline.
        
        Args:
            intent: Agent intent to process
            risk_signal: Optional risk signal from GNN
            
        Returns:
            EnforcementDecision with final result
        """
        decision_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        intent_id = intent.get("target_id", "unknown")
        
        audit_trail = {
            "intent": intent,
            "risk_signal": risk_signal,
            "validation": None,
            "policy_evaluation": None,
            "risk_integration": None
        }
        
        # Step 1: Validate intent
        validation = self.intent_validator.validate(intent)
        audit_trail["validation"] = {
            "result": validation.result.value,
            "errors": validation.errors,
            "warnings": validation.warnings
        }
        
        if not validation.is_valid():
            return self._create_denial(
                decision_id=decision_id,
                timestamp=timestamp,
                intent_id=intent_id,
                reason=f"Validation failed: {', '.join(validation.errors)}",
                audit_trail=audit_trail
            )
        
        # Step 2: Evaluate policy (with risk if available)
        if risk_signal:
            evaluation = self.risk_integrator.evaluate_with_risk(intent, risk_signal)
        else:
            policy_eval = self.policy_engine.evaluate(intent)
            evaluation = {
                "result": policy_eval.result.value,
                "policy_id": policy_eval.policy_id,
                "reason": policy_eval.reason,
                "constraints": policy_eval.constraints,
                "allowed": policy_eval.result == PolicyResult.ALLOW
            }
        
        audit_trail["policy_evaluation"] = evaluation
        
        # Step 3: Make final decision
        if not evaluation.get("allowed", False):
            return self._create_denial(
                decision_id=decision_id,
                timestamp=timestamp,
                intent_id=intent_id,
                reason=evaluation.get("reason", "Policy denied"),
                audit_trail=audit_trail
            )
        
        # Step 4: Create approval with constraints
        decision = EnforcementDecision(
            decision_id=decision_id,
            timestamp=timestamp,
            intent_id=intent_id,
            allowed=True,
            constraints=evaluation.get("constraints", {}),
            reason="All checks passed",
            audit_trail=audit_trail
        )
        
        # Log decision
        self._log_decision(decision)
        
        return decision
    
    async def execute_if_allowed(
        self,
        decision: EnforcementDecision,
        intent: Dict[str, Any],
        agent_id: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Execute intent via MCP server if allowed.
        
        CRITICAL: This is where agent intents become real actions.
        The decision MUST be registered with the MCP client before execution.
        
        Args:
            decision: Enforcement decision
            intent: Original intent
            agent_id: ID of requesting agent
            
        Returns:
            Execution result
        """
        if not decision.allowed:
            print(f"\n🚫 EXECUTION BLOCKED by Enforcement Gateway")
            print(f"   Reason: {decision.reason}")
            return {
                "executed": False,
                "blocked": True,
                "reason": decision.reason
            }
        
        if self._mcp_client is None:
            return {
                "executed": False,
                "reason": "MCP client not configured"
            }
        
        # CRITICAL: Register the approved decision with MCP client
        # This is what allows the MCP client to accept the execution
        self._mcp_client.register_approved_decision(
            decision_id=decision.decision_id,
            decision_data={
                "allowed": decision.allowed,
                "reason": decision.reason,
                "constraints": decision.constraints,
                "intent_id": decision.intent_id
            }
        )
        
        # Forward to MCP server with constraints
        execution_request = {
            "decision_id": decision.decision_id,
            "intent": intent,
            "constraints": decision.constraints,
            "agent_id": agent_id
        }
        
        result = await self._mcp_client.execute(execution_request)
        
        # Log execution
        self._log_execution(decision.decision_id, result)
        
        return result
    
    def _create_denial(
        self,
        decision_id: str,
        timestamp: str,
        intent_id: str,
        reason: str,
        audit_trail: Dict[str, Any]
    ) -> EnforcementDecision:
        """Create a denial decision."""
        decision = EnforcementDecision(
            decision_id=decision_id,
            timestamp=timestamp,
            intent_id=intent_id,
            allowed=False,
            constraints={},
            reason=reason,
            audit_trail=audit_trail
        )
        self._log_decision(decision)
        return decision
    
    def _log_decision(self, decision: EnforcementDecision):
        """Log decision for audit."""
        self._audit_log.append({
            "type": "decision",
            "data": decision.to_dict()
        })
    
    def _log_execution(self, decision_id: str, result: Dict[str, Any]):
        """Log execution for audit."""
        self._audit_log.append({
            "type": "execution",
            "decision_id": decision_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def get_audit_log(self) -> list:
        """Retrieve audit log."""
        return self._audit_log.copy()
