"""
Delegation Agent Module

Demonstrates bounded delegation where one agent can delegate limited
authority to another agent, which CANNOT exceed that authority.

This is a KEY requirement for the hackathon:
"At least one well scoped delegation scenario where another agent 
acts on a user's behalf without exceeding granted authority."
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from .base_agent import BaseAgent, AgentIntent, IntentType


class DelegationScope(Enum):
    """Types of delegated authority."""
    APPROVE_SMALL = "approve_small"      # Up to $1,000
    APPROVE_MEDIUM = "approve_medium"    # Up to $5,000  
    VIEW_ONLY = "view_only"              # Can only read, no actions
    SPECIFIC_VENDOR = "specific_vendor"  # Only specific vendor payments
    TIME_LIMITED = "time_limited"        # Only for limited time


@dataclass
class DelegationGrant:
    """
    Represents a grant of limited authority from one agent to another.
    
    This is the core of bounded delegation - it explicitly defines
    what the delegate CAN and CANNOT do.
    """
    grant_id: str
    delegator_id: str          # Agent granting authority
    delegate_id: str           # Agent receiving authority
    scope: DelegationScope     # Type of delegation
    constraints: Dict[str, Any]  # Specific limits
    created_at: str
    expires_at: Optional[str] = None
    max_uses: Optional[int] = None
    uses_remaining: Optional[int] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "delegator_id": self.delegator_id,
            "delegate_id": self.delegate_id,
            "scope": self.scope.value,
            "constraints": self.constraints,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "max_uses": self.max_uses,
            "uses_remaining": self.uses_remaining,
            "is_active": self.is_active
        }


@dataclass
class DelegationAttempt:
    """Record of an attempt to use delegated authority."""
    attempt_id: str
    grant_id: str
    delegate_id: str
    intent: Dict[str, Any]
    timestamp: str
    allowed: bool
    reason: str
    exceeded_authority: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "grant_id": self.grant_id,
            "delegate_id": self.delegate_id,
            "intent": self.intent,
            "timestamp": self.timestamp,
            "allowed": self.allowed,
            "reason": self.reason,
            "exceeded_authority": self.exceeded_authority
        }


class DelegationManager:
    """
    Manages delegation grants between agents.
    
    Key responsibilities:
    1. Create delegation grants with bounded authority
    2. Validate that delegated actions stay within bounds
    3. Block actions that exceed delegated authority
    4. Maintain audit trail of all delegation attempts
    """
    
    def __init__(self):
        self._grants: Dict[str, DelegationGrant] = {}
        self._attempts: List[DelegationAttempt] = []
    
    def create_grant(
        self,
        delegator_id: str,
        delegate_id: str,
        scope: DelegationScope,
        constraints: Dict[str, Any],
        expires_in_hours: Optional[int] = None,
        max_uses: Optional[int] = None
    ) -> DelegationGrant:
        """
        Create a new delegation grant.
        
        Args:
            delegator_id: Agent granting authority
            delegate_id: Agent receiving authority
            scope: Type of delegation
            constraints: Specific limits (amount, vendor, etc.)
            expires_in_hours: Optional expiration
            max_uses: Optional use limit
            
        Returns:
            Created DelegationGrant
        """
        grant_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        expires_at = None
        if expires_in_hours:
            from datetime import timedelta
            expires_at = (now + timedelta(hours=expires_in_hours)).isoformat()
        
        grant = DelegationGrant(
            grant_id=grant_id,
            delegator_id=delegator_id,
            delegate_id=delegate_id,
            scope=scope,
            constraints=constraints,
            created_at=now.isoformat(),
            expires_at=expires_at,
            max_uses=max_uses,
            uses_remaining=max_uses,
            is_active=True
        )
        
        self._grants[grant_id] = grant
        
        print(f"\n{'='*60}")
        print(f"🔑 DELEGATION GRANT CREATED")
        print(f"{'='*60}")
        print(f"Grant ID: {grant_id[:8]}...")
        print(f"From: {delegator_id} → To: {delegate_id}")
        print(f"Scope: {scope.value}")
        print(f"Constraints: {constraints}")
        if max_uses:
            print(f"Max Uses: {max_uses}")
        if expires_at:
            print(f"Expires: {expires_at}")
        print(f"{'='*60}\n")
        
        return grant
    
    def check_authority(
        self,
        delegate_id: str,
        intent: Dict[str, Any]
    ) -> tuple[bool, str, Optional[str]]:
        """
        Check if a delegate has authority for an intent.
        
        Args:
            delegate_id: Agent attempting the action
            intent: Intent being attempted
            
        Returns:
            Tuple of (allowed, reason, grant_id)
        """
        # Find active grants for this delegate
        active_grants = [
            g for g in self._grants.values()
            if g.delegate_id == delegate_id and g.is_active
        ]
        
        if not active_grants:
            return False, "No active delegation grants found", None
        
        intent_type = intent.get("intent_type", "")
        params = intent.get("parameters", {})
        amount = params.get("amount", 0)
        vendor = params.get("vendor", "")
        
        for grant in active_grants:
            # Check expiration
            if grant.expires_at:
                if datetime.utcnow().isoformat() > grant.expires_at:
                    grant.is_active = False
                    continue
            
            # Check uses remaining
            if grant.uses_remaining is not None and grant.uses_remaining <= 0:
                grant.is_active = False
                continue
            
            # Check scope-specific constraints
            allowed, reason = self._check_scope_constraints(
                grant, intent_type, amount, vendor
            )
            
            if allowed:
                # Decrement uses
                if grant.uses_remaining is not None:
                    grant.uses_remaining -= 1
                
                return True, reason, grant.grant_id
        
        return False, "Intent exceeds all available delegation authorities", None
    
    def _check_scope_constraints(
        self,
        grant: DelegationGrant,
        intent_type: str,
        amount: float,
        vendor: str
    ) -> tuple[bool, str]:
        """Check if intent fits within grant's scope constraints."""
        
        if grant.scope == DelegationScope.VIEW_ONLY:
            return False, "Delegation is view-only, no actions allowed"
        
        if grant.scope == DelegationScope.APPROVE_SMALL:
            max_amount = grant.constraints.get("max_amount", 1000)
            if intent_type != "approve_payment":
                return False, f"Delegation only allows approve_payment, not {intent_type}"
            if amount > max_amount:
                return False, f"Amount ${amount} exceeds delegated limit of ${max_amount}"
            return True, f"Within delegated authority (amount ${amount} ≤ ${max_amount})"
        
        if grant.scope == DelegationScope.APPROVE_MEDIUM:
            max_amount = grant.constraints.get("max_amount", 5000)
            if intent_type != "approve_payment":
                return False, f"Delegation only allows approve_payment, not {intent_type}"
            if amount > max_amount:
                return False, f"Amount ${amount} exceeds delegated limit of ${max_amount}"
            return True, f"Within delegated authority (amount ${amount} ≤ ${max_amount})"
        
        if grant.scope == DelegationScope.SPECIFIC_VENDOR:
            allowed_vendor = grant.constraints.get("vendor", "")
            if vendor.lower() != allowed_vendor.lower():
                return False, f"Delegation only allows vendor '{allowed_vendor}', not '{vendor}'"
            max_amount = grant.constraints.get("max_amount", float('inf'))
            if amount > max_amount:
                return False, f"Amount ${amount} exceeds delegated limit of ${max_amount}"
            return True, f"Within delegated authority for vendor {vendor}"
        
        return False, "Unknown delegation scope"
    
    def record_attempt(
        self,
        grant_id: Optional[str],
        delegate_id: str,
        intent: Dict[str, Any],
        allowed: bool,
        reason: str,
        exceeded_authority: bool = False
    ):
        """Record a delegation attempt for audit trail."""
        attempt = DelegationAttempt(
            attempt_id=str(uuid.uuid4()),
            grant_id=grant_id or "NONE",
            delegate_id=delegate_id,
            intent=intent,
            timestamp=datetime.utcnow().isoformat(),
            allowed=allowed,
            reason=reason,
            exceeded_authority=exceeded_authority
        )
        self._attempts.append(attempt)
        
        status = "✅ ALLOWED" if allowed else "🚫 BLOCKED"
        if exceeded_authority:
            status = "⛔ EXCEEDED AUTHORITY"
        
        print(f"[Delegation] {status}: {reason}")
    
    def get_attempts(self) -> List[Dict[str, Any]]:
        """Get all delegation attempts for audit."""
        return [a.to_dict() for a in self._attempts]
    
    def get_exceeded_attempts(self) -> List[Dict[str, Any]]:
        """Get attempts that exceeded delegated authority."""
        return [a.to_dict() for a in self._attempts if a.exceeded_authority]
    
    def revoke_grant(self, grant_id: str) -> bool:
        """Revoke a delegation grant."""
        if grant_id in self._grants:
            self._grants[grant_id].is_active = False
            print(f"[Delegation] Grant {grant_id[:8]}... revoked")
            return True
        return False


