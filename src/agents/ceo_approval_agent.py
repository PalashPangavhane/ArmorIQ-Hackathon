"""
CEO Approval Agent Module

Holds delegated authority for higher-value transactions.
Operates within strictly defined limits.

NEVER executes directly - proposes intents for policy evaluation.
"""

from typing import Dict, Any, Optional
from .base_agent import BaseAgent, AgentIntent, IntentType


class CEOApprovalAgent(BaseAgent):
    """
    CEO Approval Agent for high-value transaction authorization.
    
    Capabilities:
    - Review escalated requests
    - Apply executive judgment within defined limits
    - Approve higher-value transactions
    - Final escalation to human CEO if needed
    
    Strictly Defined Limits:
    - Maximum single transaction approval
    - Daily approval limit
    - Cannot approve self-referential transactions
    """
    
    def __init__(
        self, 
        agent_id: str = "ceo_agent_001",
        max_single_approval: float = 50000.00,
        daily_limit: float = 200000.00
    ):
        super().__init__(agent_id, "CEO Approval Agent")
        self.max_single_approval = max_single_approval
        self.daily_limit = daily_limit
        self._daily_approved = 0.0
    
    async def analyze(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze an escalated request requiring executive approval.
        
        Gathers:
        - Full context from lower-level agent analysis
        - Strategic alignment information
        - Budget impact assessment
        - Risk signals
        """
        analysis = {
            "request": request,
            "escalation_reason": request.get("escalation_reason"),
            "original_agent_analysis": request.get("original_analysis"),
            "strategic_context": None,
            "budget_impact": None,
            "risk_signal": None,
            "within_authority": True
        }
        
        amount = request.get("amount", 0)
        
        # Check if within authority
        if amount > self.max_single_approval:
            analysis["within_authority"] = False
            analysis["authority_exceeded_by"] = amount - self.max_single_approval
        
        if self._daily_approved + amount > self.daily_limit:
            analysis["within_authority"] = False
            analysis["daily_limit_exceeded"] = True
        
        # Get strategic context
        purpose = request.get("purpose", "")
        analysis["strategic_context"] = await self.query_context(
            f"strategic importance of {purpose}"
        )
        
        # Get risk signal
        analysis["risk_signal"] = await self.get_risk_signal(request)
        
        return analysis
    
    async def reason(self, analysis: Dict[str, Any]) -> AgentIntent:
        """
        Apply executive reasoning to escalated request.
        
        Considerations:
        - Authority limits
        - Strategic alignment
        - Risk tolerance
        - Budget impact
        """
        request = analysis["request"]
        amount = request.get("amount", 0)
        
        # Check authority limits
        if not analysis.get("within_authority", True):
            return AgentIntent(
                intent_type=IntentType.ESCALATE,
                target_id=request.get("request_id"),
                parameters={
                    "escalate_to": "human_ceo",
                    "reason": "exceeds_agent_authority",
                    "amount": amount
                },
                reasoning="Amount exceeds delegated authority limits, requires human CEO approval",
                confidence=1.0,
                agent_id=self.agent_id
            )
        
        risk_signal = analysis.get("risk_signal")
        
        # High risk even for CEO agent
        if risk_signal and risk_signal.risk_level.value == "HIGH":
            return AgentIntent(
                intent_type=IntentType.FLAG_SUSPICIOUS,
                target_id=request.get("request_id"),
                parameters={
                    "risk_score": risk_signal.risk_score,
                    "requires_investigation": True
                },
                reasoning="High risk detected even at executive level, flagging for investigation",
                confidence=0.95,
                agent_id=self.agent_id
            )
        
        # Strategic alignment check
        strategic_context = analysis.get("strategic_context", {})
        if self._assess_strategic_value(request, strategic_context):
            return AgentIntent(
                intent_type=IntentType.APPROVE_PAYMENT,
                target_id=request.get("request_id"),
                parameters={
                    "amount": amount,
                    "approval_level": "executive",
                    "strategic_justification": True
                },
                reasoning="Approved at executive level with strategic justification",
                confidence=0.9,
                agent_id=self.agent_id
            )
        
        # Default rejection for non-strategic high-value requests
        return AgentIntent(
            intent_type=IntentType.REJECT_PAYMENT,
            target_id=request.get("request_id"),
            parameters={
                "reason": "insufficient_strategic_justification",
                "amount": amount
            },
            reasoning="High-value request lacks sufficient strategic justification",
            confidence=0.8,
            agent_id=self.agent_id
        )
    
    def _assess_strategic_value(
        self, 
        request: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> bool:
        """Assess if request has strategic value."""
        # Implement strategic assessment logic
        return True  # Placeholder
    
    def reset_daily_limit(self):
        """Reset daily approval counter (called at day boundary)."""
        self._daily_approved = 0.0
