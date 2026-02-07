"""
Policy Engine Module

Evaluates static policy rules against agent intents.
Enforces approval hierarchies and bounded delegation.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class PolicyResult(Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_CONSTRAINT = "require_constraint"
    ESCALATE = "escalate"


@dataclass
class PolicyEvaluation:
    """Result of policy evaluation."""
    result: PolicyResult
    policy_id: str
    reason: str
    constraints: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result": self.result.value,
            "policy_id": self.policy_id,
            "reason": self.reason,
            "constraints": self.constraints
        }


@dataclass
class Policy:
    """Represents a policy rule."""
    policy_id: str
    name: str
    description: str
    conditions: Dict[str, Any]
    effect: PolicyResult
    priority: int = 0


class PolicyEngine:
    """
    Evaluates policies against agent intents.
    
    Responsibilities:
    - Load and manage policy rules
    - Evaluate intents against policies
    - Apply approval hierarchies
    - Enforce least-privilege execution
    """
    
    def __init__(self):
        self.policies: List[Policy] = []
        self._load_default_policies()
    
    def _load_default_policies(self):
        """Load default policy rules."""
        # Policy: Basic approval limits
        self.policies.append(Policy(
            policy_id="pol_001",
            name="basic_approval_limit",
            description="Approve payments under $1000 without escalation",
            conditions={"max_amount": 1000, "intent_type": "approve_payment"},
            effect=PolicyResult.ALLOW,
            priority=1
        ))
        
        # Policy: Require dual approval for high amounts
        self.policies.append(Policy(
            policy_id="pol_002",
            name="dual_approval_required",
            description="Require dual approval for amounts over $10000",
            conditions={"min_amount": 10000, "intent_type": "approve_payment"},
            effect=PolicyResult.REQUIRE_CONSTRAINT,
            priority=2
        ))
        
        # Policy: Block suspicious flagged transactions
        self.policies.append(Policy(
            policy_id="pol_003",
            name="block_suspicious",
            description="Block transactions flagged as suspicious",
            conditions={"intent_type": "flag_suspicious", "severity": "high"},
            effect=PolicyResult.DENY,
            priority=3
        ))
    
    def evaluate(self, intent: Dict[str, Any]) -> PolicyEvaluation:
        """
        Evaluate an intent against all applicable policies.
        
        Args:
            intent: Agent intent to evaluate
            
        Returns:
            PolicyEvaluation with result and any constraints
        """
        applicable_policies = self._find_applicable_policies(intent)
        
        if not applicable_policies:
            return PolicyEvaluation(
                result=PolicyResult.ALLOW,
                policy_id="default",
                reason="No applicable policies found, allowing by default"
            )
        
        # Sort by priority and evaluate
        applicable_policies.sort(key=lambda p: p.priority, reverse=True)
        
        for policy in applicable_policies:
            evaluation = self._evaluate_policy(policy, intent)
            if evaluation.result != PolicyResult.ALLOW:
                return evaluation
        
        return PolicyEvaluation(
            result=PolicyResult.ALLOW,
            policy_id="combined",
            reason="All applicable policies passed"
        )
    
    def _find_applicable_policies(self, intent: Dict[str, Any]) -> List[Policy]:
        """Find policies that apply to this intent."""
        applicable = []
        intent_type = intent.get("intent_type")
        
        for policy in self.policies:
            if policy.conditions.get("intent_type") == intent_type:
                applicable.append(policy)
        
        return applicable
    
    def _evaluate_policy(
        self, 
        policy: Policy, 
        intent: Dict[str, Any]
    ) -> PolicyEvaluation:
        """Evaluate a single policy against an intent."""
        params = intent.get("parameters", {})
        amount = params.get("amount", 0)
        
        conditions = policy.conditions
        
        # Check amount conditions
        if "max_amount" in conditions:
            if amount > conditions["max_amount"]:
                return PolicyEvaluation(
                    result=PolicyResult.ESCALATE,
                    policy_id=policy.policy_id,
                    reason=f"Amount {amount} exceeds limit {conditions['max_amount']}"
                )
        
        if "min_amount" in conditions:
            if amount >= conditions["min_amount"]:
                return PolicyEvaluation(
                    result=policy.effect,
                    policy_id=policy.policy_id,
                    reason=f"Amount {amount} triggers policy {policy.name}",
                    constraints={"dual_approval": True}
                )
        
        return PolicyEvaluation(
            result=PolicyResult.ALLOW,
            policy_id=policy.policy_id,
            reason=f"Policy {policy.name} conditions met"
        )
    
    def add_policy(self, policy: Policy):
        """Add a new policy rule."""
        self.policies.append(policy)
    
    def remove_policy(self, policy_id: str):
        """Remove a policy by ID."""
        self.policies = [p for p in self.policies if p.policy_id != policy_id]