class DelegateAgent(BaseAgent):
    """
    An agent that operates with delegated authority.
    
    This agent:
    1. Can only act within bounds of its delegation grants
    2. CANNOT exceed the authority given to it
    3. All actions are verified against delegation constraints
    4. Maintains clear traceability of delegated actions
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        delegation_manager: DelegationManager
    ):
        super().__init__(agent_id, agent_name)
        self.delegation_manager = delegation_manager
        self._pending_intents: List[AgentIntent] = []
    
    async def analyze(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a request (free reasoning)."""
        # Agent can freely analyze - no constraints here
        analysis = {
            "request_id": request.get("id"),
            "amount": request.get("amount", 0),
            "vendor": request.get("vendor", ""),
            "description": request.get("description", ""),
            "urgency": request.get("urgency", "normal")
        }
        
        # Check what authority we have
        analysis["delegation_status"] = "Will check authority before proposing action"
        
        return analysis
    
    async def reason(self, analysis: Dict[str, Any]) -> AgentIntent:
        """
        Reason about what action to take.
        
        The agent reasons freely but knows its actions will be
        constrained by its delegated authority.
        """
        amount = analysis.get("amount", 0)
        request_id = analysis.get("request_id", str(uuid.uuid4()))
        
        # Free reasoning about what SHOULD happen
        if amount < 500:
            reasoning = f"This is a small payment of ${amount}. Recommending approval."
        elif amount < 2000:
            reasoning = f"This is a moderate payment of ${amount}. Will attempt approval within delegated limits."
        else:
            reasoning = f"This is a larger payment of ${amount}. May exceed my delegated authority."
        
        # Propose the intent (will be checked against delegation)
        intent = AgentIntent(
            intent_type=IntentType.APPROVE_PAYMENT,
            target_id=request_id,
            parameters={
                "amount": amount,
                "vendor": analysis.get("vendor", ""),
                "description": analysis.get("description", "")
            },
            reasoning=reasoning,
            confidence=0.8,
            agent_id=self.agent_id
        )
        
        return intent
    
    async def act_with_delegation(
        self,
        intent: AgentIntent
    ) -> Dict[str, Any]:
        """
        Attempt to act using delegated authority.
        
        This is where the delegation constraints are enforced.
        The agent CANNOT bypass this check.
        """
        intent_dict = intent.to_dict()
        
        # Check if we have authority
        allowed, reason, grant_id = self.delegation_manager.check_authority(
            self.agent_id,
            intent_dict
        )
        
        if not allowed:
            # Record the attempt that exceeded authority
            self.delegation_manager.record_attempt(
                grant_id=grant_id,
                delegate_id=self.agent_id,
                intent=intent_dict,
                allowed=False,
                reason=reason,
                exceeded_authority=True
            )
            
            return {
                "success": False,
                "blocked": True,
                "reason": f"DELEGATION BLOCKED: {reason}",
                "intent": intent_dict,
                "exceeded_authority": True
            }
        
        # Authority confirmed - record and proceed
        self.delegation_manager.record_attempt(
            grant_id=grant_id,
            delegate_id=self.agent_id,
            intent=intent_dict,
            allowed=True,
            reason=reason
        )
        
        return {
            "success": True,
            "blocked": False,
            "reason": reason,
            "intent": intent_dict,
            "grant_id": grant_id,
            "proceed_to_gateway": True  # Now goes to enforcement gateway
        }


# Factory function
def create_delegation_scenario() -> tuple[DelegationManager, DelegateAgent]:
    """Create a delegation scenario for demonstration."""
    manager = DelegationManager()
    
    delegate = DelegateAgent(
        agent_id="delegate_agent_001",
        agent_name="Junior Payment Processor",
        delegation_manager=manager
    )
    
    return manager, delegate
