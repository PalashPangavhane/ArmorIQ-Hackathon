"""
Risk Policy Integrator Module

Integrates GNN risk signals with policy evaluation.
Applies risk-based constraints to policy decisions.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from .policy_engine import PolicyEngine, PolicyResult, PolicyEvaluation


class RiskAction(Enum):
    """Actions based on risk level."""
    PROCEED = "proceed"
    ADD_CONSTRAINTS = "add_constraints"
    REQUIRE_APPROVAL = "require_approval"
    FREEZE = "freeze"


@dataclass
class RiskConstraint:
    """Constraint applied based on risk assessment."""
    action: RiskAction
    constraints: Dict[str, Any]
    reason: str


class RiskPolicyIntegrator:
    """
    Integrates risk signals with policy decisions.
    
    Responsibilities:
    - Receive risk signals from GNN
    - Modify policy constraints based on risk
    - Implement graceful degradation under risk
    - Freeze execution under high uncertainty
    """
    
    # Risk thresholds for action determination
    THRESHOLDS = {
        "proceed": 0.3,
        "add_constraints": 0.5,
        "require_approval": 0.7,
        "freeze": 0.9
    }
    
    def __init__(self, policy_engine: PolicyEngine):
        self.policy_engine = policy_engine
    
    def evaluate_with_risk(
        self,
        intent: Dict[str, Any],
        risk_signal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate intent with risk signal integration.
        
        Args:
            intent: Agent intent to evaluate
            risk_signal: Risk signal from GNN
            
        Returns:
            Combined evaluation with risk-adjusted constraints
        """
        # First, get base policy evaluation
        policy_eval = self.policy_engine.evaluate(intent)
        
        # Determine risk-based constraint
        risk_constraint = self._determine_risk_constraint(risk_signal)
        
        # Combine policy and risk evaluations
        combined = self._combine_evaluations(policy_eval, risk_constraint)
        
        return combined
    
    def _determine_risk_constraint(
        self, 
        risk_signal: Dict[str, Any]
    ) -> RiskConstraint:
        """Determine constraint based on risk signal."""
        risk_score = risk_signal.get("risk_score", 0)
        risk_level = risk_signal.get("risk_level", "LOW")
        risk_reasons = risk_signal.get("risk_reasons", [])
        
        # Determine action based on score
        if risk_score >= self.THRESHOLDS["freeze"]:
            return RiskConstraint(
                action=RiskAction.FREEZE,
                constraints={"frozen": True, "requires_manual_review": True},
                reason=f"Risk score {risk_score} exceeds freeze threshold"
            )
        
        if risk_score >= self.THRESHOLDS["require_approval"]:
            return RiskConstraint(
                action=RiskAction.REQUIRE_APPROVAL,
                constraints={
                    "requires_human_approval": True,
                    "approval_level": "manager"
                },
                reason=f"High risk ({risk_level}): {', '.join(risk_reasons)}"
            )
        
        if risk_score >= self.THRESHOLDS["add_constraints"]:
            return RiskConstraint(
                action=RiskAction.ADD_CONSTRAINTS,
                constraints={
                    "enhanced_logging": True,
                    "notification_required": True,
                    "delay_execution": 300  # 5 minute delay
                },
                reason=f"Medium risk detected: {', '.join(risk_reasons)}"
            )
        
        return RiskConstraint(
            action=RiskAction.PROCEED,
            constraints={},
            reason="Risk within acceptable levels"
        )
    
    def _combine_evaluations(
        self,
        policy_eval: PolicyEvaluation,
        risk_constraint: RiskConstraint
    ) -> Dict[str, Any]:
        """Combine policy evaluation with risk constraint."""
        # Risk can only make things more restrictive, not less
        final_result = policy_eval.result
        final_constraints = policy_eval.constraints or {}
        
        # Apply risk-based modifications
        if risk_constraint.action == RiskAction.FREEZE:
            final_result = PolicyResult.DENY
            final_constraints["frozen"] = True
            final_constraints["freeze_reason"] = risk_constraint.reason
        
        elif risk_constraint.action == RiskAction.REQUIRE_APPROVAL:
            if final_result == PolicyResult.ALLOW:
                final_result = PolicyResult.REQUIRE_CONSTRAINT
            final_constraints.update(risk_constraint.constraints)
        
        elif risk_constraint.action == RiskAction.ADD_CONSTRAINTS:
            final_constraints.update(risk_constraint.constraints)
        
        return {
            "result": final_result.value,
            "policy_id": policy_eval.policy_id,
            "policy_reason": policy_eval.reason,
            "risk_action": risk_constraint.action.value,
            "risk_reason": risk_constraint.reason,
            "constraints": final_constraints,
            "allowed": final_result == PolicyResult.ALLOW
        }
    
    def apply_graceful_degradation(
        self,
        intent: Dict[str, Any],
        risk_score: float
    ) -> Dict[str, Any]:
        """
        Apply graceful degradation based on risk.
        
        As risk increases:
        1. Reduce automation level
        2. Increase human oversight
        3. Eventually freeze execution
        """
        degradation_level = self._calculate_degradation_level(risk_score)
        
        return {
            "intent": intent,
            "degradation_level": degradation_level,
            "automation_allowed": degradation_level < 3,
            "human_oversight_required": degradation_level >= 2,
            "execution_frozen": degradation_level >= 4
        }
    
    def _calculate_degradation_level(self, risk_score: float) -> int:
        """Calculate degradation level (0-4) based on risk."""
        if risk_score < 0.3:
            return 0  # Full automation
        elif risk_score < 0.5:
            return 1  # Automation with logging
        elif risk_score < 0.7:
            return 2  # Requires notification
        elif risk_score < 0.9:
            return 3  # Requires human approval
        else:
            return 4  # Execution frozen
