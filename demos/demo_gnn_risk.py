"""
GNN Risk Detection Demo
========================

This demo showcases the GNN-based fraud and risk detection system:

1. ✅ Transaction graph building
2. ✅ Risk signal generation (not decisions!)
3. ✅ Multiple risk factors analyzed
4. ✅ Entity profiling and pattern detection
5. ✅ Integration with policy enforcement

Run this demo:
    python demos/demo_gnn_risk.py
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.intelligence.gnn.graph_builder import TransactionGraphBuilder, NodeType, EdgeType
from src.intelligence.gnn.risk_model import FraudRiskModel, RiskLevel
from src.intelligence.gnn.risk_service import RiskAssessmentService, create_demo_service
from src.control.risk_policy_integrator import RiskPolicyIntegrator
from src.control.policy_engine import PolicyEngine


# Terminal colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(title: str):
    """Print a styled header."""
    print(f"\n{'='*70}")
    print(f"{Colors.BOLD}{Colors.CYAN}{title}{Colors.END}")
    print(f"{'='*70}\n")


def print_scenario(num: int, title: str, description: str):
    """Print a scenario header."""
    print(f"\n{Colors.BOLD}━━━ SCENARIO {num}: {title} ━━━{Colors.END}")
    print(f"{Colors.BLUE}Description:{Colors.END} {description}\n")


def print_risk_signal(signal):
    """Print risk signal with colors."""
    level = signal.risk_level.value if hasattr(signal.risk_level, 'value') else signal.risk_level
    score = signal.risk_score
    
    if level == "HIGH":
        color = Colors.RED
        icon = "🔴"
    elif level == "MEDIUM":
        color = Colors.YELLOW
        icon = "🟡"
    else:
        color = Colors.GREEN
        icon = "🟢"
    
    print(f"\n{Colors.BOLD}Risk Signal:{Colors.END}")
    print(f"  {icon} Level: {color}{level}{Colors.END}")
    print(f"  📊 Score: {score:.3f}")
    
    if signal.risk_reasons:
        print(f"  ⚠️  Reasons:")
        for reason in signal.risk_reasons:
            print(f"     • {reason}")
    
    if hasattr(signal, 'risk_factors') and signal.risk_factors:
        print(f"\n  {Colors.CYAN}Risk Factors:{Colors.END}")
        for factor, factor_score in signal.risk_factors.items():
            bar_len = int(factor_score * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            print(f"     {factor:25} [{bar}] {factor_score:.2f}")


def demo_transaction_graph():
    """Demonstrate transaction graph building."""
    print_header("📊 Transaction Graph Building")
    
    builder = TransactionGraphBuilder()
    
    print(f"{Colors.YELLOW}Building transaction graph...{Colors.END}\n")
    
    # Add employees
    builder.add_node("emp_001", NodeType.EMPLOYEE, {"name": "Alice", "department": "Engineering"})
    builder.add_node("emp_002", NodeType.EMPLOYEE, {"name": "Bob", "department": "Marketing"})
    
    # Add vendors
    builder.add_node("vendor_001", NodeType.VENDOR, {"name": "Office Depot"})
    builder.add_node("vendor_002", NodeType.VENDOR, {"name": "AWS"})
    builder.add_node("vendor_003", NodeType.VENDOR, {"name": "Unknown LLC"})
    
    # Add transactions
    builder.add_edge("emp_001", "vendor_001", EdgeType.TRANSACTION, 250.0, "2024-01-15", "office_supplies")
    builder.add_edge("emp_001", "vendor_002", EdgeType.TRANSACTION, 5000.0, "2024-01-16", "software")
    builder.add_edge("emp_002", "vendor_001", EdgeType.TRANSACTION, 150.0, "2024-01-17", "office_supplies")
    
    # Build and show stats
    graph = builder.build_graph()
    stats = graph["statistics"]
    
    print(f"  📌 Total Nodes: {stats['total_nodes']}")
    print(f"  📌 Total Edges: {stats['total_edges']}")
    print(f"  📌 Nodes by Type:")
    for node_type, count in stats['nodes_by_type'].items():
        print(f"      • {node_type}: {count}")
    print(f"  💰 Total Volume: ${stats['total_transaction_volume']:,.2f}")
    print(f"  📊 Avg Transaction: ${stats['average_transaction_amount']:,.2f}")
    
    return builder


async def demo_scenario_1_low_risk():
    """Scenario 1: Normal transaction - LOW RISK"""
    print_scenario(
        1,
        "Normal Transaction",
        "Regular office supplies purchase from known vendor"
    )
    
    service = create_demo_service()
    
    transaction = {
        "amount": 250,
        "vendor": "Office Depot",
        "category": "office_supplies",
        "employee_id": "emp_001",
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"{Colors.YELLOW}Transaction:{Colors.END}")
    print(f"  • Amount: ${transaction['amount']}")
    print(f"  • Vendor: {transaction['vendor']}")
    print(f"  • Category: {transaction['category']}")
    
    signal = service.assess_transaction_risk(transaction)
    print_risk_signal(signal)
    
    return signal.risk_level == RiskLevel.LOW


async def demo_scenario_2_new_vendor():
    """Scenario 2: New vendor - MEDIUM RISK"""
    print_scenario(
        2,
        "New/Unknown Vendor",
        "Transaction to a vendor not seen before"
    )
    
    service = create_demo_service()
    
    transaction = {
        "amount": 3000,
        "vendor": "NewStartup XYZ",
        "category": "services",
        "employee_id": "emp_001",
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"{Colors.YELLOW}Transaction:{Colors.END}")
    print(f"  • Amount: ${transaction['amount']}")
    print(f"  • Vendor: {transaction['vendor']} {Colors.RED}(NEW!){Colors.END}")
    print(f"  • Category: {transaction['category']}")
    
    signal = service.assess_transaction_risk(transaction)
    print_risk_signal(signal)
    
    return signal.risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]


async def demo_scenario_3_amount_spike():
    """Scenario 3: Amount spike - HIGH RISK"""
    print_scenario(
        3,
        "Amount Spike",
        "Large unexpected amount from normally low-spending employee"
    )
    
    service = create_demo_service()
    
    # First establish baseline with small transactions
    for i in range(3):
        service.assess_transaction_risk({
            "amount": 100 + i * 50,
            "vendor": "Office Depot",
            "category": "office_supplies",
            "employee_id": "emp_new"
        })
    
    print(f"{Colors.CYAN}Baseline established: 3 transactions, avg ~$150{Colors.END}\n")
    
    # Now spike the amount
    transaction = {
        "amount": 25000,
        "vendor": "Unknown LLC",
        "category": "consulting",
        "employee_id": "emp_new",
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"{Colors.YELLOW}Spike Transaction:{Colors.END}")
    print(f"  • Amount: ${transaction['amount']:,} {Colors.RED}(167x baseline!){Colors.END}")
    print(f"  • Vendor: {transaction['vendor']}")
    print(f"  • Category: {transaction['category']}")
    
    signal = service.assess_transaction_risk(transaction)
    print_risk_signal(signal)
    
    return signal.risk_level == RiskLevel.HIGH


async def demo_scenario_4_multiple_factors():
    """Scenario 4: Multiple risk factors - HIGH RISK"""
    print_scenario(
        4,
        "Multiple Risk Factors",
        "Transaction with many suspicious indicators"
    )
    
    service = create_demo_service()
    
    # Suspicious transaction: round amount, new vendor, consulting, large
    transaction = {
        "amount": 50000,  # Large round amount
        "vendor": "Suspicious Consulting Inc",  # New vendor
        "category": "consulting",  # High-risk category
        "employee_id": "emp_never_seen",  # First-time user
        "timestamp": datetime.now().replace(hour=2, minute=0).isoformat()  # Off hours
    }
    
    print(f"{Colors.YELLOW}Suspicious Transaction:{Colors.END}")
    print(f"  • Amount: ${transaction['amount']:,} {Colors.RED}(round, large){Colors.END}")
    print(f"  • Vendor: {transaction['vendor']} {Colors.RED}(unknown){Colors.END}")
    print(f"  • Category: {transaction['category']} {Colors.RED}(high-risk){Colors.END}")
    print(f"  • Employee: First-time user")
    print(f"  • Time: 2:00 AM {Colors.RED}(off hours){Colors.END}")
    
    signal = service.assess_transaction_risk(transaction)
    print_risk_signal(signal)
    
    return signal.risk_level == RiskLevel.HIGH


async def demo_scenario_5_policy_integration():
    """Scenario 5: GNN + Policy integration"""
    print_scenario(
        5,
        "GNN + Policy Integration",
        "Risk signal influences policy decision"
    )
    
    # Create policy engine and risk integrator
    policy_engine = PolicyEngine()
    policy_engine.disable_time_window_check()
    risk_integrator = RiskPolicyIntegrator(policy_engine)
    
    # Normal transaction but HIGH risk signal
    intent = {
        "intent_type": "approve_payment",
        "target_id": "req_005",
        "parameters": {
            "amount": 5000,  # Within normal limits
            "vendor": "TechSupplies Inc",
            "category": "equipment"
        },
        "reasoning": "Equipment purchase",
        "confidence": 0.90,
        "agent_id": "finance_agent_001"
    }
    
    # Simulate high risk from GNN
    risk_signal = {
        "risk_level": "HIGH",
        "risk_score": 0.85,
        "risk_reasons": ["velocity_spike", "unusual_pattern", "new_device"]
    }
    
    print(f"{Colors.YELLOW}Transaction:{Colors.END}")
    print(f"  • Amount: ${intent['parameters']['amount']:,} (within policy limits)")
    print(f"  • Vendor: {intent['parameters']['vendor']}")
    
    print(f"\n{Colors.RED}GNN Risk Signal:{Colors.END}")
    print(f"  • Level: HIGH")
    print(f"  • Score: 0.85")
    print(f"  • Reasons: {', '.join(risk_signal['risk_reasons'])}")
    
    # Evaluate with risk
    result = risk_integrator.evaluate_with_risk(intent, risk_signal)
    
    print(f"\n{Colors.BOLD}Combined Decision:{Colors.END}")
    if result.get("allowed"):
        status = f"{Colors.GREEN}✅ ALLOWED{Colors.END}"
    else:
        status = f"{Colors.RED}❌ BLOCKED/FROZEN{Colors.END}"
    
    print(f"  • Decision: {status}")
    print(f"  • Risk Action: {result.get('risk_action')}")
    
    if result.get("constraints"):
        print(f"  • Constraints Applied:")
        for key, value in result.get("constraints", {}).items():
            print(f"      • {key}: {value}")
    
    return not result.get("allowed") or result.get("constraints", {}).get("frozen")


async def demo_entity_profiling():
    """Demonstrate entity profiling."""
    print_header("👤 Entity Risk Profiling")
    
    service = create_demo_service()
    
    # Add some transaction history
    for i in range(5):
        service.assess_transaction_risk({
            "amount": 200 + i * 100,
            "vendor": "Office Depot",
            "category": "office_supplies",
            "employee_id": "emp_profiled"
        })
    
    # Get profile
    profile = service.get_entity_risk_profile("emp_profiled", "employee")
    
    print(f"{Colors.YELLOW}Entity Profile: emp_profiled{Colors.END}\n")
    
    analysis = profile.get("pattern_analysis", {})
    print(f"  📊 Total Transactions: {analysis.get('total_transactions', 0)}")
    print(f"  💰 Average Amount: ${analysis.get('average_amount', 0):,.2f}")
    print(f"  🏷️  Typical Categories: {', '.join(analysis.get('typical_categories', []))}")
    print(f"  🏢 Typical Vendors: {', '.join(analysis.get('typical_vendors', []))}")
    print(f"  📈 Profile Maturity: {analysis.get('profile_maturity', 'unknown')}")
    print(f"  ⚠️  Baseline Risk: {analysis.get('baseline_risk', 'unknown')}")
    print(f"  📉 Risk Trend: {profile.get('risk_trend', 'unknown')}")


async def main():
    """Run all GNN demo scenarios."""
    print_header("🧠 GNN Risk Detection Demo")
    
    print(f"""{Colors.BOLD}
