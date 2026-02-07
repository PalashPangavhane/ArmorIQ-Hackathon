"""
Tests for Policy Engine
"""

import pytest
from src.control.policy_engine import PolicyEngine, PolicyResult, Policy


class TestPolicyEngine:
    """Tests for the Policy Engine."""
    
    @pytest.fixture
    def policy_engine(self):
        return PolicyEngine()
    
    def test_basic_approval_policy(self, policy_engine):
        """Test basic approval for low amounts."""
        intent = {
            "intent_type": "approve_payment",
            "target_id": "req_001",
            "parameters": {"amount": 500},
            "reasoning": "Test",
            "confidence": 0.9,
            "agent_id": "finance_agent_001"
        }
        
        result = policy_engine.evaluate(intent)
        assert result.result == PolicyResult.ALLOW
    
    def test_high_amount_escalation(self, policy_engine):
        """Test escalation for high amounts."""
        intent = {
            "intent_type": "approve_payment",
            "target_id": "req_002",
            "parameters": {"amount": 15000},
            "reasoning": "Test",
            "confidence": 0.9,
            "agent_id": "finance_agent_001"
        }
        
        result = policy_engine.evaluate(intent)
        assert result.result in [PolicyResult.REQUIRE_CONSTRAINT, PolicyResult.ESCALATE]
