"""
Tests for Policy Engine
"""

import pytest
import os
from src.control.policy_engine import (
    PolicyEngine, 
    PolicyResult, 
    Policy,
    VendorPolicy,
    CategoryPolicy,
    SpendCapPolicy
)


class TestPolicyEngine:
    """Tests for the Policy Engine."""
    
    @pytest.fixture
    def policy_engine(self):
        """Create a policy engine with default policies."""
        engine = PolicyEngine()
        engine.disable_time_window_check()  # Disable for testing
        return engine
    
    # ==========================================
    # AMOUNT-BASED POLICY TESTS
    # ==========================================
    
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
    
    def test_exceeds_per_transaction_limit(self, policy_engine):
        """Test blocking when exceeding per-transaction limit."""
        intent = {
            "intent_type": "approve_payment",
            "target_id": "req_003",
            "parameters": {"amount": 75000},  # Exceeds $50k limit
            "reasoning": "Large purchase",
            "confidence": 0.9,
            "agent_id": "finance_agent_001"
        }
        
        result = policy_engine.evaluate(intent)
        assert result.result == PolicyResult.DENY
        assert "exceeds" in result.reason.lower()
    
    # ==========================================
    # VENDOR POLICY TESTS
    # ==========================================
    
    def test_blocked_vendor(self, policy_engine):
        """Test blocking of transactions to blocked vendors."""
        intent = {
            "intent_type": "approve_payment",
            "target_id": "req_004",
            "parameters": {
                "amount": 100,
                "vendor": "Suspicious Vendor"
            },
            "reasoning": "Test",
            "confidence": 0.9,
            "agent_id": "finance_agent_001"
        }
        
        result = policy_engine.evaluate(intent)
        assert result.result == PolicyResult.DENY
        assert "blocked" in result.reason.lower() or "blocklist" in result.reason.lower()
    
    def test_allowed_vendor(self, policy_engine):
        """Test approval for allowed vendors."""
        intent = {
            "intent_type": "approve_payment",
            "target_id": "req_005",
            "parameters": {
                "amount": 500,
                "vendor": "Office Depot"
            },
            "reasoning": "Test",
            "confidence": 0.9,
            "agent_id": "finance_agent_001"
        }
        
        result = policy_engine.evaluate(intent)
        assert result.result == PolicyResult.ALLOW
    
    # ==========================================
    # CATEGORY POLICY TESTS
    # ==========================================
    
    def test_blocked_category(self, policy_engine):
        """Test blocking of transactions in blocked categories."""
        intent = {
            "intent_type": "approve_payment",
            "target_id": "req_006",
            "parameters": {
                "amount": 100,
                "category": "gambling"
            },
            "reasoning": "Test",
            "confidence": 0.9,
            "agent_id": "finance_agent_001"
        }
        
        result = policy_engine.evaluate(intent)
        assert result.result == PolicyResult.DENY
        assert "category" in result.reason.lower()
    
    def test_allowed_category(self, policy_engine):
        """Test approval for allowed categories."""
        intent = {
            "intent_type": "approve_payment",
            "target_id": "req_007",
            "parameters": {
                "amount": 500,
                "category": "office_supplies"
            },
            "reasoning": "Test",
            "confidence": 0.9,
            "agent_id": "finance_agent_001"
        }
        
        result = policy_engine.evaluate(intent)
        assert result.result == PolicyResult.ALLOW
    
    # ==========================================
    # SPEND CAP TESTS
    # ==========================================
    
    def test_spend_cap_exceeded(self, policy_engine):
        """Test blocking when monthly spend cap is exceeded."""
        # Record previous spending close to limit
        policy_engine._spending_tracker["finance_agent_001"] = 495000  # Close to $500k limit
        
        intent = {
            "intent_type": "approve_payment",
            "target_id": "req_008",
            "parameters": {"amount": 10000},  # Would exceed limit
            "reasoning": "Test",
            "confidence": 0.9,
            "agent_id": "finance_agent_001"
        }
        
        result = policy_engine.evaluate(intent)
        assert result.result == PolicyResult.DENY
        assert "spend cap" in result.reason.lower() or "monthly" in result.reason.lower()
    
    def test_spend_within_cap(self, policy_engine):
        """Test approval when within spend cap."""
        policy_engine._spending_tracker["finance_agent_002"] = 0
        
        intent = {
            "intent_type": "approve_payment",
            "target_id": "req_009",
            "parameters": {"amount": 500},
            "reasoning": "Test",
            "confidence": 0.9,
            "agent_id": "finance_agent_002"
        }
        
        result = policy_engine.evaluate(intent)
        assert result.result == PolicyResult.ALLOW
    
    # ==========================================
    # YAML LOADING TESTS
    # ==========================================
    
    def test_yaml_policy_loading(self):
        """Test that policies are loaded from YAML."""
        config_path = os.path.join(
            os.path.dirname(__file__),
            "..", "config", "policies.yaml"
        )
        
        if os.path.exists(config_path):
            engine = PolicyEngine(config_path)
            assert len(engine.policies) > 0
            assert len(engine.vendor_policies) > 0
            assert len(engine.category_policies) > 0
    
    def test_policy_summary(self, policy_engine):
        """Test getting policy summary."""
        summary = policy_engine.get_policy_summary()
        
        assert "amount_policies" in summary
        assert "vendor_policies" in summary
        assert "category_policies" in summary
        assert summary["amount_policies"] >= 0
    
    # ==========================================
    # COMBINED POLICY TESTS
    # ==========================================
    
    def test_combined_policies_all_pass(self, policy_engine):
        """Test that all policies are checked and pass."""
        intent = {
            "intent_type": "approve_payment",
            "target_id": "req_010",
            "parameters": {
                "amount": 500,
                "vendor": "Office Depot",
                "category": "office_supplies"
            },
            "reasoning": "Regular purchase",
            "confidence": 0.95,
            "agent_id": "finance_agent_001"
        }
        
        result = policy_engine.evaluate(intent)
        assert result.result == PolicyResult.ALLOW
    
    def test_combined_policies_vendor_block(self, policy_engine):
        """Test that vendor block takes precedence even with valid amount."""
        intent = {
            "intent_type": "approve_payment",
            "target_id": "req_011",
            "parameters": {
                "amount": 100,  # Valid amount
                "vendor": "Fraud Inc",  # Blocked vendor
                "category": "office_supplies"  # Valid category
            },
            "reasoning": "Purchase",
            "confidence": 0.95,
            "agent_id": "finance_agent_001"
        }
        
        result = policy_engine.evaluate(intent)
        assert result.result == PolicyResult.DENY


