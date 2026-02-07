"""
ArmorIQ Hackathon Demo - Agent Constrained Execution

This demo showcases the KEY requirements:

1. ✅ CLEAN SEPARATION between agent reasoning and real world execution
   - Agents reason freely about what to do
   - Actions ONLY happen through MCP servers

2. ✅ ALL ACTIONS flow through MCP servers that enforce user-defined rules
   - Policy engine checks every intent
   - MCP servers only execute with valid decision IDs

3. ✅ CLEAR BLOCKING BEHAVIOR when actions violate rules
   - Demo shows explicit blocks with reasons
   - Audit trail captures all blocked attempts

4. ✅ TRACEABILITY from agent plans to executed actions
   - Complete audit trail from reasoning to execution
   - Every step logged with context

5. ✅ DELEGATION SCENARIO where agent acts on behalf of user
   - Junior agent has limited delegated authority
   - Cannot exceed that authority

Run with: python demos/agent_constrained_execution.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.base_agent import BaseAgent, AgentIntent, IntentType
from src.agents.delegation_agent import (
    DelegationManager, 
    DelegateAgent, 
    DelegationScope
)
from src.control.policy_engine import PolicyEngine, PolicyResult
from src.control.intent_validator import IntentValidator
from src.control.risk_policy_integrator import RiskPolicyIntegrator
from src.control.enforcement_gateway import EnforcementGateway
from src.control.audit_trail import (
    AuditTrailSystem, 
    AuditEventType, 
    get_audit_system
)
from src.execution.mcp.mcp_client import MCPClient


class PaymentProcessingAgent(BaseAgent):
    """
    AI Agent that processes payment requests.
    
    This agent can REASON freely about payments but CANNOT
    directly execute them - all actions must go through the
    enforcement gateway and MCP servers.
    """
    
    def __init__(self, agent_id: str = "payment_agent_001"):
        super().__init__(agent_id, "Payment Processing Agent")
    
    async def analyze(self, request: dict) -> dict:
        """
        STAGE 1: FREE REASONING
        
        The agent analyzes the request using any available context.
        This is unconstrained - the agent can think about anything.
        """
        print(f"\n{'─'*60}")
        print(f"🧠 AGENT REASONING (Free - No Constraints)")
        print(f"{'─'*60}")
        
        amount = request.get("amount", 0)
        vendor = request.get("vendor", "Unknown")
        description = request.get("description", "")
        
        # Agent freely reasons about the request
        analysis = {
            "request_id": request.get("id", "unknown"),
            "amount": amount,
            "vendor": vendor,
            "description": description,
            "risk_assessment": self._assess_risk(amount, vendor),
            "recommendation": self._make_recommendation(amount),
            "confidence": 0.85
        }
        
        print(f"📊 Analyzing: ${amount} payment to {vendor}")
        print(f"   Description: {description}")
        print(f"   Risk Assessment: {analysis['risk_assessment']}")
        print(f"   Recommendation: {analysis['recommendation']}")
        
        return analysis
    
    def _assess_risk(self, amount: float, vendor: str) -> str:
        """Assess risk level of payment."""
        if amount > 10000:
            return "HIGH - Exceeds standard approval threshold"
        elif amount > 5000:
            return "MEDIUM - Requires additional review"
        else:
            return "LOW - Within standard limits"
    
    def _make_recommendation(self, amount: float) -> str:
        """Make a recommendation based on analysis."""
        if amount > 10000:
            return "ESCALATE to finance director"
        elif amount > 5000:
            return "APPROVE with dual signature"
        else:
            return "APPROVE - standard workflow"
    
    async def reason(self, analysis: dict) -> AgentIntent:
        """
        STAGE 2: PROPOSE INTENT
        
        Based on reasoning, the agent proposes a structured intent.
        This is still just a PROPOSAL - not execution.
        """
        print(f"\n{'─'*60}")
        print(f"📝 AGENT PROPOSES INTENT (Still No Execution)")
        print(f"{'─'*60}")
        
        amount = analysis["amount"]
        
        if amount > 10000:
            intent_type = IntentType.ESCALATE
            reasoning = f"Amount ${amount} exceeds my approval authority, escalating to director"
        elif analysis["risk_assessment"].startswith("HIGH"):
            intent_type = IntentType.FLAG_SUSPICIOUS
            reasoning = "Flagging for additional review due to risk signals"
        else:
            intent_type = IntentType.APPROVE_PAYMENT
            reasoning = f"Payment of ${amount} is within policy limits, recommending approval"
        
        intent = AgentIntent(
            intent_type=intent_type,
            target_id=analysis["request_id"],
            parameters={
                "amount": amount,
                "vendor": analysis["vendor"],
                "description": analysis["description"]
            },
            reasoning=reasoning,
            confidence=analysis["confidence"],
            agent_id=self.agent_id
        )
        
        print(f"Intent Type: {intent_type.value}")
        print(f"Reasoning: {reasoning}")
        print(f"⚠️ NOTE: This is just a proposal - execution requires Gateway approval")
        
        return intent


async def demo_scenario_1_approved_payment():
    """
    SCENARIO 1: Payment within policy limits - APPROVED
    
    Shows the full flow from reasoning to execution.
    """
    print("\n" + "="*70)
    print("🎯 SCENARIO 1: Small Payment - Within Policy Limits")
    print("="*70)
    
    # Setup
    audit = get_audit_system()
    trace_id = audit.start_trace(
        session_id="demo_session_001",
        request={"scenario": "small_payment", "expected": "approved"}
    )
    
    agent = PaymentProcessingAgent()
    
    # Request
    request = {
        "id": "PAY-001",
        "amount": 500,
        "vendor": "Office Supplies Inc",
        "description": "Monthly office supplies"
    }
    
    # Stage 1: Agent Reasoning (Free)
    analysis = await agent.analyze(request)
    audit.log_event(
        trace_id, AuditEventType.AGENT_REASONING, agent.agent_id,
        {"analysis": analysis, "stage": "free_reasoning"}
    )
    
    # Stage 2: Agent Proposes Intent
    intent = await agent.reason(analysis)
    audit.log_event(
        trace_id, AuditEventType.INTENT_PROPOSED, agent.agent_id,
        {"intent": intent.to_dict(), "stage": "proposal_only"}
    )
    
    # Stage 3: Policy Enforcement (Constrained)
    print(f"\n{'─'*60}")
    print(f"⚖️ ENFORCEMENT GATEWAY (Constraints Applied)")
    print(f"{'─'*60}")
    
    # Create enforcement components
    policy_engine = PolicyEngine()
    intent_validator = IntentValidator()
    risk_integrator = RiskPolicyIntegrator(policy_engine)
    gateway = EnforcementGateway(intent_validator, policy_engine, risk_integrator)
    
    mcp_client = MCPClient()
    gateway.set_mcp_client(mcp_client)
    
    # Gateway evaluates intent
    decision = await gateway.process_intent(intent.to_dict())
    
    audit.log_event(
        trace_id, AuditEventType.DECISION_MADE, "gateway",
        {"decision_id": decision.decision_id, "allowed": decision.allowed, "reason": decision.reason}
    )
    
    print(f"Decision: {'✅ ALLOWED' if decision.allowed else '🚫 DENIED'}")
    print(f"Reason: {decision.reason}")
    
    # Stage 4: MCP Execution (Only if allowed)
    if decision.allowed:
        print(f"\n{'─'*60}")
        print(f"▶️ MCP SERVER EXECUTION (Real Action)")
        print(f"{'─'*60}")
        
        result = await gateway.execute_if_allowed(decision, intent.to_dict(), agent.agent_id)
        
        audit.log_event(
            trace_id, AuditEventType.EXECUTION_SUCCESS, agent.agent_id,
            {"result": result}
        )
        audit.complete_trace(trace_id, "executed")
        
        print(f"Execution Result: {'✅ SUCCESS' if result.get('executed') else '❌ FAILED'}")
    
    return trace_id


async def demo_scenario_2_blocked_payment():
    """
    SCENARIO 2: Payment flagged as suspicious - BLOCKED
    
    Shows clear blocking behavior when policies are violated.
    """
    print("\n" + "="*70)
    print("🎯 SCENARIO 2: Suspicious Payment - BLOCKED BY POLICY")
    print("="*70)
    
    audit = get_audit_system()
    trace_id = audit.start_trace(
        session_id="demo_session_002",
        request={"scenario": "suspicious_payment", "expected": "blocked"}
    )
    
    agent = PaymentProcessingAgent()
    
    # Suspicious request
    request = {
        "id": "PAY-002",
        "amount": 15000,
        "vendor": "Unknown Foreign Entity",
        "description": "Urgent wire transfer"
    }
    
    # Agent reasoning
    analysis = await agent.analyze(request)
    audit.log_event(
        trace_id, AuditEventType.AGENT_REASONING, agent.agent_id,
        {"analysis": analysis}
    )
    
    # Agent proposes (escalate due to amount)
    intent = await agent.reason(analysis)
    audit.log_event(
        trace_id, AuditEventType.INTENT_PROPOSED, agent.agent_id,
        {"intent": intent.to_dict()}
    )
    
    print(f"\n{'─'*60}")
    print(f"⚖️ ENFORCEMENT GATEWAY - Adding Risk Signal")
    print(f"{'─'*60}")
    
    # Create gateway with HIGH risk signal
    policy_engine = PolicyEngine()
    intent_validator = IntentValidator()
    risk_integrator = RiskPolicyIntegrator(policy_engine)
    gateway = EnforcementGateway(intent_validator, policy_engine, risk_integrator)
    
    mcp_client = MCPClient()
    gateway.set_mcp_client(mcp_client)
    
    # Add risk signal that triggers blocking
    risk_signal = {
        "risk_score": 0.95,  # Very high risk
        "risk_factors": ["unknown_vendor", "high_amount", "urgent_flag"],
        "recommendation": "block"
    }
    
    print(f"Risk Signal: score={risk_signal['risk_score']}, factors={risk_signal['risk_factors']}")
    
    audit.log_event(
        trace_id, AuditEventType.RISK_ASSESSMENT, "gnn_model",
        {"risk_signal": risk_signal}
    )
    
    # Gateway evaluates with risk signal
    decision = await gateway.process_intent(intent.to_dict(), risk_signal)
    
    audit.log_event(
        trace_id, AuditEventType.DECISION_MADE, "gateway",
        {"decision_id": decision.decision_id, "allowed": decision.allowed, "reason": decision.reason}
    )
    
    print(f"\nDecision: {'✅ ALLOWED' if decision.allowed else '🚫 BLOCKED'}")
    print(f"Reason: {decision.reason}")
    
    if not decision.allowed:
        audit.log_event(
            trace_id, AuditEventType.EXECUTION_BLOCKED, "gateway",
            {"reason": decision.reason}
        )
        audit.complete_trace(trace_id, "blocked")
        print(f"\n⛔ EXECUTION BLOCKED - Payment will NOT proceed")
    
    return trace_id


async def demo_scenario_3_delegation():
    """
    SCENARIO 3: Bounded Delegation
    
    Shows an agent acting on behalf of another with LIMITED authority.
    The delegate CANNOT exceed their granted authority.
    """
    print("\n" + "="*70)
    print("🎯 SCENARIO 3: Bounded Delegation - Limited Authority")
    print("="*70)
    
    audit = get_audit_system()
    trace_id = audit.start_trace(
        session_id="demo_session_003",
        request={"scenario": "delegation", "expected": "partial"}
    )
    
    # Create delegation scenario
    delegation_manager = DelegationManager()
    
    # Senior agent grants LIMITED authority to junior agent
    print(f"\n{'─'*60}")
    print(f"🔑 DELEGATION GRANT")
    print(f"{'─'*60}")
    
    grant = delegation_manager.create_grant(
        delegator_id="senior_agent_001",
        delegate_id="junior_agent_001",
        scope=DelegationScope.APPROVE_SMALL,
        constraints={
            "max_amount": 1000,
            "allowed_vendors": ["Office Supplies Inc", "IT Equipment Co"]
        },
        max_uses=3
    )
    
    audit.log_event(
        trace_id, AuditEventType.DELEGATION_CHECK, "senior_agent_001",
        {"grant_created": grant.to_dict(), "granted_to": "junior_agent_001"}
    )
    
    # Create delegate agent
    delegate = DelegateAgent(
        agent_id="junior_agent_001",
        agent_name="Junior Payment Processor",
        delegation_manager=delegation_manager
    )
    
    # Test 1: Within delegated authority (should succeed)
    print(f"\n{'─'*60}")
    print(f"📋 TEST 1: Payment WITHIN Delegated Authority")
    print(f"{'─'*60}")
    
    small_request = {
        "id": "DEL-001",
        "amount": 500,
        "vendor": "Office Supplies Inc",
        "description": "Printer paper"
    }
    
    analysis = await delegate.analyze(small_request)
    intent = await delegate.reason(analysis)
    
    print(f"\nJunior agent attempting: ${small_request['amount']} to {small_request['vendor']}")
    result = await delegate.act_with_delegation(intent)
    
    audit.log_event(
        trace_id, AuditEventType.DELEGATION_CHECK, delegate.agent_id,
        {"attempt": "within_authority", "result": result}
    )
    
    print(f"Result: {'✅ ALLOWED' if not result.get('blocked') else '🚫 BLOCKED'}")
    print(f"Reason: {result.get('reason')}")
    
    # Test 2: EXCEEDS delegated authority (should be blocked)
    print(f"\n{'─'*60}")
    print(f"📋 TEST 2: Payment EXCEEDS Delegated Authority")
    print(f"{'─'*60}")
    
    large_request = {
        "id": "DEL-002",
        "amount": 5000,  # Exceeds $1000 limit!
        "vendor": "Office Supplies Inc",
        "description": "Premium equipment"
    }
    
    analysis2 = await delegate.analyze(large_request)
    intent2 = await delegate.reason(analysis2)
    
    print(f"\nJunior agent attempting: ${large_request['amount']} to {large_request['vendor']}")
    print(f"⚠️ This EXCEEDS the $1000 delegated limit!")
    
    result2 = await delegate.act_with_delegation(intent2)
    
    audit.log_event(
        trace_id, AuditEventType.DELEGATION_CHECK, delegate.agent_id,
        {"attempt": "exceeds_authority", "result": result2, "exceeded": True}
    )
    
    print(f"\nResult: {'✅ ALLOWED' if not result2.get('blocked') else '🚫 BLOCKED'}")
    print(f"Reason: {result2.get('reason')}")
    print(f"Exceeded Authority: {result2.get('exceeded_authority', False)}")
    
    audit.complete_trace(trace_id, "completed")
    
    return trace_id


async def demo_scenario_4_bypass_attempt():
    """
    SCENARIO 4: Attempt to bypass enforcement gateway - BLOCKED
    
    Shows that even if an agent tries to execute directly on MCP,
    it will be blocked without a valid gateway decision.
    """
    print("\n" + "="*70)
    print("🎯 SCENARIO 4: Bypass Attempt - Direct MCP Access BLOCKED")
    print("="*70)
    
    audit = get_audit_system()
    trace_id = audit.start_trace(
        session_id="demo_session_004",
        request={"scenario": "bypass_attempt", "expected": "blocked"}
    )
    
    mcp_client = MCPClient()
    
    print(f"\n{'─'*60}")
    print(f"🚨 MALICIOUS ATTEMPT: Direct MCP Execution (No Gateway)")
    print(f"{'─'*60}")
    
    # Try to execute directly without gateway approval
    fake_intent = {
        "intent_type": "approve_payment",
        "target_id": "FAKE-001",
        "parameters": {
            "amount": 10000,
            "vendor": "Suspicious Entity"
        }
    }
    
    print(f"Attempting to execute ${fake_intent['parameters']['amount']} payment...")
    print(f"⚠️ WITHOUT going through Enforcement Gateway!")
    
    # This should be BLOCKED because there's no valid decision_id
    result = await mcp_client.execute({
        "decision_id": "fake_decision_id_12345",  # Invalid!
        "intent": fake_intent,
        "constraints": {},
        "agent_id": "malicious_agent"
    })
    
    audit.log_event(
        trace_id, AuditEventType.EXECUTION_BLOCKED, "mcp_client",
        {"reason": "Invalid decision_id", "blocked": True}
    )
    
    print(f"\nResult: {'🚫 BLOCKED' if result.get('blocked') else '❌ ERROR'}")
    print(f"Reason: {result.get('error')}")
    
    audit.complete_trace(trace_id, "blocked")
    
    # Show blocked attempts
    print(f"\n{'─'*60}")
    print(f"📋 MCP CLIENT BLOCKED ATTEMPTS LOG")
    print(f"{'─'*60}")
    mcp_client.print_audit_trail()
    
    return trace_id


async def main(interactive: bool = True):
    """Run the complete demo."""
    print("\n" + "="*70)
    print("🛡️ ArmorIQ - Agent Constrained Execution Demo")
    print("="*70)
    print("""
