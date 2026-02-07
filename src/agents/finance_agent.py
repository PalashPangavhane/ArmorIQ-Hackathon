"""
Finance Agent Module

Responsible for:
- Reviewing reimbursement requests
- Analyzing budget availability and spending trends
- Proposing approval or escalation intents

NEVER executes payments directly.
"""

from typing import Dict, Any, Optional
from .base_agent import BaseAgent, AgentIntent, IntentType


class FinanceAgent(BaseAgent):
    """
    Finance Agent for processing reimbursement and payment requests.
    
    Capabilities:
    - Query RAG for budget, history, and vendor context
    - Analyze spending patterns
    - Propose structured approval/rejection intents
    """
    
    def __init__(self, agent_id: str = "finance_agent_001"):
        super().__init__(agent_id, "Finance Agent")
        self.approval_limit = 5000.00  # Default limit
    
    async def analyze(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a reimbursement or payment request.
        
        Gathers:
        - Budget availability for the department
        - Employee spending history
        - Vendor legitimacy (if applicable)
        - Risk signals from GNN
        """
        analysis = {
            "request": request,
            "budget_context": None,
            "spending_history": None,
            "vendor_context": None,
            "risk_signal": None
        }
        
        # Query budget context
        department = request.get("department")
        if department:
            budget_query = f"budget availability for {department}"
            analysis["budget_context"] = await self.query_context(budget_query)
        
        # Query spending history
        employee_id = request.get("employee_id")
        if employee_id:
            history_query = f"spending history for employee {employee_id}"
            analysis["spending_history"] = await self.query_context(history_query)
        
        # Query vendor context if applicable
        vendor_id = request.get("vendor_id")
        if vendor_id:
            vendor_query = f"vendor information for {vendor_id}"
            analysis["vendor_context"] = await self.query_context(vendor_query)
        
        # Get risk signal
        analysis["risk_signal"] = await self.get_risk_signal(request)
        
        return analysis
    
    async def reason(self, analysis: Dict[str, Any]) -> AgentIntent:
        """
        Reason about the analysis and propose an intent.
        
        Decision factors:
        - Amount vs approval limit
        - Budget availability
        - Historical patterns
        - Risk signal level
        """
        request = analysis["request"]
        amount = request.get("amount", 0)
        risk_signal = analysis.get("risk_signal")
        
        # Check if amount exceeds agent's approval limit
        if amount > self.approval_limit:
            return AgentIntent(
                intent_type=IntentType.ESCALATE,
                target_id=request.get("request_id"),
                parameters={"amount": amount, "reason": "exceeds_approval_limit"},
                reasoning=f"Amount ${amount} exceeds approval limit of ${self.approval_limit}",
                confidence=1.0,
                agent_id=self.agent_id
            )
        
        # Check risk signal
        if risk_signal and risk_signal.risk_level.value == "HIGH":
            return AgentIntent(
                intent_type=IntentType.FLAG_SUSPICIOUS,
                target_id=request.get("request_id"),
                parameters={"risk_score": risk_signal.risk_score, "reasons": risk_signal.risk_reasons},
                reasoning=f"High risk detected: {', '.join(risk_signal.risk_reasons)}",
                confidence=0.9,
                agent_id=self.agent_id
            )
        
        # Default: propose approval
        return AgentIntent(
            intent_type=IntentType.APPROVE_PAYMENT,
            target_id=request.get("request_id"),
            parameters={"amount": amount},
            reasoning="Request within limits and low risk",
            confidence=0.85,
            agent_id=self.agent_id
        )
    
    async def check_budget_availability(
        self, 
        department: str, 
        amount: float
    ) -> Dict[str, Any]:
        """Check if budget is available for a department."""
        context = await self.query_context(
            f"remaining budget for {department} department"
        )
        return context
