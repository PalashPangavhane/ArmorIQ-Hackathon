"""
API Routes Module

REST API endpoints for the payment security system.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter()


class PaymentRequest(BaseModel):
    """Schema for payment/reimbursement request."""
    request_id: str = Field(..., description="Unique request identifier")
    employee_id: str = Field(..., description="Requesting employee ID")
    amount: float = Field(..., gt=0, description="Payment amount")
    department: str = Field(..., description="Department")
    vendor_id: str = Field(None, description="Vendor ID if applicable")
    purpose: str = Field(..., description="Purpose of payment")
    category: str = Field(..., description="Expense category")


class PaymentResponse(BaseModel):
    """Schema for payment response."""
    request_id: str
    status: str
    decision: Dict[str, Any]
    execution_result: Dict[str, Any] = None


@router.post("/payments/submit", response_model=PaymentResponse)
async def submit_payment_request(request: PaymentRequest):
    """
    Submit a payment or reimbursement request.
    
    Flow:
    1. Request received by API
    2. Routed to agent coordinator
    3. Policy evaluation
    4. Execution if approved
    """
    # This would be connected to the actual system components
    return PaymentResponse(
        request_id=request.request_id,
        status="received",
        decision={"pending": True}
    )


@router.get("/payments/{request_id}/status")
async def get_payment_status(request_id: str):
    """Get the status of a payment request."""
    # Implementation would query actual system state
    return {"request_id": request_id, "status": "pending"}


@router.get("/audit/decisions")
async def get_audit_log():
    """Get audit log of all decisions."""
    # Implementation would return enforcement gateway audit log
    return {"decisions": []}


@router.get("/risk/{entity_type}/{entity_id}")
async def get_entity_risk(entity_type: str, entity_id: str):
    """Get risk assessment for an entity."""
    # Implementation would query GNN risk service
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "risk_level": "LOW",
        "risk_score": 0.15
    }