This demo shows:

1. ✅ CLEAN SEPARATION: Agents reason freely, actions constrained
2. ✅ MCP ENFORCEMENT: All actions flow through MCP servers with rules
3. ✅ BLOCKING BEHAVIOR: Clear blocks when policies violated
4. ✅ TRACEABILITY: Complete audit trail from plan to execution
5. ✅ DELEGATION: Bounded delegation with authority limits
    """)
    
    if interactive:
        input("Press Enter to start the demo...")
    
    # Run all scenarios
    trace1 = await demo_scenario_1_approved_payment()
    if interactive:
        input("\nPress Enter for next scenario...")
    
    trace2 = await demo_scenario_2_blocked_payment()
    if interactive:
        input("\nPress Enter for next scenario...")
    
    trace3 = await demo_scenario_3_delegation()
    if interactive:
        input("\nPress Enter for next scenario...")
    
    trace4 = await demo_scenario_4_bypass_attempt()
    
    # Show complete audit trail
    print("\n" + "="*70)
    print("📊 COMPLETE AUDIT TRAIL")
    print("="*70)
    
    audit = get_audit_system()
    audit.print_summary()
    
    # Show individual traces
    print("\nDetailed trace for approved payment:")
    audit.print_trace(trace1)
    
    print("\nDetailed trace for blocked payment:")
    audit.print_trace(trace2)
    
    print("\n" + "="*70)
    print("✅ DEMO COMPLETE")
    print("="*70)
    print("""
KEY TAKEAWAYS:

1. Agents REASON FREELY - No constraints on thinking
2. Actions ONLY through MCP - Gateway controls all execution
3. BLOCKING is explicit - Clear reasons and audit trail
4. TRACEABILITY is complete - Every step logged
5. DELEGATION is bounded - Cannot exceed granted authority
    """)


if __name__ == "__main__":
    # Run in non-interactive mode with --auto flag
    interactive = "--auto" not in sys.argv
    asyncio.run(main(interactive))