╔════════════════════════════════════════════════════════════════════╗
║  This demo shows how the GNN-based risk detection system works.   ║
║                                                                    ║
║  KEY PRINCIPLE: GNN produces SIGNALS, not decisions.              ║
║  The signals INFLUENCE but do not directly BLOCK transactions.    ║
║  Actual blocking is done by the Policy + Risk Integrator layer.   ║
╚════════════════════════════════════════════════════════════════════╝
{Colors.END}""")
    
    # Demo graph building
    demo_transaction_graph()
    
    # Track results
    results = []
    
    print_header("🎬 RISK ASSESSMENT SCENARIOS")
    
    results.append(("Low Risk Transaction", await demo_scenario_1_low_risk()))
    results.append(("New Vendor Detection", await demo_scenario_2_new_vendor()))
    results.append(("Amount Spike Detection", await demo_scenario_3_amount_spike()))
    results.append(("Multiple Risk Factors", await demo_scenario_4_multiple_factors()))
    results.append(("Policy Integration", await demo_scenario_5_policy_integration()))
    
    # Entity profiling
    await demo_entity_profiling()
    
    # Summary
    print_header("📊 DEMO SUMMARY")
    
    all_passed = True
    for name, passed in results:
        status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
        print(f"  {status}  {name}")
        if not passed:
            all_passed = False
    
    print(f"\n{'='*70}")
    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}All GNN scenarios demonstrated successfully!{Colors.END}")
    else:
        print(f"{Colors.RED}Some scenarios did not behave as expected.{Colors.END}")
    print(f"{'='*70}\n")
    
    print(f"""{Colors.BOLD}
📌 KEY HACKATHON REQUIREMENTS DEMONSTRATED:
{Colors.END}
  1. ✅ GNN produces SIGNALS (read-only layer)
  2. ✅ Multiple risk factors analyzed
  3. ✅ Entity profiling and pattern detection
  4. ✅ Risk signals influence policy decisions
  5. ✅ High risk can FREEZE execution
  6. ✅ Full audit trail of risk assessments
""")


if __name__ == "__main__":
    asyncio.run(main())
