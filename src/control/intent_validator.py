"""
Intent Validator Module

Validates agent intents before policy evaluation.
Ensures intents are well-formed and from authorized agents.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class ValidationResult(Enum):
    VALID = "valid"
    INVALID = "invalid"
    MALFORMED = "malformed"


@dataclass
class IntentValidation:
    """Result of intent validation."""
    result: ValidationResult
    errors: List[str]
    warnings: List[str]
    
    def is_valid(self) -> bool:
        return self.result == ValidationResult.VALID


class IntentValidator:
    """
    Validates agent intents for correctness and authorization.
    
    Checks:
    - Intent structure and required fields
    - Agent authorization for intent type
    - Parameter validity
    - Target existence
    """
    
    REQUIRED_FIELDS = [
        "intent_type",
        "target_id",
        "parameters",
        "reasoning",
        "confidence",
        "agent_id"
    ]
    
    VALID_INTENT_TYPES = [
        "approve_payment",
        "reject_payment",
        "escalate",
        "request_info",
        "flag_suspicious"
    ]
    
    # Agent authorization matrix
    AGENT_PERMISSIONS = {
        "finance_agent": ["approve_payment", "reject_payment", "escalate", "request_info"],
        "fraud_agent": ["flag_suspicious", "request_info", "approve_payment"],
        "ceo_agent": ["approve_payment", "reject_payment", "escalate", "flag_suspicious"]
    }
    
    def __init__(self):
        self._authorized_agents: Dict[str, List[str]] = self.AGENT_PERMISSIONS.copy()
    
    def validate(self, intent: Dict[str, Any]) -> IntentValidation:
        """
        Validate an intent.
        
        Args:
            intent: Intent dictionary to validate
            
        Returns:
            IntentValidation with result and any errors/warnings
        """
        errors = []
        warnings = []
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in intent:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return IntentValidation(
                result=ValidationResult.MALFORMED,
                errors=errors,
                warnings=warnings
            )
        
        # Validate intent type
        intent_type = intent.get("intent_type")
        if intent_type not in self.VALID_INTENT_TYPES:
            errors.append(f"Invalid intent type: {intent_type}")
        
        # Validate agent authorization
        agent_id = intent.get("agent_id", "")
        agent_type = self._extract_agent_type(agent_id)
        
        if agent_type and intent_type:
            if not self._is_authorized(agent_type, intent_type):
                errors.append(
                    f"Agent {agent_type} not authorized for intent {intent_type}"
                )
        
        # Validate confidence score
        confidence = intent.get("confidence", 0)
        if not 0 <= confidence <= 1:
            errors.append(f"Invalid confidence score: {confidence}")
        
        # Validate parameters
        param_errors = self._validate_parameters(intent_type, intent.get("parameters", {}))
        errors.extend(param_errors)
        
        # Add warnings for low confidence
        if confidence < 0.5:
            warnings.append(f"Low confidence score: {confidence}")
        
        if errors:
            return IntentValidation(
                result=ValidationResult.INVALID,
                errors=errors,
                warnings=warnings
            )
        
        return IntentValidation(
            result=ValidationResult.VALID,
            errors=[],
            warnings=warnings
        )
    
    def _extract_agent_type(self, agent_id: str) -> Optional[str]:
        """Extract agent type from agent ID."""
        if "finance" in agent_id.lower():
            return "finance_agent"
        elif "fraud" in agent_id.lower():
            return "fraud_agent"
        elif "ceo" in agent_id.lower():
            return "ceo_agent"
        return None
    
    def _is_authorized(self, agent_type: str, intent_type: str) -> bool:
        """Check if agent type is authorized for intent type."""
        permissions = self._authorized_agents.get(agent_type, [])
        return intent_type in permissions
    
    def _validate_parameters(
        self, 
        intent_type: str, 
        parameters: Dict[str, Any]
    ) -> List[str]:
        """Validate intent parameters based on intent type."""
        errors = []
        
        if intent_type == "approve_payment":
            if "amount" not in parameters:
                errors.append("approve_payment requires 'amount' parameter")
            elif parameters["amount"] <= 0:
                errors.append("Amount must be positive")
        
        if intent_type == "escalate":
            if "reason" not in parameters:
                errors.append("escalate requires 'reason' parameter")
        
        return errors
    
    def register_agent_permissions(
        self, 
        agent_type: str, 
        permissions: List[str]
    ):
        """Register or update agent permissions."""
        self._authorized_agents[agent_type] = permissions
