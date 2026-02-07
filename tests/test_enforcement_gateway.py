"""
Tests for Enforcement Gateway
"""

import pytest
from src.control.enforcement_gateway import EnforcementGateway
from src.control.intent_validator import IntentValidator
from src.control.policy_engine import PolicyEngine
from src.control.risk_policy_integrator import RiskPolicyIntegrator


class TestEnforcementGateway:
    """Tests for the Enforcement Gateway."""
    
    @pytest.fixture
    def gateway(self):
        validator = IntentValidator()
        policy_engine = PolicyEngine()
        risk_integrator = RiskPolicyIntegrator(policy_engine)
        return EnforcementGateway(validator, policy_engine, risk_integrator)
    
    @pytest.mark.asyncio
    async def test_valid_intent_processing(self, gateway):
        """Test processing of a valid intent."""
        intent = {
            "intent_type": "approve_payment",
            "target_id": "req_001",
            "parameters": {"amount": 500},
            "reasoning": "Low risk payment within limits",
            "confidence": 0.9,
            "agent_id": "finance_agent_001"
        }
        
        decision = await gateway.process_intent(intent)
        assert decision.decision_id is not None
    
    @pytest.mark.asyncio
    async def test_invalid_intent_rejection(self, gateway):
        """Test rejection of invalid intent."""
        intent = {
            "intent_type": "approve_payment",
            # Missing required fields
        }
        
        decision = await gateway.process_intent(intent)
        assert not decision.allowed
    
    @pytest.mark.asyncio
    async def test_high_risk_freezing(self, gateway):
        """Test that high risk signals freeze execution."""
        intent = {
            "intent_type": "approve_payment",
            "target_id": "req_003",
            "parameters": {"amount": 5000},
            "reasoning": "Test",
            "confidence": 0.9,
            "agent_id": "finance_agent_001"
        }
        
        risk_signal = {
            "risk_level": "HIGH",
            "risk_score": 0.95,
            "risk_reasons": ["suspicious_pattern", "new_vendor"]
        }
        
        decision = await gateway.process_intent(intent, risk_signal)
        # High risk should result in denial or constraints
        assert not decision.allowed or decision.constraints.get("frozen")
