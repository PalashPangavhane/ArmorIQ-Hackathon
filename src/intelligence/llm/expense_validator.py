"""
Smart Expense Validator

Uses local LLM (Qwen3 8B) to intelligently validate expense claims
like cab reimbursements, checking if amounts are reasonable.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
import asyncio

from .local_llm_client import LocalLLMClient


class ExpenseType(Enum):
    CAB = "cab"
    FLIGHT = "flight"
    HOTEL = "hotel"
    FOOD = "food"
    SUPPLIES = "supplies"
    OTHER = "other"


class ValidationDecision(Enum):
    APPROVE = "APPROVE"      # Amount is reasonable
    FLAG = "FLAG"            # Needs human review
    REJECT = "REJECT"        # Clearly unreasonable


@dataclass
class ExpenseClaim:
    """An expense claim submitted for validation."""
    expense_id: str
    employee_id: str
    expense_type: ExpenseType
    amount: float
    currency: str
    from_location: Optional[str]
    to_location: Optional[str]
    description: str
    timestamp: datetime
    receipt_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "expense_id": self.expense_id,
            "employee_id": self.employee_id,
            "expense_type": self.expense_type.value,
            "amount": self.amount,
            "currency": self.currency,
            "from_location": self.from_location,
            "to_location": self.to_location,
            "description": self.description,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ValidationResult:
    """Result of expense validation."""
    expense_id: str
    decision: ValidationDecision
    expected_range: Dict[str, float]
    reasoning: str
    confidence: float
    thinking: Optional[str] = None  # LLM's reasoning process
    processing_time_ms: float = 0.0
    used_fallback: bool = False
    
    @property
    def is_approved(self) -> bool:
        return self.decision == ValidationDecision.APPROVE
    
    @property
    def needs_review(self) -> bool:
        return self.decision == ValidationDecision.FLAG
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "expense_id": self.expense_id,
            "decision": self.decision.value,
            "expected_range": self.expected_range,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "processing_time_ms": self.processing_time_ms
        }


class SmartExpenseValidator:
    """
    AI-powered expense validator using local LLM.
    
    Validates expense claims by checking if amounts are reasonable
    for the given expense type, locations, and context.
    
    Uses Qwen3 8B running locally via Ollama for intelligent reasoning.
    Falls back to heuristic rules if LLM is unavailable.
    """
    
    def __init__(
        self,
        llm_model: str = "qwen3:8b",
        ollama_url: str = "http://localhost:11434"
    ):
        self.llm_client = LocalLLMClient(
            model=llm_model,
            base_url=ollama_url
        )
        self._is_healthy: Optional[bool] = None
    
    async def close(self):
        """Close LLM client."""
        await self.llm_client.close()
    
    async def check_llm_health(self) -> bool:
        """Check if LLM is available."""
        self._is_healthy = await self.llm_client.check_health()
        return self._is_healthy
    
    async def validate(self, claim: ExpenseClaim) -> ValidationResult:
        """
        Validate an expense claim.
        
        Args:
            claim: The expense claim to validate
            
        Returns:
            ValidationResult with decision and reasoning
        """
        start_time = datetime.now()
        
        # Handle different expense types
        if claim.expense_type == ExpenseType.CAB:
            result = await self._validate_cab(claim)
        elif claim.expense_type == ExpenseType.FOOD:
            result = await self._validate_food(claim)
        elif claim.expense_type == ExpenseType.HOTEL:
            result = await self._validate_hotel(claim)
        else:
            result = await self._validate_generic(claim)
        
        # Add timing
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        result.processing_time_ms = elapsed
        
        return result
    
    async def _validate_cab(self, claim: ExpenseClaim) -> ValidationResult:
        """Validate cab/taxi expense."""
        
        llm_result = await self.llm_client.validate_expense(
            expense_type="cab",
            amount=claim.amount,
            from_location=claim.from_location or "Unknown",
            to_location=claim.to_location or "Unknown",
            description=claim.description,
            currency=claim.currency
        )
        
        return self._parse_llm_result(claim.expense_id, llm_result)
    
    async def _validate_food(self, claim: ExpenseClaim) -> ValidationResult:
        """Validate food/meal expense."""
        
        # Food expense limits (in INR)
        limits = {
            "breakfast": (100, 300),
            "lunch": (150, 500),
            "dinner": (200, 800),
            "team_meal": (500, 3000)
        }
        
        # Detect meal type from description
        desc_lower = claim.description.lower()
        meal_type = "lunch"  # default
        for meal in limits:
            if meal.replace("_", " ") in desc_lower:
                meal_type = meal
                break
        
        min_exp, max_exp = limits[meal_type]
        
        if claim.amount <= max_exp:
            decision = ValidationDecision.APPROVE
            reasoning = f"Food expense of {claim.currency} {claim.amount} is within expected range for {meal_type}"
            confidence = 0.85
        elif claim.amount <= max_exp * 1.5:
            decision = ValidationDecision.FLAG
            reasoning = f"Food expense slightly above typical {meal_type} range ({claim.currency} {max_exp})"
            confidence = 0.7
        else:
            decision = ValidationDecision.REJECT
            reasoning = f"Food expense of {claim.currency} {claim.amount} exceeds reasonable limit for {meal_type}"
            confidence = 0.9
        
        return ValidationResult(
            expense_id=claim.expense_id,
            decision=decision,
            expected_range={"min": min_exp, "max": max_exp},
            reasoning=reasoning,
            confidence=confidence,
            used_fallback=True
        )
    
    async def _validate_hotel(self, claim: ExpenseClaim) -> ValidationResult:
        """Validate hotel stay expense."""
        
        # Use LLM for hotel validation
        llm_result = await self.llm_client.validate_expense(
            expense_type="hotel",
            amount=claim.amount,
            from_location=claim.from_location or "Hotel",
            to_location=claim.to_location or "N/A",
            description=claim.description,
            currency=claim.currency
        )
        
        return self._parse_llm_result(claim.expense_id, llm_result)
    
    async def _validate_generic(self, claim: ExpenseClaim) -> ValidationResult:
        """Validate generic expense."""
        
        llm_result = await self.llm_client.validate_expense(
            expense_type=claim.expense_type.value,
            amount=claim.amount,
            from_location=claim.from_location or "N/A",
            to_location=claim.to_location or "N/A",
            description=claim.description,
            currency=claim.currency
        )
        
        return self._parse_llm_result(claim.expense_id, llm_result)
    
    def _parse_llm_result(
        self, 
        expense_id: str, 
        llm_result: Dict[str, Any]
    ) -> ValidationResult:
        """Parse LLM result into ValidationResult."""
        
        # Parse decision
        decision_str = llm_result.get("decision", "FLAG").upper()
        try:
            decision = ValidationDecision(decision_str)
        except ValueError:
            decision = ValidationDecision.FLAG
        
        # Parse expected range
        expected_range = llm_result.get("expected_range", {"min": 0, "max": 0})
        if not isinstance(expected_range, dict):
            expected_range = {"min": 0, "max": 0}
        
        return ValidationResult(
            expense_id=expense_id,
            decision=decision,
            expected_range=expected_range,
            reasoning=llm_result.get("reasoning", "No reasoning provided"),
            confidence=float(llm_result.get("confidence", 0.5)),
            thinking=llm_result.get("thinking"),
            used_fallback=llm_result.get("fallback_mode", False)
        )
    
    async def validate_batch(
        self, 
        claims: List[ExpenseClaim]
    ) -> List[ValidationResult]:
        """Validate multiple expense claims."""
        results = []
        for claim in claims:
            result = await self.validate(claim)
            results.append(result)
        return results


# Factory function
def create_expense_validator(
    model: str = "qwen3:8b"
) -> SmartExpenseValidator:
    """Create a SmartExpenseValidator instance."""
    return SmartExpenseValidator(llm_model=model)
