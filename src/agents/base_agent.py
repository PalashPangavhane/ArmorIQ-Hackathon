"""
Base Agent Module

Abstract base class for all AI agents in the system.
Agents can reason and propose actions but NEVER execute directly.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class IntentType(Enum):
    """Types of intents an agent can propose."""
    APPROVE_PAYMENT = "approve_payment"
    REJECT_PAYMENT = "reject_payment"
    ESCALATE = "escalate"
    REQUEST_INFO = "request_info"
    FLAG_SUSPICIOUS = "flag_suspicious"


@dataclass
class AgentIntent:
    """
    Structured intent proposed by an agent.
    
    This is what agents produce - intents are then evaluated
    by the policy enforcement layer before any execution.
    """
    intent_type: IntentType
    target_id: str
    parameters: Dict[str, Any]
    reasoning: str
    confidence: float
    agent_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_type": self.intent_type.value,
            "target_id": self.target_id,
            "parameters": self.parameters,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "agent_id": self.agent_id
        }


class BaseAgent(ABC):
    """
    Abstract base class for AI agents.
    
    Agents are responsible for:
    - Analysis and reasoning
    - Querying RAG for context
    - Consuming risk signals from GNN
    - Proposing structured intents
    
    Agents CANNOT:
    - Execute payments directly
    - Modify system state
    - Bypass policy enforcement
    """
    
    def __init__(self, agent_id: str, agent_name: str):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self._rag_service = None
        self._risk_service = None
    
    def set_intelligence_services(self, rag_service, risk_service):
        """Connect agent to intelligence layer services."""
        self._rag_service = rag_service
        self._risk_service = risk_service
    
    @abstractmethod
    async def analyze(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a request and gather relevant context.
        
        Args:
            request: The incoming request to analyze
            
        Returns:
            Analysis results with context
        """
        pass
    
    @abstractmethod
    async def reason(self, analysis: Dict[str, Any]) -> AgentIntent:
        """
        Reason about the analysis and propose an intent.
        
        Args:
            analysis: Results from the analyze phase
            
        Returns:
            Structured intent proposal
        """
        pass
    
    async def process_request(self, request: Dict[str, Any]) -> AgentIntent:
        """
        Full processing pipeline: analyze then reason.
        
        Args:
            request: Incoming request
            
        Returns:
            Proposed intent for policy evaluation
        """
        analysis = await self.analyze(request)
        intent = await self.reason(analysis)
        return intent
    
    async def query_context(self, query: str) -> Dict[str, Any]:
        """Query RAG for relevant context."""
        if self._rag_service is None:
            raise RuntimeError("RAG service not connected")
        return self._rag_service.retrieve(query)
    
    async def get_risk_signal(self, transaction: Dict[str, Any]):
        """Get risk signal from GNN service."""
        if self._risk_service is None:
            raise RuntimeError("Risk service not connected")
        return self._risk_service.assess_transaction_risk(transaction)
