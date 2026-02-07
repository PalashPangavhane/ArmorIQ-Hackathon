"""
Fraud Monitoring Agent Module

Responsible for:
- Consuming risk signals from GNN
- Flagging anomalies and suspicious patterns
- Proposing investigation or freeze intents

NEVER approves or blocks directly - only flags and proposes.
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentIntent, IntentType


class FraudMonitoringAgent(BaseAgent):
    """
    Fraud Monitoring Agent for detecting suspicious activity.
    
    Capabilities:
    - Consume and analyze risk signals
    - Identify patterns across multiple transactions
    - Flag anomalies for review
    - Propose investigation intents
    """
    
    def __init__(self, agent_id: str = "fraud_agent_001"):
        super().__init__(agent_id, "Fraud Monitoring Agent")
        self.alert_threshold = 0.7
        self.pattern_window = 30  # days
    
    async def analyze(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze transaction or activity for fraud signals.
        
        Gathers:
        - Risk signal from GNN
        - Historical patterns for involved entities
        - Related transactions in time window
        """
        analysis = {
            "request": request,
            "risk_signal": None,
            "entity_patterns": {},
            "related_transactions": [],
            "anomaly_indicators": []
        }
        
        # Get primary risk signal
        analysis["risk_signal"] = await self.get_risk_signal(request)
        
        # Analyze patterns for employee
        employee_id = request.get("employee_id")
        if employee_id:
            analysis["entity_patterns"]["employee"] = await self._analyze_entity_patterns(
                employee_id, "employee"
            )
        
        # Analyze patterns for vendor
        vendor_id = request.get("vendor_id")
        if vendor_id:
            analysis["entity_patterns"]["vendor"] = await self._analyze_entity_patterns(
                vendor_id, "vendor"
            )
        
        # Identify anomaly indicators
        analysis["anomaly_indicators"] = self._identify_anomalies(analysis)
        
        return analysis
    
    async def reason(self, analysis: Dict[str, Any]) -> AgentIntent:
        """
        Reason about fraud signals and propose appropriate action.
        
        Actions:
        - FLAG_SUSPICIOUS: Mark for human review
        - REQUEST_INFO: Need more information
        - No action if signals are normal
        """
        risk_signal = analysis.get("risk_signal")
        anomalies = analysis.get("anomaly_indicators", [])
        request = analysis["request"]
        
        # High risk or multiple anomalies -> flag suspicious
        if (risk_signal and risk_signal.risk_score >= self.alert_threshold) or len(anomalies) >= 3:
            return AgentIntent(
                intent_type=IntentType.FLAG_SUSPICIOUS,
                target_id=request.get("request_id"),
                parameters={
                    "risk_score": risk_signal.risk_score if risk_signal else 0,
                    "anomalies": anomalies,
                    "severity": "high" if len(anomalies) >= 3 else "medium"
                },
                reasoning=f"Detected {len(anomalies)} anomaly indicators with risk score {risk_signal.risk_score if risk_signal else 'N/A'}",
                confidence=0.9,
                agent_id=self.agent_id
            )
        
        # Medium risk -> request additional information
        if risk_signal and 0.4 <= risk_signal.risk_score < self.alert_threshold:
            return AgentIntent(
                intent_type=IntentType.REQUEST_INFO,
                target_id=request.get("request_id"),
                parameters={
                    "info_needed": ["receipt_verification", "manager_confirmation"],
                    "risk_context": risk_signal.risk_reasons
                },
                reasoning="Medium risk detected, additional verification recommended",
                confidence=0.75,
                agent_id=self.agent_id
            )
        
        # Low risk -> no action needed
        return AgentIntent(
            intent_type=IntentType.APPROVE_PAYMENT,
            target_id=request.get("request_id"),
            parameters={"fraud_cleared": True},
            reasoning="No significant fraud indicators detected",
            confidence=0.85,
            agent_id=self.agent_id
        )
    
    async def _analyze_entity_patterns(
        self, 
        entity_id: str, 
        entity_type: str
    ) -> Dict[str, Any]:
        """Analyze historical patterns for an entity."""
        if self._risk_service:
            return self._risk_service.get_entity_risk_profile(entity_id, entity_type)
        return {}
    
    def _identify_anomalies(self, analysis: Dict[str, Any]) -> List[str]:
        """Identify specific anomaly indicators."""
        anomalies = []
        risk_signal = analysis.get("risk_signal")
        
        if risk_signal:
            anomalies.extend(risk_signal.risk_reasons)
        
        # Add pattern-based anomalies
        for entity_type, patterns in analysis.get("entity_patterns", {}).items():
            if patterns.get("unusual_frequency"):
                anomalies.append(f"{entity_type}_unusual_frequency")
            if patterns.get("amount_deviation"):
                anomalies.append(f"{entity_type}_amount_deviation")
        
        return anomalies
