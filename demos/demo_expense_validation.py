#!/usr/bin/env python3
"""
Demo: Smart Expense Validation with Local LLM

Demonstrates intelligent expense validation using Qwen3 8B
running locally via Ollama. The LLM validates if expense
amounts are reasonable (e.g., cab fare for a route).

SETUP:
1. Install Ollama: https://ollama.ai
2. Pull Qwen3: ollama pull qwen3:8b
3. Run this demo: python demos/demo_expense_validation.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.intelligence.llm import (
    SmartExpenseValidator,
    ExpenseClaim,
    ExpenseType,
    ValidationDecision,
    LocalLLMClient
)


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header():
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}  🧠 Smart Expense Validation with Local LLM (Qwen3 8B){Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}\n")


def print_expense(claim: ExpenseClaim):
    print(f"  {Colors.BOLD}Expense:{Colors.END} {claim.expense_type.value.upper()}")
    print(f"  {Colors.BOLD}Amount:{Colors.END} {claim.currency} {claim.amount:,}")
    if claim.from_location:
        print(f"  {Colors.BOLD}From:{Colors.END} {claim.from_location}")
    if claim.to_location:
        print(f"  {Colors.BOLD}To:{Colors.END} {claim.to_location}")
    print(f"  {Colors.BOLD}Description:{Colors.END} {claim.description}")


def print_result(result):
    # Decision color
    if result.decision == ValidationDecision.APPROVE:
        color = Colors.GREEN
        icon = "✅"
    elif result.decision == ValidationDecision.FLAG:
        color = Colors.YELLOW
        icon = "⚠️"
    else:
        color = Colors.RED
        icon = "❌"
    
    print(f"\n  {Colors.BOLD}Decision:{Colors.END} {icon} {color}{result.decision.value}{Colors.END}")
    
    if result.expected_range.get("min") or result.expected_range.get("max"):
        print(f"  {Colors.BOLD}Expected Range:{Colors.END} ₹{result.expected_range.get('min', 0):,} - ₹{result.expected_range.get('max', 0):,}")
    
    print(f"  {Colors.BOLD}Confidence:{Colors.END} {result.confidence*100:.0f}%")
    print(f"  {Colors.BOLD}Reasoning:{Colors.END} {result.reasoning}")
    
    if result.thinking:
        print(f"\n  {Colors.MAGENTA}🤔 LLM Thinking:{Colors.END}")
        # Truncate long thinking
        thinking = result.thinking[:500] + "..." if len(result.thinking) > 500 else result.thinking
        for line in thinking.split('\n'):
            print(f"     {Colors.MAGENTA}{line}{Colors.END}")
    
    if result.used_fallback:
        print(f"  {Colors.YELLOW}⚡ Used fallback heuristics (LLM unavailable){Colors.END}")
    
    print(f"  {Colors.BOLD}Processing Time:{Colors.END} {result.processing_time_ms:.0f}ms")


async def demo_cab_reasonable():
    """Test 1: Reasonable cab fare - should APPROVE"""
    print(f"\n{Colors.BLUE}━━━ Scenario 1: Reasonable Cab Fare ━━━{Colors.END}")
    print(f"  Employee claims cab from office to airport")
    
    claim = ExpenseClaim(
        expense_id="EXP-001",
        employee_id="emp_ravi",
        expense_type=ExpenseType.CAB,
        amount=850,
        currency="INR",
        from_location="Hinjewadi IT Park, Pune",
        to_location="Pune Airport",
        description="Cab to airport for client meeting in Mumbai",
        timestamp=datetime.now()
    )
    print_expense(claim)
    
    validator = SmartExpenseValidator()
    try:
        result = await validator.validate(claim)
        print_result(result)
        return result.decision == ValidationDecision.APPROVE
    finally:
        await validator.close()


async def demo_cab_inflated():
    """Test 2: Inflated cab fare - should FLAG or REJECT"""
    print(f"\n{Colors.BLUE}━━━ Scenario 2: Inflated Cab Fare ━━━{Colors.END}")
    print(f"  Employee claims unusually high amount for short trip")
    
    claim = ExpenseClaim(
        expense_id="EXP-002",
        employee_id="emp_priya",
        expense_type=ExpenseType.CAB,
        amount=2500,  # Too high for local trip
        currency="INR",
        from_location="Koramangala, Bangalore",
        to_location="Indiranagar, Bangalore",  # Only 5-6 km
        description="Cab to lunch meeting",
        timestamp=datetime.now()
    )
    print_expense(claim)
    
    validator = SmartExpenseValidator()
    try:
        result = await validator.validate(claim)
        print_result(result)
        # Should be flagged due to high amount for short distance
        return result.decision in [ValidationDecision.FLAG, ValidationDecision.REJECT]
    finally:
        await validator.close()


async def demo_cab_surge():
    """Test 3: Surge pricing scenario - might APPROVE with context"""
    print(f"\n{Colors.BLUE}━━━ Scenario 3: Late Night Surge Pricing ━━━{Colors.END}")
    print(f"  Employee claims higher fare due to late night surge")
    
    claim = ExpenseClaim(
        expense_id="EXP-003",
        employee_id="emp_amit",
        expense_type=ExpenseType.CAB,
        amount=1200,  # Higher than usual but justified
        currency="INR",
        from_location="MG Road, Bangalore",
        to_location="Electronic City, Bangalore",  # ~20 km
        description="Late night cab at 11 PM after project deadline - surge pricing 1.8x",
        timestamp=datetime.now()
    )
    print_expense(claim)
    
    validator = SmartExpenseValidator()
    try:
        result = await validator.validate(claim)
        print_result(result)
        # Could be approved if LLM understands surge pricing context
        return True  # Accept any decision, context-dependent
    finally:
        await validator.close()


async def demo_food_reasonable():
    """Test 4: Reasonable food expense"""
    print(f"\n{Colors.BLUE}━━━ Scenario 4: Reasonable Lunch Expense ━━━{Colors.END}")
    print(f"  Employee claims lunch during client visit")
    
    claim = ExpenseClaim(
        expense_id="EXP-004",
        employee_id="emp_neha",
        expense_type=ExpenseType.FOOD,
        amount=350,
        currency="INR",
        from_location=None,
        to_location=None,
        description="Lunch at Truffles during client visit",
        timestamp=datetime.now()
    )
    print_expense(claim)
    
    validator = SmartExpenseValidator()
    try:
        result = await validator.validate(claim)
        print_result(result)
        return result.decision == ValidationDecision.APPROVE
    finally:
        await validator.close()


async def demo_food_inflated():
    """Test 5: Inflated food expense"""
    print(f"\n{Colors.BLUE}━━━ Scenario 5: Inflated Food Expense ━━━{Colors.END}")
    print(f"  Employee claims unusually high lunch amount")
    
    claim = ExpenseClaim(
        expense_id="EXP-005",
        employee_id="emp_raj",
        expense_type=ExpenseType.FOOD,
        amount=1500,  # Too high for solo lunch
        currency="INR",
        from_location=None,
        to_location=None,
        description="Lunch at restaurant",
        timestamp=datetime.now()
    )
    print_expense(claim)
    
    validator = SmartExpenseValidator()
    try:
        result = await validator.validate(claim)
        print_result(result)
        return result.decision in [ValidationDecision.FLAG, ValidationDecision.REJECT]
    finally:
        await validator.close()


async def check_llm_status():
    """Check if Qwen3 is running."""
    print(f"{Colors.CYAN}Checking LLM status...{Colors.END}")
    client = LocalLLMClient()
    try:
        is_healthy = await client.check_health()
        if is_healthy:
            print(f"{Colors.GREEN}✅ Qwen3 8B is running via Ollama{Colors.END}")
        else:
            print(f"{Colors.YELLOW}⚠️ Qwen3 not found. Using fallback heuristics.{Colors.END}")
            print(f"   To enable LLM: ollama pull qwen3:8b && ollama serve")
        return is_healthy
    finally:
        await client.close()


async def main():
    print_header()
    
    # Check LLM status
    await check_llm_status()
    
    print(f"\n{Colors.BOLD}Running Expense Validation Scenarios...{Colors.END}")
    
    results = []
    
    # Run all scenarios
    results.append(("Reasonable Cab", await demo_cab_reasonable()))
    results.append(("Inflated Cab", await demo_cab_inflated()))
    results.append(("Surge Pricing", await demo_cab_surge()))
    results.append(("Reasonable Food", await demo_food_reasonable()))
    results.append(("Inflated Food", await demo_food_inflated()))
    
    # Summary
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}Summary{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        icon = f"{Colors.GREEN}✅{Colors.END}" if result else f"{Colors.RED}❌{Colors.END}"
        print(f"  {icon} {name}")
    
    print(f"\n  {Colors.BOLD}Result: {passed}/{total} scenarios validated correctly{Colors.END}")
    
    print(f"\n{Colors.CYAN}💡 This demonstrates how the LLM validates expense reasonableness")
    print(f"   without calling external APIs like Google Maps.{Colors.END}\n")


if __name__ == "__main__":
    asyncio.run(main())
