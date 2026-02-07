"""
Agent Coordinator Module

Manages agent collaboration and orchestrates multi-agent workflows.
Agents may collaborate and query intelligence services,
but cannot mutate system state.
"""

from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent, AgentIntent, IntentType
from .finance_agent import FinanceAgent
from .fraud_monitoring_agent import FraudMonitoringAgent
from .ceo_approval_agent import CEOApprovalAgent


class AgentCoordinator:
    """
    Coordinates multiple agents for complex request processing.
    
    Workflow:
    1. Route request to appropriate primary agent
    2. Gather fraud monitoring assessment
    3. Handle escalations to higher authority
    4. Combine intents for policy evaluation
    """
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self._finance_agent: Optional[FinanceAgent] = None
        self._fraud_agent: Optional[FraudMonitoringAgent] = None
        self._ceo_agent: Optional[CEOApprovalAgent] = None
    
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the coordinator."""
        self.agents[agent.agent_id] = agent
        
        if isinstance(agent, FinanceAgent):
            self._finance_agent = agent
        elif isinstance(agent, FraudMonitoringAgent):
            self._fraud_agent = agent
        elif isinstance(agent, CEOApprovalAgent):
            self._ceo_agent = agent
    
    async def process_payment_request(
        self, 
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a payment/reimbursement request through agent pipeline.
        
        Flow:
        1. Finance agent analyzes and proposes
        2. Fraud agent provides risk assessment
        3. Escalate if needed
        4. Return combined intents
        """
        results = {
            "request_id": request.get("request_id"),
            "intents": [],
            "final_recommendation": None
        }
        
        # Step 1: Finance agent analysis
        if self._finance_agent:
            finance_intent = await self._finance_agent.process_request(request)
            results["intents"].append(finance_intent.to_dict())
        
        # Step 2: Fraud monitoring
        if self._fraud_agent:
            fraud_intent = await self._fraud_agent.process_request(request)
            results["intents"].append(fraud_intent.to_dict())
        
        # Step 3: Handle escalation if needed
        needs_escalation = any(
            intent.get("intent_type") == IntentType.ESCALATE.value
            for intent in results["intents"]
        )
        
        if needs_escalation and self._ceo_agent:
            escalated_request = {
                **request,
                "escalation_reason": "amount_exceeds_limit",
                "original_analysis": results["intents"]
            }
            ceo_intent = await self._ceo_agent.process_request(escalated_request)
            results["intents"].append(ceo_intent.to_dict())
            results["final_recommendation"] = ceo_intent.to_dict()
        else:
            # Use finance agent recommendation as final
            if results["intents"]:
                results["final_recommendation"] = results["intents"][0]
        
        return results
    
    async def handle_escalation(
        self,
        original_intent: AgentIntent,
        request: Dict[str, Any]
    ) -> AgentIntent:
        """Handle escalation to higher authority agent."""
        if self._ceo_agent:
            escalated_request = {
                **request,
                "escalation_reason": original_intent.parameters.get("reason"),
                "original_analysis": original_intent.to_dict()
            }
            return await self._ceo_agent.process_request(escalated_request)
        
        # No higher authority available
        return AgentIntent(
            intent_type=IntentType.ESCALATE,
            target_id=request.get("request_id"),
            parameters={"escalate_to": "human_review"},
            reasoning="No automated authority available, escalating to human review",
            confidence=1.0,
            agent_id="coordinator"
        )