class TestPolicyManagement:
    """Tests for policy management functions."""
    
    def test_add_policy(self):
        """Test adding a new policy."""
        engine = PolicyEngine()
        initial_count = len(engine.policies)
        
        new_policy = Policy(
            policy_id="test_001",
            name="Test Policy",
            description="Test",
            conditions={"intent_type": "test"},
            effect=PolicyResult.ALLOW
        )
        engine.add_policy(new_policy)
        
        assert len(engine.policies) == initial_count + 1
    
    def test_remove_policy(self):
        """Test removing a policy."""
        engine = PolicyEngine()
        initial_count = len(engine.policies)
        
        if engine.policies:
            policy_id = engine.policies[0].policy_id
            engine.remove_policy(policy_id)
            assert len(engine.policies) == initial_count - 1
    
    def test_disable_time_window(self):
        """Test disabling time window check."""
        engine = PolicyEngine()
        engine.disable_time_window_check()
        
        assert len(engine.time_window_policies) == 0
    
    def test_record_spending(self):
        """Test spending tracking."""
        engine = PolicyEngine()
        
        engine.record_spending("agent_001", 1000)
        assert engine.get_spending("agent_001") == 1000
        
        engine.record_spending("agent_001", 500)
        assert engine.get_spending("agent_001") == 1500
